# -*- coding: utf-8 -*-
"""SapianERP onboarding wizard: company profile → module picks → Ethiopian defaults.

The wizard is deliberately THIN (docs/plan-2026/06 §4, light subset): it writes
the company profile and light branding (logo + primary color — external-layout
reports and the login page pick both up from the company record), enables the
picked catalog entries, installs their Odoo modules, and lets the installed
modules' own loaders apply the Ethiopian defaults. No debranding, fonts or
terminology overrides — that is the deferred full theme.

Web-path hardening (bug-fix session, reproduced over XML-RPC):
- Applying to a company with EXISTING accounting must not crash on the ETB
  currency write or on loading chart 'et' over a foreign chart — both are
  guarded and reported as warnings on the company partner's chatter instead.
- Module installation commits the transaction mid-request; the post-install
  writes are committed explicitly too, so a later failure in the same request
  can never take them down.
- Apply and Cancel both redirect to the apps home (act_url): the wizard action
  never remains the web client's restorable URL action, which was reopening the
  dialog on refresh/company switch and leaving a blank screen behind on close.
- The logo is validated as a decodable image AT THE WIZARD (res.company.logo
  is a validated Image field — a bad file must fail here with a clear message,
  not deep inside apply).
"""

import base64
import logging

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.modules import module as module_tools
from odoo.tools.image import image_process

_logger = logging.getLogger(__name__)

HOME_ACTION = {"type": "ir.actions.act_url", "url": "/odoo", "target": "self"}


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
        help="Company logo: navbar, login page and all branded PDF reports. " "PNG or JPEG.",
    )
    primary_color = fields.Char(
        default="#1a7f5a",
        help="Primary brand color (hex), applied to the report layouts.",
    )
    module_catalog_ids = fields.Many2many(
        "sapian.module.catalog",
        string="Modules",
        help="Product modules to enable for this company (from the catalog). "
        "Picking a module also picks whatever it includes.",
    )

    @api.onchange("module_catalog_ids")
    def _onchange_module_catalog_ids(self):
        """Tick what the picked modules include, visibly.

        The consultant must SEE that choosing Ethiopian Payroll also brings the
        SapianERP core — a silent expansion at apply time would install
        something they never saw on screen. The closure is re-applied at apply
        time as well (see `action_apply`), because an onchange only fires in the
        UI: a wizard driven over RPC or from a script never triggers it, and the
        customer bought the bundle either way.
        """
        for wizard in self:
            expanded = wizard.module_catalog_ids._expand_requires()
            if expanded != wizard.module_catalog_ids:
                wizard.module_catalog_ids = [Command.set(expanded.ids)]

    @api.model
    def default_get(self, fields_list):
        """Seed the catalog and PREFILL from the company's existing values, so
        reopening the wizard never shows blanks (and re-applying never silently
        erases previously configured branding)."""
        values = super().default_get(fields_list)
        company = self.env["res.company"].browse(
            values.get("company_id") or self.env.company.id
        )
        entries = self.env["sapian.module.catalog"]._ensure_default_catalog(company)
        defaults = {
            "company_name": company.name,
            "street": company.street,
            "city": company.city or "Addis Ababa",
            "logo": company.logo,
            "module_catalog_ids": [
                Command.set(
                    (
                        entries.filtered("enabled")
                        or entries.filtered(lambda e: e.tier == "core")
                    ).ids
                )
            ],
        }
        if "primary_color" in company._fields and company.primary_color:
            defaults["primary_color"] = company.primary_color
        if "fiscalyear_last_month" in company._fields:
            defaults["fiscal_year"] = (
                "ethiopian" if company.fiscalyear_last_month == "7" else "calendar"
            )
        if "l10n_et_tin" in company.partner_id._fields:
            defaults["tin"] = company.partner_id.l10n_et_tin
        for field_name, value in defaults.items():
            if field_name in fields_list:
                values[field_name] = value
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

    @api.constrains("logo")
    def _check_logo(self):
        """Fail bad uploads HERE with a clear message: res.company.logo is a
        validated Image field, and a decode error deep inside apply rolls the
        whole onboarding back (the web-path bug users saw as 'lost' fields).
        Uses Odoo's own image pipeline so the wizard accepts exactly what the
        company field will accept — no stricter, no looser."""
        for wizard in self:
            if not wizard.logo:
                continue
            try:
                # Same call fields.Image makes on write (image_1920 behind
                # res.company.logo): bare image_process() would short-circuit.
                image_process(
                    base64.b64decode(wizard.logo),
                    size=(1920, 1920),
                    verify_resolution=True,
                )
            except Exception as error:
                raise UserError(
                    self.env._(
                        "The logo could not be read as an image (use PNG or "
                        "JPEG): %(error)s",
                        error=error,
                    )
                ) from error

    @api.model
    def action_open_onboarding(self):
        """Menu entry point: wizard for companies not yet onboarded, module
        catalog afterwards — a completed company never gets the modal again."""
        if self.env.company.sapian_onboarding_done:
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "sapian_core.action_sapian_module_catalog"
            )
            return action
        return self.env["ir.actions.act_window"]._for_xml_id(
            "sapian_core.action_sapian_onboarding_wizard"
        )

    def action_apply(self):
        """Run the onboarding end-to-end (idempotent, safe to re-run).

        Order matters: profile + branding first, then module installation
        (which COMMITS and replaces the registry), then the steps that need the
        newly installed fields/models on a fresh environment — followed by an
        explicit commit so those writes survive anything later in the request.
        Ends with a redirect to the apps home so the new company identity loads
        and the wizard action is gone from the client's URL.
        """
        self.ensure_one()
        # Capture plain values: the transient record dies with the old registry.
        company_id = self.company_id.id
        tin = self.tin
        fiscal_year = self.fiscal_year
        # Expand bundles HERE too, not only in the onchange. An onchange fires
        # in the UI and nowhere else — a wizard driven over RPC, from a
        # provisioning script or by a test would otherwise install the picked
        # modules without what they include, and the customer bought the bundle
        # in every one of those paths.
        picked = self.module_catalog_ids._expand_requires()
        if picked != self.module_catalog_ids:
            self.module_catalog_ids = [Command.set(picked.ids)]
        technical_names = self.module_catalog_ids.mapped("technical_name")

        warnings = self._apply_company_profile()
        self.module_catalog_ids.write({"enabled": True})
        env, installed = self._install_modules(technical_names)
        warnings += self._apply_ethiopian_defaults(env, company_id, tin, fiscal_year)
        company = env["res.company"].browse(company_id)
        company.sapian_onboarding_done = True
        if warnings:
            # The partner is a mail.thread: an auditable place for the parts
            # that were skipped (currency/chart guards).
            company.partner_id.message_post(
                body=env._(
                    "SapianERP onboarding completed with warnings: %(items)s",
                    items="; ".join(warnings),
                )
            )
        if installed:
            # sudo-free explicit commit: module installation already committed
            # this request's transaction once; committing the post-install
            # writes keeps them safe if anything later in the request fails.
            # Never reached in test transactions (tests pick installed modules).
            env.cr.commit()
        return dict(HOME_ACTION)

    def action_cancel(self):
        """Close the wizard onto the normal apps home — never a blank screen
        (the dialog used to be the only action the web client had loaded)."""
        return dict(HOME_ACTION)

    def _apply_company_profile(self):
        """Company identity + light branding. Returns a list of warnings for
        anything that had to be skipped (never crashes the onboarding)."""
        self.ensure_one()
        warnings = []
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
            # Odoo refuses a currency change once journal items exist — a real
            # constraint we must respect, not crash on (web-path bug: the whole
            # onboarding rolled back on established demo companies).
            has_entries = "account.move.line" in self.env and self.env[
                "account.move.line"
            ].sudo().search_count([("company_id", "=", company.id)])
            if has_entries:
                warnings.append(
                    self.env._(
                        "currency left as %(currency)s — journal items already "
                        "exist, so it cannot be switched to ETB",
                        currency=company.currency_id.name,
                    )
                )
            else:
                company.currency_id = etb
        return warnings

    def _install_modules(self, technical_names):
        """Install the picked modules; return (fresh_env, installed_flag).

        ``button_immediate_install`` commits and rebuilds the registry;
        everything held from before (including this wizard record) is stale
        afterwards — callers must only use the returned environment and plain
        captured values.
        """
        modules = (
            self.env["ir.module.module"]
            .sudo()  # module install is admin-only; the menu is group_system
            .search([("name", "in", technical_names), ("state", "=", "uninstalled")])
        )
        if not modules:
            return self.env(), False
        # Odoo forbids module operations while the registry is loading (demo
        # data, module install) or inside tests — core raises there, which is
        # an opaque failure for a demo/test that merely picked an uninstalled
        # app. Neither condition can hold during real onboarding (a live
        # request has a ready registry), so runtime behaviour is unchanged:
        # skip the install and say which apps were left alone.
        if not self.env.registry.ready or self.env.registry._init or module_tools.current_test:
            _logger.warning(
                "SapianERP onboarding: registry cannot perform module operations "
                "(loading or test mode); skipped installing %s. Add them to the "
                "calling module's manifest dependencies instead.",
                ", ".join(sorted(modules.mapped("name"))),
            )
            return self.env(), False
        modules.button_immediate_install()
        self.env.transaction.reset()
        return self.env(), True

    @api.model
    def _apply_ethiopian_defaults(self, env, company_id, tin, fiscal_year):
        """Post-install configuration that needs the installed modules.

        Chart 'et' is only loaded on companies WITHOUT a chart: loading it over
        an existing foreign chart is undefined territory (and crashes with
        existing accounting) — skipped with a warning instead. Returns the list
        of warnings.
        """
        warnings = []
        company = env["res.company"].browse(company_id)
        if "account.chart.template" in env:
            if not company.chart_template:
                env["account.chart.template"].try_loading("et", company, install_demo=False)
            elif company.chart_template != "et":
                warnings.append(
                    env._(
                        "existing chart of accounts '%(chart)s' kept — Ethiopian "
                        "accounting defaults were NOT loaded (use a fresh company "
                        "for a full Ethiopian setup)",
                        chart=company.chart_template,
                    )
                )
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
        return warnings
