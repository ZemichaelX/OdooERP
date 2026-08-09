# -*- coding: utf-8 -*-
"""Effective-dated pension configuration (rates + optional insurable cap)."""

from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .payslip_compute import _calc

# Commencement of the seeded 7%/11% split. Unlike PAYE, the pension rates did
# NOT change at the 1395/2025 boundary, so no payslip computes differently
# either way — but 2024-07-01 (the old value, copied from the PAYE seed) was
# still an unsupported assertion about when these rates began.
#
# The Private Organisation Employees' Pension Proclamation No. 715/2011 did NOT
# introduce 7%/11% outright: Article 57 PHASES the contributions from
# commencement on 8 July 2011 —
#     employee  yr1 5%   yr2 6%   yr3+ 7%
#     employer  yr1 7%   yr2 8%   yr3 9%   yr4+ 11%
# so 7% and 11% first coincide in year four, from 8 July 2014. That is the
# earliest date at which the rates we seed were actually the law, and it is
# what we assert. Proclamation No. 1268/2022 carries the same rates forward and
# now governs (CLAUDE.md cites it for the nationality rules).
#
# The 2011–2014 transitional generations are DELIBERATELY not modelled: they
# fall outside the supported range, and half-modelling them would assert rate
# history we have not verified. Asserting less is fine; asserting wrong is not.
# TODO: confirm the commencement and phase-in dates against the Negarit Gazeta.
SEED_EFFECTIVE_FROM = date(2014, 7, 8)


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

    @api.model
    def _l10n_et_ensure_default(self, company):
        """Seed the default 7%/11% uncapped pension config for ``company`` if it
        has none (per-company, like the PAYE band seeder — A1). Idempotent; a
        company that already has a config is left untouched."""
        if self.sudo().search_count([("company_id", "=", company.id)]):
            return
        self.sudo().create(
            {
                "company_id": company.id,
                "name": "Ethiopia Pension (default 7%/11%)",
                "employee_rate": _calc.DEFAULT_PENSION_EMPLOYEE_RATE,
                "employer_rate": _calc.DEFAULT_PENSION_EMPLOYER_RATE,
                "insurable_cap": 0.0,
                "effective_from": SEED_EFFECTIVE_FROM,
            }
        )

    @api.model
    def _l10n_et_seed_all_companies(self):
        """Data-file/migration hook: seed every active company's pension config."""
        for company in self.env["res.company"].search([("active", "=", True)]):
            self._l10n_et_ensure_default(company)
        return True
