# -*- coding: utf-8 -*-
"""Extensions to the core Ethiopian chart template (code 'et').

The core `l10n_et` module owns template 'et'. The chart-template loader merges the
data returned by every registered ``@template('et', model)`` function per xml id
(``dict.update``), and the code-``None`` CSV loaders (which read the OWNING module's
CSVs) run first — so the functions below both ADD records from this module's
``data/template/*.csv`` files and OVERRIDE fields of core records (e.g. the
mis-typed ``account_type`` of the core VAT/WHT accounts) without touching core files.
"""

import logging

from odoo import api, models
from odoo.addons.account.models.chart_template import template

from .l10n_et_social_welfare_levy_config import DEFAULT_SOURCE_NOTE as SWL_SOURCE_NOTE
from .l10n_et_social_welfare_levy_config import TEMPLATE_TAX_XMLID as SWL_TEMPLATE_TAX_XMLID
from .l10n_et_wht_config import DEFAULT_SOURCE_NOTE, TEMPLATE_TAX_XMLID_BY_KIND

_logger = logging.getLogger(__name__)

# Core l10n_et ships these accounts with the wrong account_type (and a typo'd name
# on 3006). Fresh chart loads get the fixes via the template merge; on companies
# that loaded the chart earlier, `_pre_reload_data` deliberately skips field updates
# on existing accounts, so `_l10n_et_base_reload_for_company` applies them directly.
# Codes as padded by code_digits=6.
# Core l10n_et maps the company's DEFAULT EXPENSE ACCOUNT to 2301 "Goods in
# Transit" — an `asset_current` account — in the `expense_account_id` key of
# `_get_et_res_company` (odoo/addons/l10n_et/models/template_et.py). That default
# is the last link of the chain `_get_product_accounts` walks:
#
#     product.property_account_expense_id
#       -> category property_account_expense_categ_id   (seeded from the company
#                                                        default via ir.default at
#                                                        chart load)
#       -> company.expense_account_id                   <- the transit account
#
# so EVERY product that carries no account of its own — which is every product a
# client imports — books its purchases into a current asset. Odoo's generic chart
# loader also copies `company.expense_account_id` into `ir.default` for
# `product.category.property_account_expense_categ_id`, so both surviving links of
# the chain point at the same wrong account.
#
# WHY THIS MATTERS MORE THAN IT LOOKS: the books still balance. A balanced ledger
# cannot tell a misclassified debit from a correct one, so nothing complains. What
# breaks is the profit & loss account, which shows revenue with no cost of sales,
# and the balance sheet, which carries a transit balance that only grows. Measured
# on a demo tenant: 230100 at 453,800.00 with the inventory-valuation journal
# empty, and a single 54,000.00 purchase overstating reported profit by 54,000.00.
#
# NOT OUR BUG, AND NOT ONLY OUR PROBLEM: it ships in Odoo's own Ethiopian
# localisation, so every Odoo-based Ethiopian deployment has it, competitors
# included. Reported upstream (see README). We never modify l10n_et, so we correct
# it the same way we correct the mis-typed core accounts below — through the
# template merge for fresh chart loads, and directly for companies that loaded the
# chart before this module.
CORE_EXPENSE_ACCOUNT_XMLID = "l10n_et2301"  # 230100 Goods in Transit, asset_current
DEFAULT_EXPENSE_ACCOUNT_XMLID = "l10n_et5111"  # 511100 Cost of Goods and Services, expense

CORE_ACCOUNT_FIXES = {
    "221200": {"account_type": "asset_current"},
    "221300": {"account_type": "asset_current"},
    "221400": {"account_type": "asset_current"},
    "300600": {"account_type": "liability_current", "name": "Withholding Tax Payable"},
    "300700": {"account_type": "liability_current"},
    "300800": {"account_type": "liability_current"},
}

# Core l10n_et ships withholding taxes at rates Ethiopian law does not support.
# They sit in the same selection list as our correct ones, so an accountant
# raising a vendor bill is offered six withholding options of which two are
# wrong. Nothing crashes: the WHT summary then reports the wrong figure
# *correctly*, which is the silent-failure shape this repo keeps meeting.
#
#   2% WH  — the domestic withholding rate has been 3% since the Aug 2025
#            change; 2% is the superseded rate. Choosing it UNDER-withholds.
#   35% WH — no 35% withholding rate exists in Ethiopian law at all. The
#            punitive no-TIN/no-licence rate is 30%. (35% is the top PAYE
#            marginal band, which is probably where it came from.)
#
# Verified against odoo/addons/l10n_et/data/template/account.tax-et.csv at
# Odoo 19 and corroborated by PwC's Ethiopia withholding-tax summary.
#
# DEACTIVATED, NOT DELETED OR RENAMED. Bills already posted under the old 2%
# must keep their tax record: the move lines reference it, and the WHT summary
# reads it back to report history. active=False removes a tax from selection
# on NEW documents while leaving every existing line intact and reportable.
# Deleting would orphan those lines; renaming would silently restate history.
#
# Not our rates to fix upstream: we never modify l10n_et.
CORE_TAX_DEACTIVATIONS = {
    "id_tax02": "2% WH (sale) — superseded by the 3% domestic rate, Aug 2025",
    "id_tax05": "2% WH (purchase) — superseded by the 3% domestic rate, Aug 2025",
    "id_tax13": "35% WH (sale) — no such Ethiopian withholding rate exists",
    "id_tax12": "35% WH (purchase) — no such Ethiopian withholding rate exists",
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

    @template("et", "res.company")
    def _get_l10n_et_base_res_company(self):
        """Point the company's default expense account at cost of sales.

        Overrides core l10n_et's `expense_account_id` (see the module-level note
        on CORE_EXPENSE_ACCOUNT_XMLID). The loader merges per xml id with
        ``dict.update``, and ``getmembers`` orders the registered template
        functions by attribute name, so ``_get_l10n_et_base_res_company`` runs
        after core's ``_get_et_res_company`` and this single key wins while every
        other company value core sets is left untouched.
        """
        return {
            self.env.company.id: {
                "expense_account_id": DEFAULT_EXPENSE_ACCOUNT_XMLID,
            },
        }

    @api.model
    def _l10n_et_base_fix_default_expense_account(self, company):
        """Repoint an existing company's default expense account, and its default.

        Fresh chart loads are covered by the template merge above; a company that
        loaded chart 'et' before this version keeps the transit account both on
        ``res.company.expense_account_id`` and in the ``ir.default`` row the chart
        loader copied it into. Both are moved here.

        Deliberately conservative: only a company still sitting on the CORE
        default is moved. A client who has chosen their own expense account —
        including one who has already corrected this by hand — is left alone,
        because this is a defaulting fix and not an opinion about their chart.
        Idempotent, so the post_init hook and the migration can both call it.

        Returns the companies actually moved, so a caller can assert the work
        happened rather than assume it.
        """
        chart_template = self.with_company(company)
        transit = chart_template.ref(CORE_EXPENSE_ACCOUNT_XMLID, raise_if_not_found=False)
        cost_of_sales = chart_template.ref(
            DEFAULT_EXPENSE_ACCOUNT_XMLID, raise_if_not_found=False
        )
        if not cost_of_sales:
            # No target account: leave the company as it is rather than guess.
            _logger.warning(
                "l10n_et_base: %s not found for %s; the default expense account "
                "was left unchanged.",
                DEFAULT_EXPENSE_ACCOUNT_XMLID,
                company.display_name,
            )
            return self.env["res.company"]

        moved = self.env["res.company"]
        current = company.expense_account_id
        if not current or (transit and current == transit):
            company.expense_account_id = cost_of_sales
            moved |= company

        # The chart loader copies the company default into ir.default for product
        # categories; that copy does not follow the company field afterwards.
        ir_default = self.env["ir.default"].sudo()
        category_default = ir_default._get(
            "product.category", "property_account_expense_categ_id", company_id=company.id
        )
        if not category_default or (transit and category_default == transit.id):
            ir_default.set(
                "product.category",
                "property_account_expense_categ_id",
                cost_of_sales.id,
                company_id=company.id,
            )
            moved |= company
        return moved

    def _post_load_data(self, template_code, company, template_data):
        """Seed the effective-dated Ethiopian tax configuration on chart load."""
        result = super()._post_load_data(template_code, company, template_data)
        if template_code == "et":
            company = company or self.env.company
            self.env["l10n.et.wht.config"]._l10n_et_ensure_default(company)
            self.env["l10n.et.cash.cap.config"]._l10n_et_ensure_default(company)
            self.env["l10n.et.social.welfare.levy.config"]._l10n_et_ensure_default(company)
            self._l10n_et_base_deactivate_unsupported_core_taxes(company)
        return result

    @api.model
    def _l10n_et_base_deactivate_unsupported_core_taxes(self, company):
        """Take the unsupported core withholding rates out of selection.

        Called from BOTH paths — `_post_load_data` for a fresh chart load and
        `_l10n_et_base_reload_for_company` for a company that loaded chart 'et'
        earlier. Deliberately ONE implementation rather than the CSV-override
        trick used for account fields: the two paths must not be able to drift,
        and a company at a client site reaches this through the reload path,
        which is the one that actually matters.

        Idempotent, and it only ever deactivates. A tax someone re-enabled by
        hand is deactivated again on the next upgrade, on purpose: these rates
        are not a preference. If a proclamation ever reinstates one, it comes
        out of this dict with a citation — not from a manual toggle nobody
        wrote down.

        Returns the taxes it changed, so callers and tests can assert on the
        work done rather than on the absence of an error.
        """
        chart_template = self.with_company(company)
        deactivated = self.env["account.tax"]
        for xmlid, reason in CORE_TAX_DEACTIVATIONS.items():
            # active_test=False: once deactivated, a plain ref() will not find
            # the record again, and the second run would silently do nothing
            # while looking successful.
            tax = chart_template.with_context(active_test=False).ref(
                xmlid, raise_if_not_found=False
            )
            if tax and tax.active:
                tax.active = False
                deactivated |= tax
                _logger.info(
                    "l10n_et_base: deactivated core tax %s on company %s — %s",
                    xmlid,
                    company.display_name,
                    reason,
                )
        return deactivated

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
        # The social welfare levy's base is the CIF value and NOTHING else, so
        # the tax must not be affected by taxes sequenced before it and must not
        # enter the base of taxes sequenced after it. Both are set in the
        # template CSV, and both are re-asserted here for the same reason the
        # WHT markers above are: `_pre_reload_data` does not update fields on
        # taxes that already exist, so a database that installed an earlier
        # version keeps Odoo's default `is_base_affected = True` and would
        # compute the levy on CIF + duty. Measured on an upgraded database
        # before this block existed.
        levy_tax = chart_template.ref(SWL_TEMPLATE_TAX_XMLID, raise_if_not_found=False)
        if levy_tax:
            base_values = {
                field: value
                for field, value in (
                    ("is_base_affected", False),
                    ("include_base_amount", False),
                )
                if levy_tax[field] != value
            }
            if base_values:
                levy_tax.write(base_values)
            if not levy_tax.l10n_et_source_note:
                levy_tax.write({"l10n_et_source_note": SWL_SOURCE_NOTE})
        self.env["l10n.et.wht.config"]._l10n_et_ensure_default(company)
        self.env["l10n.et.cash.cap.config"]._l10n_et_ensure_default(company)
        self.env["l10n.et.social.welfare.levy.config"]._l10n_et_ensure_default(company)
        # Same call as the fresh-load path. A client site reaches the fix here.
        self._l10n_et_base_deactivate_unsupported_core_taxes(company)
        # The transit-account default: fresh loads get it from the template merge,
        # existing companies only from here.
        self._l10n_et_base_fix_default_expense_account(company)
