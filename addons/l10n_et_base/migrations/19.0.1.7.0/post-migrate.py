# -*- coding: utf-8 -*-
"""Type the profit & loss accounts on databases that already exist.

Core `l10n_et` types every expense account `expense` and none
`expense_direct_cost`, so no profit & loss built on this chart can separate cost
of sales from operating expenses. `CORE_ACCOUNT_FIXES` corrects nine of them
(eight typed, `592100` deliberately left alone), and the post-init hook applies
it — but a post-init hook runs at INSTALL. A database that already has this
module never re-reads the table, and `_pre_reload_data` deliberately does not
update fields on accounts that already exist.

Without this, CI would be green on a fresh install while every existing tenant
kept a chart on which a gross profit line is impossible.

Nothing recomputes and no balance moves: `account_type` is a classification, not
an amount. Measured before shipping — the change is ALLOWED with posted entries
present, and the derived expense total was identical either side (139,993.00).
What does change is that a prior-period statement reprints WITH a gross profit
line it did not have before. Net profit is unchanged, so nothing already filed is
contradicted.

Idempotent: `_l10n_et_base_reload_for_company` writes only the fields that differ.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if version is None:
        # Fresh install: the post-init hook applies the table.
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    chart_template = env["account.chart.template"]
    for company in env["res.company"].search([("chart_template", "=", "et")]):
        chart_template._l10n_et_base_reload_for_company(company)
