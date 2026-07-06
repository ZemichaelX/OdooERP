# -*- coding: utf-8 -*-
"""Effective-dated pension configuration (rates + optional insurable cap)."""

from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class L10nEtPensionConfig(models.Model):
    _name = "l10n.et.pension.config"
    _description = "Ethiopian Pension Configuration"
    _order = "effective_from desc"

    name = fields.Char(default="Pension Configuration")
    employee_rate = fields.Float(default=0.07)
    employer_rate = fields.Float(default=0.11)
    insurable_cap = fields.Float(
        string="Monthly Insurable Cap",
        default=0.0,
        help="Optional cap on the pensionable base. 0 = uncapped.",
    )
    effective_from = fields.Date(required=True, default=fields.Date.context_today)
    effective_to = fields.Date()
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True
    )

    @api.constrains("effective_from", "effective_to", "company_id")
    def _check_no_overlap(self):
        """The applicable pension rate on any date must be unambiguous — a new
        generation seeded without closing the old one's effective-to would
        otherwise make the rate selection order-dependent."""
        for config in self:
            domain = [
                ("id", "!=", config.id),
                ("company_id", "=", config.company_id.id),
                ("effective_from", "<=", config.effective_to or date.max),
                "|",
                ("effective_to", "=", False),
                ("effective_to", ">=", config.effective_from),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    self.env._(
                        "Pension configurations must not overlap in time for "
                        "the same company."
                    )
                )
