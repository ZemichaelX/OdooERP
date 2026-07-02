# -*- coding: utf-8 -*-
"""Effective-dated PAYE bands. Rates are configuration data, not code (CLAUDE.md rule #4)."""
from odoo import fields, models, api


class L10nEtPayeBand(models.Model):
    _name = "l10n.et.paye.band"
    _description = "Ethiopian PAYE Tax Band"
    _order = "effective_from desc, lower_bound asc"

    name = fields.Char(compute="_compute_name", store=True)
    lower_bound = fields.Float(string="From (exclusive)", required=True)
    upper_bound = fields.Float(
        string="To (inclusive)", help="Leave 0 for the top band (and above)."
    )
    is_top_band = fields.Boolean(string="Top Band (and above)", default=False)
    rate = fields.Float(string="Rate (fraction)", required=True, help="e.g. 0.15 for 15%.")
    deduction = fields.Float(string="Deduction", required=True, default=0.0)
    effective_from = fields.Date(required=True, default=fields.Date.context_today)
    effective_to = fields.Date()
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True
    )

    @api.depends("lower_bound", "upper_bound", "is_top_band", "rate")
    def _compute_name(self):
        for b in self:
            hi = "and above" if b.is_top_band else f"{b.upper_bound:,.0f}"
            b.name = f"{b.lower_bound:,.0f}–{hi} @ {b.rate * 100:.0f}%"

    @api.model
    def get_active_bands(self, on_date=None, company=None):
        """Return active bands as the tuple list the reference calculator expects."""
        on_date = on_date or fields.Date.context_today(self)
        company = company or self.env.company
        domain = [
            ("company_id", "=", company.id),
            ("effective_from", "<=", on_date),
            "|", ("effective_to", "=", False), ("effective_to", ">=", on_date),
        ]
        bands = self.search(domain, order="lower_bound asc")
        return [
            (b.lower_bound, None if b.is_top_band else b.upper_bound, b.rate, b.deduction)
            for b in bands
        ]
