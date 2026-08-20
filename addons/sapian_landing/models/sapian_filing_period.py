# -*- coding: utf-8 -*-
"""WHICH CALENDAR each statutory filing is counted in. Configuration, dated.

THE DEFECT THIS MODEL EXISTS FOR. The landing page used one Gregorian month for
all four filings. Rendered in Ethiopian dates that read "Sene 2018 – Hamle
2018" — two month names over 31 days that begin 24 days into Sene and end 24
days into Hamle, covering neither. For employment income tax that is not a
labelling problem: `docs/ethiopian-tax-reference.md` §2 is VERIFIED that the
period IS an Ethiopian month, so every figure on that row covered the wrong 31
days.

WHY IT IS DATA AND NOT A CONSTANT. Three of the four are still open questions —
the reference is silent on VAT and withholding and explicitly UNVERIFIED on
pension's window. Recording the calendar as an effective-dated row means the
answer, when somebody gets it, is a data change made by the accountant who got
it. The alternative is a constant in a method and a release.

Same discipline as `sapian.filing.deadline` beside it, and as the PAYE bands and
WHT rates before them: CLAUDE.md rule 4. `effective_from` is load-bearing —
moving a filing from one calendar to another must never re-cut a period that has
already been declared under the old one.

READ THE SOURCE NOTE BEFORE TRUSTING A ROW. `data/filing_period_data.xml` puts
the word UNVERIFIED and the exact question that would settle it into the three
rows that are not settled. CLAUDE.md forbids building logic on those; what the
product does instead is keep today's behaviour and say so on the row.
"""

from odoo import api, fields, models

from ..reference import filing_status


class SapianFilingPeriod(models.Model):
    _name = "sapian.filing.period"
    _description = "Statutory Filing Period Rule"
    _order = "filing_key, effective_from desc"

    company_id = fields.Many2one(
        "res.company",
        index=True,
        help="Leave empty for a rule that applies to every company. A rule WITH "
        "a company beats a global one for that company — which is how a tenant "
        "whose accountant has established the answer for VAT gets it without "
        "waiting for the seeded row to be corrected for everybody.",
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
        help="The first day this calendar applies from. A period assessed "
        "before every rule's start has NO calendar and the page says so rather "
        "than borrowing one written later.",
    )
    calendar = fields.Selection(
        [
            (filing_status.GREGORIAN, "Gregorian month"),
            (filing_status.ETHIOPIAN, "Ethiopian month"),
        ],
        required=True,
        default=filing_status.GREGORIAN,
        help="The calendar whose months are this filing's periods. Dates are "
        "always stored in Gregorian; this decides where the period BOUNDARIES "
        "fall, not how a date is written down.",
    )
    source_note = fields.Text(
        help="Where this came from, and — where it did not come from anywhere "
        "yet — the exact question that would settle it.",
    )

    _sql_constraints = [
        (
            "unique_period_rule",
            "unique(company_id, filing_key, effective_from)",
            "Two period rules for the same filing cannot start on the same day "
            "— which of them applied would be undefined.",
        ),
    ]

    @api.model
    def _calendar_for(self, filing_key, on_date, company):
        """The calendar in force for ``on_date``, or ``None``.

        ``None`` reaches the page as a figure it refuses to state, with the
        reason. It is not defaulted to Gregorian: defaulting is how the original
        defect got in, and a filing whose calendar nobody has recorded is a
        filing this page cannot put a period against.
        """
        if not on_date:
            return None

        def rules(domain):
            found = self.sudo().search(domain + [("filing_key", "=", filing_key)])
            return filing_status.effective_rule(
                [(item.effective_from, item.calendar) for item in found], on_date
            )

        specific = rules([("company_id", "=", company.id)])
        return specific if specific is not None else rules([("company_id", "=", False)])
