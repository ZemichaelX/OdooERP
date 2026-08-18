# -*- coding: utf-8 -*-
from . import models


def _l10n_et_base_post_init(env):
    """Bring companies that adopted the 'et' chart before this module up to date.

    Fresh companies get the merged template automatically at chart load; existing
    ones (including the core l10n_et demo company, whose chart loads before this
    module in the same install transaction) need the explicit reload. The heavy
    lifting is in ``account.chart.template._l10n_et_base_reload_for_company`` so
    the demo loader can reuse it.
    """
    for company in env["res.company"].search([("chart_template", "=", "et")]):
        env["account.chart.template"]._l10n_et_base_reload_for_company(company)
    # Partners created before this module owned `l10n_et_tin` — including any the
    # chart or demo data made — need core `vat` filled, or their documents print
    # no tax identifier at all.
    env["res.partner"]._l10n_et_backfill_vat_from_tin()
    env["res.country"]._l10n_et_ensure_vat_label()
