# -*- coding: utf-8 -*-
"""Seed the social welfare levy configuration on databases that already exist.

New companies are seeded by ``res.company.create`` and fresh chart loads by
``_post_load_data``; neither reaches a database that was installed before this
version. Without this, an existing tenant's levy engine would resolve no
configuration and — following the same rule as the WHT engine — raise on the
first import bill rather than silently charging nothing. Filling it in here
means the upgrade completes the change instead of leaving it half-applied.

The seeded date is the REGULATION's commencement date (6 August 2022), not the
upgrade date: an import cleared in 2023 was subject to the levy whether or not
this module existed then, and a migrated historical bill must compute the same
figure the customs declaration did.

AND the levy TAX's base flags, which an upgrade cannot set on its own.

`_pre_reload_data` deliberately does not update fields on taxes that already
exist, and the post_init hook that applies such fixes runs on INSTALL only. So a
database upgrading from an earlier version would keep Odoo's default
`is_base_affected = True` on the levy — and compute 3% of (CIF + any tax
sequenced before it) instead of 3% of CIF. Measured on an upgraded database
before this block existed: the fresh install read False, the upgrade read True.

Idempotent.
"""

from odoo import SUPERUSER_ID, api

from odoo.addons.l10n_et_base.models.l10n_et_social_welfare_levy_config import (
    TEMPLATE_TAX_XMLID,
)


def migrate(cr, version):
    if version is None:
        # Fresh install: res.company.create seeds as companies are created.
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["l10n.et.social.welfare.levy.config"]._l10n_et_seed_all_companies()

    chart_template = env["account.chart.template"]
    for company in env["res.company"].search([("chart_template", "=", "et")]):
        tax = chart_template.with_company(company).ref(
            TEMPLATE_TAX_XMLID, raise_if_not_found=False
        )
        if not tax:
            continue
        values = {
            field: value
            for field, value in (("is_base_affected", False), ("include_base_amount", False))
            if tax[field] != value
        }
        if values:
            tax.write(values)
