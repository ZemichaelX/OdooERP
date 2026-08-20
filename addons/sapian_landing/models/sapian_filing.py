# -*- coding: utf-8 -*-
"""That a return was actually submitted. The one fact no report holds.

WHY THIS MODEL EXISTS, STATED PLAINLY
--------------------------------------
The landing page is asked to show whether each filing is "filed, due or late".
Due and late come from a date. **Filed does not exist anywhere in this product**
— not on the VAT declaration, not on the withholding summary, not on the payroll
run, whose `state` means "payslips confirmed and posted", not "declared to the
Ministry of Revenues". Those are different events, weeks apart.

So either the page never says "filed", or somebody records it. This is the
smallest thing that can be recorded: who filed what, for which period, on which
day, with the receipt reference. It is deliberately NOT derived from anything —
a derived "filed" would be a guess about a government's inbox.

It is also the only writable model this feature adds. Everything else on the
page is read from a report that already existed.
"""

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SapianFiling(models.Model):
    _name = "sapian.filing"
    _description = "Statutory Filing Submitted"
    _order = "period_end desc, filing_key"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
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
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True, index=True)
    filed_on = fields.Date(
        required=True,
        default=fields.Date.context_today,
        help="The day the return went in. Not the day it was prepared.",
    )
    reference = fields.Char(
        help="The receipt or acknowledgement number the authority returned. "
        "Optional, because a filing is filed whether or not the number was "
        "written down — but it is what an audit asks for.",
    )
    filed_by_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        help="Who recorded it, which is not necessarily who submitted it.",
    )

    _sql_constraints = [
        (
            "one_filing_per_period",
            "unique(company_id, filing_key, period_end)",
            "This filing has already been recorded for that period.",
        ),
    ]

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for filing in self:
            if filing.period_start > filing.period_end:
                raise ValidationError(self.env._("The period start must be before its end."))

    @api.model
    def _filed_on_for(self, filing_key, period_end, company):
        """The submission date for one period, or ``False``."""
        record = self.sudo().search(
            [
                ("company_id", "=", company.id),
                ("filing_key", "=", filing_key),
                ("period_end", "=", period_end),
            ],
            limit=1,
        )
        return record.filed_on or False
