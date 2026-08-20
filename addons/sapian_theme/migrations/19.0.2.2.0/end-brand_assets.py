# -*- coding: utf-8 -*-
"""Put our favicon (and, where none was chosen, our logo) on an EXISTING tenant.

THE OTHER HALF OF THE PAIR, and the half that is easy to forget.

`post_init_hook` runs on install and never on upgrade. A tenant that already
has `sapian_theme` — which is every tenant we have provisioned — would keep
Odoo's purple favicon in every browser tab forever, because nothing would ever
run the code that replaces it. That is the same install-versus-upgrade split
`sapian_theme_mail` documents for the bot's name, and it is why both paths are
proved separately in CI rather than one being assumed from the other.

`end-` so it runs at STEP 3.5, after every module in the graph has loaded:
`res.company._sapian_apply_brand_assets` is defined by this module and the
`file_open` it does resolves against the addons path, both of which want a
fully loaded registry.

The manifest version must be bumped with this file or it never executes — Odoo
runs `migrations/<version>/` only when the installed version is BELOW the
manifest's. A migration shipped without its bump is inert, reviews as done, and
leaves every check green because nothing ran.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID  # noqa: PLC0415 - migration-time import

    env = api.Environment(cr, SUPERUSER_ID, {})
    written = env["res.company"]._sapian_apply_brand_assets()
    _logger.info(
        "sapian_theme: upgrade wrote brand assets on %d compan%s",
        written,
        "y" if written == 1 else "ies",
    )
