# -*- coding: utf-8 -*-
"""Effective-dated pension configuration (rates + optional insurable cap)."""
from odoo import fields, models


class L10nEtPensionConfig(models.Model):
    _name = "l10n.et.pension.config"
    _description = "Ethiopian Pension Configuration"
    _order = "effective_from desc"

    name = fields.Char(default="Pension Configuration")
    employee_rate = fields.Float(string="Employee Rate", default=0.07)
    employer_rate = fields.Float(string="Employer Rate", default=0.11)
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
