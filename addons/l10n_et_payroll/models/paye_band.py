# -*- coding: utf-8 -*-
"""Effective-dated PAYE bands. Rates are configuration data, not code (CLAUDE.md rule #4)."""

from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


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
    deduction = fields.Float(required=True, default=0.0)
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

    @api.constrains(
        "lower_bound",
        "upper_bound",
        "is_top_band",
        "effective_from",
        "effective_to",
        "company_id",
    )
    def _check_no_overlap(self):
        """PAYE for a given income on a given date must be unambiguous: no two
        bands of the same company may overlap in BOTH the effective window AND
        the income interval. Forgetting to close the old generation's
        ``effective_to`` when seeding a new one would otherwise make
        ``compute_paye`` return whichever row sorts first."""
        for band in self:
            band_to = band.effective_to or date.max
            band_hi = None if band.is_top_band else band.upper_bound
            others = self.search(
                [
                    ("id", "!=", band.id),
                    ("company_id", "=", band.company_id.id),
                    ("effective_from", "<=", band_to),
                    "|",
                    ("effective_to", "=", False),
                    ("effective_to", ">=", band.effective_from),
                ]
            )
            for other in others:
                other_hi = None if other.is_top_band else other.upper_bound
                # Half-open income intervals (lower exclusive, upper inclusive)
                # overlap when each starts below the other's ceiling.
                low_below_other_hi = other_hi is None or band.lower_bound < other_hi
                other_low_below_hi = band_hi is None or other.lower_bound < band_hi
                if low_below_other_hi and other_low_below_hi:
                    raise ValidationError(
                        self.env._(
                            "PAYE bands overlap in time and income for the same "
                            "company (%(a)s vs %(b)s). Close the old band's "
                            "effective-to date before adding the new one.",
                            a=band.name,
                            b=other.name,
                        )
                    )

    @api.model
    def get_active_bands(self, on_date=None, company=None):
        """Return active bands as the tuple list the reference calculator expects."""
        on_date = on_date or fields.Date.context_today(self)
        company = company or self.env.company
        domain = [
            ("company_id", "=", company.id),
            ("effective_from", "<=", on_date),
            "|",
            ("effective_to", "=", False),
            ("effective_to", ">=", on_date),
        ]
        bands = self.search(domain, order="lower_bound asc")
        return [
            (b.lower_bound, None if b.is_top_band else b.upper_bound, b.rate, b.deduction)
            for b in bands
        ]
