# -*- coding: utf-8 -*-
"""Put our logo, where none was chosen, on an EXISTING tenant.

THE OTHER HALF OF THE PAIR, and the half that is easy to forget.

`post_init_hook` runs on install and never on upgrade. A tenant that already
has `sapian_theme` — which is every tenant we have provisioned — would keep
Odoo's stock logo on its invoices forever, because nothing would ever run the
code that replaces it. That is the same install-versus-upgrade split
`sapian_theme_mail` documents for the bot's name, and it is why both paths are
proved separately in CI rather than one being assumed from the other.

The favicon needs no migration at all, and that is not an omission: it is a
view (`views/favicon.xml`), and a module upgrade reloads views. Only records
have this problem.

`end-` so it runs at STEP 3.5, after every module in the graph has loaded:
`res.company._sapian_apply_default_logo` is defined by this module and the
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
    written = env["res.company"]._sapian_apply_default_logo()
    _logger.info(
        "sapian_theme: upgrade wrote the default logo on %d compan%s",
        written,
        "y" if written == 1 else "ies",
    )
