# -*- coding: utf-8 -*-
"""Seed WHT + cash-cap configuration for companies that never got any.

Before this version the configs were seeded ONLY when chart 'et' loaded, so any
company created another way (a group's second company, a tenant provisioned
without the chart) had no configuration at all — and both engines read that as
"stay inert", posting vendor bills with no withholding and cash payments with
no cap check, silently. The engines now raise for an in-scope company with no
configuration, so existing databases must be filled in BEFORE anyone posts.

New companies are seeded by ``res.company.create``; the data-file ``<function>``
covers upgrades too. This migration makes the fill-in explicit and ordered for
databases that already exist. Idempotent.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if version is None:
        # Fresh install: res.company.create seeds as companies are created.
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["l10n.et.wht.config"]._l10n_et_seed_all_companies()
    env["l10n.et.cash.cap.config"]._l10n_et_seed_all_companies()
