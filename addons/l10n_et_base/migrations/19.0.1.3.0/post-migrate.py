# -*- coding: utf-8 -*-
"""Deactivate the core withholding taxes Ethiopian law does not support.

Core `l10n_et` ships 2% WH (id_tax02/id_tax05) and 35% WH (id_tax13/id_tax12).
The domestic withholding rate has been 3% since the Aug 2025 change, and no 35%
withholding rate exists in Ethiopian law at all — the punitive no-TIN rate is
30%. Until now both sat in the same selection list as our correct rates, so an
accountant raising a vendor bill was offered six withholding options of which
two were wrong. Nothing crashed: the WHT summary reported the wrong figure
correctly.

This is the path that matters at a client site. `post_init_hook` runs on
INSTALL only, so a database that already has l10n_et_base installed would never
pick the fix up without this migration; it would keep offering 2% and 35%
through every upgrade.

Deactivates only — bills posted under the old 2% keep their tax record, their
move lines still resolve, and the WHT summary still reports them. Idempotent.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if version is None:
        # Fresh install: the post_init hook and _post_load_data both call the
        # same helper, so there is nothing left to do here.
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    chart_template = env["account.chart.template"]
    companies = env["res.company"].search([("chart_template", "=", "et")])
    total = 0
    for company in companies:
        deactivated = chart_template._l10n_et_base_deactivate_unsupported_core_taxes(company)
        total += len(deactivated)
    # Report what was done, not merely that nothing failed. Zero is a legitimate
    # result (already migrated, or no 'et' company), but it must be visible
    # rather than indistinguishable from the migration not running at all.
    _logger.info(
        "l10n_et_base: unsupported core WHT deactivation — %d compan(y/ies) on chart 'et', "
        "%d tax record(s) deactivated.",
        len(companies),
        total,
    )
