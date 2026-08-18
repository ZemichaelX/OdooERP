# -*- coding: utf-8 -*-
"""Move existing companies off core l10n_et's transit-account expense default.

Core `l10n_et` maps the company's default expense account to 2301 "Goods in
Transit", an `asset_current` account, and Odoo's chart loader copies that into
`ir.default` for product categories. Every product without an account of its own
therefore books purchases into a current asset, the profit & loss account shows
revenue with no cost of sales, and nothing complains because the books still
balance. See `models/template_et.py` and defect register entry 26.

Fresh chart loads take the corrected value from the template merge. A database
that already loaded the chart never re-reads it — this is the rule this repo
keeps meeting: a template change applies at INSTALL and is skipped at UPGRADE, so
CI would be green while every existing tenant kept the defect.

Conservative by construction: `_l10n_et_base_fix_default_expense_account` moves
only companies still sitting on the CORE default, so a client who has chosen
their own expense account is left alone.

Idempotent.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if version is None:
        # Fresh install: the template merge already supplies the right account.
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    chart_template = env["account.chart.template"]
    for company in env["res.company"].search([("chart_template", "=", "et")]):
        chart_template._l10n_et_base_fix_default_expense_account(company)
