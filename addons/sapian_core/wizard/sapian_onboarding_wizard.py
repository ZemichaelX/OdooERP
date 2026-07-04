# -*- coding: utf-8 -*-
"""SapianERP onboarding wizard: company profile → module picks → Ethiopian defaults.

The wizard is deliberately THIN (docs/plan-2026/06 §4, light subset): it writes
the company profile and light branding (logo + primary color — external-layout
reports and the login page pick both up from the company record), enables the
picked catalog entries, installs their Odoo modules, and lets the installed
modules' own loaders apply the Ethiopian defaults (chart 'et' with taxes and
account fixes, WHT/cash-cap configs, payroll accounts). No debranding, fonts or
terminology overrides — that is the deferred full theme.
"""

from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class SapianOnboardingWizard(models.TransientModel):
    _name = "sapian.onboarding.wizard"
    _description = "SapianERP Onboarding Wizard"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        help="The company being onboarded.",
    )
    company_name = fields.Char(
        required=True,
        default=lambda self: self.env.company.name,
        help="Legal company name (appears on all documents).",
    )
    tin = fields.Char(
        string="Company TIN",
        size=13,
        help="Ministry of Revenue TIN — printed on invoices, declarations and "
        "payslips. Validated once the Ethiopian accounting module is installed.",
    )
    street = fields.Char(help="Head-office street address.")
    city = fields.Char(default="Addis Ababa")
    fiscal_year = fields.Selection(
        selection=[
            ("calendar", "Calendar year (ends 31 December)"),
            ("ethiopian", "Ethiopian fiscal year (ends 7 July)"),
        ],
        required=True,
        default="calendar",
        help="Sets the accounting fiscal year end (docs/plan-2026/07 §4).",
    )
    logo = fields.Binary(
        help="Company logo: navbar, login page and all branded PDF reports.",
    )
    primary_color = fields.Char(
        default="#1a7f5a",
        help="Primary brand color (hex), applied to the report layouts.",
    )
    module_catalog_ids = fields.Many2many(
        "sapian.module.catalog",
        string="Modules",
        help="Product modules to enable for this company (from the catalog).",
    )

    @api.model
    def default_get(self, fields_list):
        """Seed the standard catalog for the company and preselect the core tier."""
        values = super().default_get(fields_list)
        company = self.env["res.company"].browse(
            values.get("company_id") or self.env.company.id
        )
        entries = self.env["sapian.module.catalog"]._ensure_default_catalog(company)
        if "module_catalog_ids" in fields_list:
            values["module_catalog_ids"] = [
                Command.set(entries.filtered(lambda e: e.tier == "core").ids)
            ]
        return values

    @api.constrains("primary_color")
    def _check_primary_color(self):
        """Only hex colors reach the report stylesheets."""
        for wizard in self:
            color = wizard.primary_color
            if color and not (
                color.startswith("#")
                and len(color) == 7
                and all(char in "0123456789abcdefABCDEF" for char in color[1:])
            ):
                raise UserError(
                    self.env._("The primary color must be a hex value like #1a7f5a.")
                )

    def action_apply(self):
        """Run the onboarding end-to-end (idempotent, safe to re-run).

        Order matters: profile + branding first (registry-independent), then
        module installation (which REPLACES the registry), then the steps that
        need the newly installed fields/models — Ethiopian chart, TIN, fiscal
        year — on a fresh environment.
        """
        self.ensure_one()
        # Capture plain values: the transient record dies with the old registry.
        company_id = self.company_id.id
        tin = self.tin
        fiscal_year = self.fiscal_year
        technical_names = self.module_catalog_ids.mapped("technical_name")

        self._apply_company_profile()
        self.module_catalog_ids.write({"enabled": True})
        env = self._install_modules(technical_names)
        self._apply_ethiopian_defaults(env, company_id, tin, fiscal_year)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": self.env._("Onboarding complete"),
                "message": self.env._(
                    "Company configured, %(count)s module(s) enabled and "
                    "Ethiopian defaults applied.",
                    count=len(technical_names),
                ),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _apply_company_profile(self):
        """Company identity + light branding (no installed-module dependencies)."""
        self.ensure_one()
        company = self.company_id
        values = {
            "name": self.company_name,
            "street": self.street,
            "city": self.city,
            "country_id": self.env.ref("base.et").id,
        }
        if self.logo:
            values["logo"] = self.logo
        # primary/secondary drive the standard external report layouts.
        if self.primary_color and "primary_color" in company._fields:
            values["primary_color"] = self.primary_color
            values["secondary_color"] = self.primary_color
        company.write(values)
        etb = self.env.ref("base.ETB")
        if not etb.active:
            etb.active = True
        if company.currency_id != etb:
            company.currency_id = etb

    def _install_modules(self, technical_names):
        """Install the picked modules and return a FRESH environment.

        ``button_immediate_install`` rebuilds the registry; everything held from
        before (including this wizard record) is stale afterwards — callers must
        only use the returned environment and plain captured values.
        """
        modules = (
            self.env["ir.module.module"]
            .sudo()  # module install is admin-only; the menu is group_system
            .search([("name", "in", technical_names), ("state", "=", "uninstalled")])
        )
        if not modules:
            return self.env()
        modules.button_immediate_install()
        self.env.transaction.reset()
        return self.env()

    @api.model
    def _apply_ethiopian_defaults(self, env, company_id, tin, fiscal_year):
        """Post-install configuration that needs the installed modules.

        Chart 'et' loading triggers the l10n_et_base seeding (_post_load_data);
        the fiscal-year fields and the TIN field only exist once account /
        l10n_et_base are in.
        """
        company = env["res.company"].browse(company_id)
        if "account.chart.template" in env and company.chart_template != "et":
            env["account.chart.template"].try_loading("et", company, install_demo=False)
        if "fiscalyear_last_month" in company._fields:
            company.write(
                {
                    "fiscalyear_last_month": "7" if fiscal_year == "ethiopian" else "12",
                    "fiscalyear_last_day": 7 if fiscal_year == "ethiopian" else 31,
                }
            )
        partner = company.partner_id
        if tin and "l10n_et_tin" in partner._fields:
            partner.l10n_et_tin = tin
        return True
