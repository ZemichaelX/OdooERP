# -*- coding: utf-8 -*-
"""Effective-dated PAYE bands. Rates are configuration data, not code (CLAUDE.md rule #4)."""

from datetime import date, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .payslip_compute import _calc

# Commencement of the CURRENT generation: Income Tax (Amendment) Proclamation
# No. 1395/2025, in force 8 July 2025 (see reference/et_payroll_calc.py for the
# citation). It was previously seeded as 2024-07-01 — twelve months before the
# proclamation existed — which computed the 2025 (more generous) bands for
# every payslip in the gap and so UNDERSTATED PAYE, the employer's liability at
# assessment. A future proclamation is a NEW generation of records with a later
# effective_from (and the previous one's effective_to closed) — never an edit
# to these, so historical payslips stay reproducible.
SEED_EFFECTIVE_FROM = _calc.PAYE_1395_2025_EFFECTIVE_FROM


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

    @api.model
    def _l10n_et_ensure_default(self, company):
        """Seed the standard PAYE bands for ``company`` if it has none.

        Values come from the reference calculator (``et_payroll_calc`` — the
        single source of truth the fast goldens test); this is the per-company
        analogue of the WHT/cash-cap/allowance seeders, so EVERY company (not
        just the one active at module install) gets real, effective-dated
        configuration records instead of relying on a code fallback (A1).
        Idempotent: a company that already has any band is left untouched, so a
        client that tuned its bands is never overwritten.
        """
        has_any = (
            self.sudo()
            .with_context(active_test=False)
            .search_count([("company_id", "=", company.id)])
        )
        if has_any:
            return
        self.sudo().create(self._l10n_et_seed_values(company))

    @api.model
    def _l10n_et_seed_values(self, company):
        """Create-values for EVERY known PAYE generation, oldest first.

        Seeding only the current generation left the table unable to answer
        "what was the tax in May 2025?" — one rate set with a date column, not
        an effective-dated table. Each generation is closed the day before the
        next one commences so the date windows never overlap.
        """
        generations = _calc.PAYE_BAND_GENERATIONS
        vals = []
        for index, generation in enumerate(generations):
            following = generations[index + 1] if index + 1 < len(generations) else None
            effective_to = following.effective_from - timedelta(days=1) if following else False
            vals.extend(
                {
                    "company_id": company.id,
                    "lower_bound": lower,
                    "upper_bound": 0.0 if upper is None else upper,
                    "is_top_band": upper is None,
                    "rate": rate,
                    "deduction": deduction,
                    "effective_from": generation.effective_from,
                    "effective_to": effective_to,
                }
                for lower, upper, rate, deduction in generation.bands
            )
        return vals

    @api.model
    def _l10n_et_seed_active_companies(self):
        """Data-file/migration hook: seed every ACTIVE company's PAYE bands.

        Archived companies are deliberately skipped: they run no payroll, and
        if one is ever unarchived the missing configuration RAISES (A1) rather
        than falling back to code constants — loud, not silent. The name says
        "active" because that is what it does; an earlier name claimed "all"
        while filtering on active, which is the kind of lie that hides bugs.
        Note this is about rows EXISTING; that rows which exist carry the right
        commencement date is a separate invariant, enforced by the migration's
        post-condition across every company, archived included.
        """
        for company in self.env["res.company"].search([("active", "=", True)]):
            self._l10n_et_ensure_default(company)
        return True
