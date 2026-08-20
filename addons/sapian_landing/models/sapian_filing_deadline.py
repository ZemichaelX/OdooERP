# -*- coding: utf-8 -*-
"""When each statutory filing is due. CONFIGURATION, with an effective date.

CLAUDE.md rule 4, applied to a date instead of a rate: "Tax rates, PAYE bands,
pension %, thresholds are CONFIGURATION DATA in dedicated config models / data
files with effective dates — NEVER hard-coded in business logic. Changing a
future rate must never alter historical payslips/entries."

A deadline is the same kind of fact. If the Ministry of Revenues moves the VAT
return from 30 days to 45, last March's return was still late on the old rule,
and a landing page that recomputed history against the new one would quietly
absolve a filing that was actually late.

TWO SHAPES, BECAUSE THE EVIDENCE HAS TWO SHAPES
-----------------------------------------------
- **days** — "within 30 days of the period end". This is pension's shape:
  CLAUDE.md, "pension via POESSA declaration + bank slip within 30 days".
- **end_of_next_period** — "during the following month". This is employment
  income tax's shape, VERIFIED in `docs/ethiopian-tax-reference.md` §2: *"The
  declaration for one Ethiopian month is filed at any time during the following
  Ethiopian month"*, with the accountant's example *"Sene taxes must be
  reported from Hamle 01 to Hamle 30."*

They agree for eleven months of the Ethiopian year, because an Ethiopian month
is 30 days. They part at **Pagume**, which is 5 or 6: Nehase's return is due at
the end of Pagume — 10 September 2026 — where "+30 days" would say 5 October,
25 days late. A rule that is right by coincidence is not a rule, so the shape is
recorded rather than the coincidence.

WHAT IS STILL UNVERIFIED, AND SAYS SO
--------------------------------------
VAT, withholding and pension keep 30 days, and their rows carry the word
UNVERIFIED and the exact question that would settle each one. That figure is
what this project recorded for pension, applied to the other two by analogy —
and analogy is not evidence. `data/filing_deadline_data.xml` carries the notes.
"""

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..reference import filing_status


class SapianFilingDeadline(models.Model):
    _name = "sapian.filing.deadline"
    _description = "Statutory Filing Deadline Rule"
    _order = "filing_key, effective_from desc"

    company_id = fields.Many2one(
        "res.company",
        index=True,
        help="Leave empty for a rule that applies to every company — which is "
        "what the seeded statutory rules are, because a filing deadline is the "
        "law's, not the tenant's. A rule WITH a company beats a global one for "
        "that company, so a group whose entities hold different filing "
        "categories can override just the entity that differs. Not a "
        "multi-company leak: the global row is a default, and no company's "
        "data is read through it.",
    )
    filing_key = fields.Selection(
        [
            ("vat", "Value Added Tax"),
            ("wht", "Withholding Tax"),
            ("paye", "Employment Income Tax"),
            ("pension", "Pension"),
        ],
        required=True,
        index=True,
    )
    effective_from = fields.Date(
        required=True,
        help="The first period END this rule applies to. A period that ends "
        "before every rule's start has NO deadline and reads as unknown on the "
        "landing page — it does not borrow a rule written later.",
    )
    # NAMED `deadline_window`, NOT `window`. `WINDOW` is a RESERVED WORD in
    # PostgreSQL (SQL:2003 window functions), so a column called `window` is
    # legal only when quoted. Odoo's ORM quotes every identifier it generates,
    # so the field itself worked and the tests passed — and the first piece of
    # raw SQL to touch it, the migration next door, died on
    # `syntax error at or near "window"`. A name that is safe only as long as
    # nobody writes SQL is a trap with a fuse, not a name.
    deadline_window = fields.Selection(
        [
            (filing_status.WINDOW_DAYS, "A number of days after the period ends"),
            (
                filing_status.WINDOW_END_OF_NEXT_PERIOD,
                "The end of the following filing period",
            ),
        ],
        required=True,
        default=filing_status.WINDOW_DAYS,
        help="Which SHAPE the deadline has. 'End of the following period' "
        "follows the filing's own calendar, so it lands on the last day of the "
        "next Ethiopian month for a filing counted in Ethiopian months.",
    )
    days_after_period_end = fields.Integer(
        default=30,
        help="Days after the last day of the period by which the filing is "
        "due. Read only when the window is 'a number of days'. UNVERIFIED "
        "against a current Ministry of Revenues schedule — see the model "
        "docstring.",
    )
    source_note = fields.Char(
        help="Where this figure came from, so the next person can check it "
        "rather than trust it.",
    )

    _sql_constraints = [
        (
            "unique_rule_per_period",
            "unique(company_id, filing_key, effective_from)",
            "Two deadline rules for the same filing cannot start on the same "
            "day — which of them applied would be undefined.",
        ),
    ]

    @api.constrains("days_after_period_end", "deadline_window")
    def _check_days(self):
        for rule in self:
            if rule.deadline_window != filing_status.WINDOW_DAYS:
                continue
            if rule.days_after_period_end <= 0:
                raise ValidationError(
                    self.env._("A filing deadline must fall after the period it covers.")
                )

    @api.model
    def _rule_for(self, filing_key, period_end, company):
        """The (deadline_window, days) in force for ``period_end``, or ``None``.

        ``None`` is a real answer and reaches the page as "deadline unknown".
        """
        if not period_end:
            return None

        def rule(domain):
            rules = self.sudo().search(domain + [("filing_key", "=", filing_key)])
            return filing_status.effective_rule(
                [
                    (item.effective_from, (item.deadline_window, item.days_after_period_end))
                    for item in rules
                ],
                period_end,
            )

        # The company's own rule wins outright, then the global one. Two
        # searches rather than one sorted list: "specific beats global" and
        # "later beats earlier" are different questions, and resolving them in
        # one pass is where an off-by-one in the ordering hides.
        specific = rule([("company_id", "=", company.id)])
        return specific if specific is not None else rule([("company_id", "=", False)])
