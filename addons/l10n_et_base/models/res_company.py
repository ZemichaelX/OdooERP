# -*- coding: utf-8 -*-
"""Per-company Ethiopian tax-engine scope and configuration seeding.

Mirrors the A1 fix already applied to payroll: every company owns real,
effective-dated WHT and cash-cap configuration records, seeded on creation, so
the engines never fall back to "no configuration = do nothing". The scope flag
decides which companies the engines apply to at all — see the field help.
"""

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_et_tax_engine_active = fields.Boolean(
        string="Ethiopian Tax Engine",
        compute="_compute_l10n_et_tax_engine_active",
        store=True,
        readonly=False,
        help="Apply Ethiopian withholding and cash-cap rules in this company. "
        "Turn off only for companies with no Ethiopian fiscal setup, or "
        "non-Ethiopian companies. Defaults from the company country; note that "
        "re-saving the country resets it to that default.",
    )

    @api.depends("country_id")
    def _compute_l10n_et_tax_engine_active(self):
        """Default the engine on for Ethiopian companies.

        Computed rather than a plain default because provisioning creates the
        company FIRST and sets the country afterwards (the onboarding wizard,
        scripts/provision_client.sh): a create-time default would leave every
        wizard-provisioned Ethiopian tenant out of scope.
        """
        ethiopia = self.env.ref("base.et", raise_if_not_found=False)
        for company in self:
            company.l10n_et_tax_engine_active = bool(
                ethiopia and company.country_id == ethiopia
            )

    @api.model_create_multi
    def create(self, vals_list):
        """Seed the per-company WHT and cash-cap configuration immediately.

        Without this the configs were only seeded when chart 'et' loaded, so a
        group's second company or a SaaS tenant provisioned another way had NO
        configuration — and both engines treated that as "stay inert", posting
        vendor bills with no withholding and cash payments with no cap check,
        silently. Seeding runs for every company (cheap, idempotent); whether
        the engines then act is decided by l10n_et_tax_engine_active.
        """
        companies = super().create(vals_list)
        wht_config = self.env["l10n.et.wht.config"].sudo()
        cash_cap_config = self.env["l10n.et.cash.cap.config"].sudo()
        levy_config = self.env["l10n.et.social.welfare.levy.config"].sudo()
        for company in companies:
            wht_config._l10n_et_ensure_default(company)
            cash_cap_config._l10n_et_ensure_default(company)
            levy_config._l10n_et_ensure_default(company)
        return companies
