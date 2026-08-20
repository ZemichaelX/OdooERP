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

THE SEEDED VALUE IS UNVERIFIED, AND SAYS SO
--------------------------------------------
30 days after the period end, for all four. That is what this project has
recorded for pension — CLAUDE.md, "pension via POESSA declaration + bank slip
within 30 days" — applied to VAT, withholding and employment income tax by
analogy. It has NOT been checked against a current MoR schedule, which is
exactly why it is a dated row an accountant can correct in the UI rather than a
constant in a method. `data/filing_deadline_data.xml` carries the note too.
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
    days_after_period_end = fields.Integer(
        required=True,
        default=30,
        help="Days after the last day of the period by which the filing is "
        "due. UNVERIFIED against a current Ministry of Revenues schedule — see "
        "the model docstring.",
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

    @api.constrains("days_after_period_end")
    def _check_days(self):
        for rule in self:
            if rule.days_after_period_end <= 0:
                raise ValidationError(
                    self.env._("A filing deadline must fall after the period it covers.")
                )

    @api.model
    def _days_for(self, filing_key, period_end, company):
        """The rule in force for ``period_end``, or ``None``.

        ``None`` is a real answer and reaches the page as "deadline unknown".
        """
        if not period_end:
            return None

        def days(domain):
            rules = self.sudo().search(domain + [("filing_key", "=", filing_key)])
            return filing_status.effective_rule(
                [(rule.effective_from, rule.days_after_period_end) for rule in rules],
                period_end,
            )

        # The company's own rule wins outright, then the global one. Two
        # searches rather than one sorted list: "specific beats global" and
        # "later beats earlier" are different questions, and resolving them in
        # one pass is where an off-by-one in the ordering hides.
        specific = days([("company_id", "=", company.id)])
        return specific if specific is not None else days([("company_id", "=", False)])
