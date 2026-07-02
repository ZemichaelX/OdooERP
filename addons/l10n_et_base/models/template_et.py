# -*- coding: utf-8 -*-
"""Extensions to the core Ethiopian chart template (code 'et').

The core `l10n_et` module owns template 'et'. The chart-template loader merges the
data returned by every registered ``@template('et', model)`` function per xml id
(``dict.update``), and the code-``None`` CSV loaders (which read the OWNING module's
CSVs) run first — so the functions below both ADD records from this module's
``data/template/*.csv`` files and OVERRIDE fields of core records (e.g. the
mis-typed ``account_type`` of the core VAT/WHT accounts) without touching core files.
"""

from odoo import api, models
from odoo.addons.account.models.chart_template import template

from .l10n_et_wht_config import DEFAULT_SOURCE_NOTE, TEMPLATE_TAX_XMLID_BY_KIND

# Core l10n_et ships these accounts with the wrong account_type (and a typo'd name
# on 3006). Fresh chart loads get the fixes via the template merge; on companies
# that loaded the chart earlier, `_pre_reload_data` deliberately skips field updates
# on existing accounts, so `_l10n_et_base_reload_for_company` applies them directly.
# Codes as padded by code_digits=6.
CORE_ACCOUNT_FIXES = {
    "221200": {"account_type": "asset_current"},
    "221300": {"account_type": "asset_current"},
    "221400": {"account_type": "asset_current"},
    "300600": {"account_type": "liability_current", "name": "Withholding Tax Payable"},
    "300700": {"account_type": "liability_current"},
    "300800": {"account_type": "liability_current"},
}


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("et", "account.account")
    def _get_l10n_et_base_account_account(self):
        """New ET accounts (PAYE payable, customs clearing) + core account-type fixes."""
        return self._parse_csv("et", "account.account", module="l10n_et_base")

    @template("et", "account.tax.group")
    def _get_l10n_et_base_account_tax_group(self):
        """Tax groups for the Aug-2025 withholding rates (3% and 30%)."""
        return self._parse_csv("et", "account.tax.group", module="l10n_et_base")

    @template("et", "account.tax")
    def _get_l10n_et_base_account_tax(self):
        """Aug-2025 WHT taxes + fiscal-position mappings onto the core VAT taxes."""
        return self._parse_csv("et", "account.tax", module="l10n_et_base")

    @template("et", "account.fiscal.position")
    def _get_l10n_et_base_account_fiscal_position(self):
        """Zero-rated and VAT-exempt fiscal positions (Proc 1341/2024)."""
        return self._parse_csv("et", "account.fiscal.position", module="l10n_et_base")

    def _post_load_data(self, template_code, company, template_data):
        """Seed the effective-dated Ethiopian tax configuration on chart load."""
        result = super()._post_load_data(template_code, company, template_data)
        if template_code == "et":
            company = company or self.env.company
            self.env["l10n.et.wht.config"]._l10n_et_ensure_default(company)
            self.env["l10n.et.cash.cap.config"]._l10n_et_ensure_default(company)
        return result

    @api.model
    def _l10n_et_base_reload_for_company(self, company):
        """Bring a company that loaded chart 'et' BEFORE this module up to date.

        Creates this module's template records (accounts, tax groups, WHT taxes,
        fiscal positions), applies the core account-type fixes the reload path
        skips on existing accounts, and seeds the effective-dated configs.
        Idempotent — safe to call repeatedly (post_init hook, demo loading).
        Fresh chart loads don't need it: the template merge covers everything.
        """
        chart_template = self.with_company(company)
        data = {
            model: chart_template._parse_csv("et", model, module="l10n_et_base")
            for model in (
                "account.account",
                "account.tax.group",
                "account.tax",
                "account.fiscal.position",
            )
        }
        chart_template._deref_account_tags("et", data["account.tax"])
        chart_template._pre_reload_data(company, {}, data)
        chart_template._load_data(data)
        account_model = self.env["account.account"].with_company(company)
        for code, values in CORE_ACCOUNT_FIXES.items():
            account = account_model.search(
                [
                    *account_model._check_company_domain(company),
                    ("code", "=", code),
                ],
                limit=1,
            )
            if account:
                needed = {
                    field: value for field, value in values.items() if account[field] != value
                }
                if needed:
                    account.write(needed)
        # Re-assert the WHT kind markers: after an uninstall/reinstall cycle the
        # tax records survive (they belong to the 'account' xmlid namespace) but
        # the module's columns were dropped, and the reload path above does not
        # update fields on existing taxes.
        for kind, xmlid in TEMPLATE_TAX_XMLID_BY_KIND.items():
            tax = chart_template.ref(xmlid, raise_if_not_found=False)
            if tax:
                values = {}
                if tax.l10n_et_wht_kind != kind:
                    values["l10n_et_wht_kind"] = kind
                if not tax.l10n_et_source_note:
                    values["l10n_et_source_note"] = DEFAULT_SOURCE_NOTE
                if values:
                    tax.write(values)
        self.env["l10n.et.wht.config"]._l10n_et_ensure_default(company)
        self.env["l10n.et.cash.cap.config"]._l10n_et_ensure_default(company)
