# -*- coding: utf-8 -*-
"""Rename the system partner on a database that already has this module.

THE CASE THIS EXISTS FOR
------------------------
`post_init_hook` runs at INSTALL. Every tenant already running SapianERP has
`sapian_theme_mail` installed, so the version that renames the bot arrives
there as an UPGRADE — and an upgrade runs no install hook and, as
models/res_partner.py explains at length, re-applies no data record for an
xmlid whose `ir_model_data.noupdate` is set. Without this script the fix would
land on new databases only, CI (which builds new databases) would be green, and
every existing client would keep reading "OdooBot" in their chatter.

WHY `end-` AND NOT `post-`, WHICH IS THE WHOLE POINT OF THIS VERSION
--------------------------------------------------------------------
1.2.0 shipped this as `post-bot_identity.py`. A `post-` script runs at the end
of ITS OWN MODULE's load, at whatever position the module occupies in the
graph — so anything loading afterwards could still write over it. That is the
defect: across identical runs this module moved between 26/30 and 27/30 and the
outcome moved with it.

`end-` scripts run in a different phase entirely. `odoo/modules/loading.py`,
STEP 3.5:

    # STEP 3.5: execute migration end-scripts
    if update_module:
        migrations = MigrationManager(cr, graph)
        for package in graph:
            migrations.migrate_module(package, 'end')

That loop runs after STEP 3 has loaded every module in the graph. There is no
module left to load, so there is nothing left to overwrite us. The ordering
stops being something we hope for and becomes something the loader guarantees.

The install half is ordered by a different mechanism — `mail_bot` is declared
in `depends`, which makes the sibling order total. See the manifest.

Idempotent — `_sapian_apply_bot_identity` writes only what differs and returns
whether anything moved — so re-running it is a no-op rather than a hazard.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    if not version:
        # Odoo passes version=None when the module is being INSTALLED rather
        # than upgraded; the hook has it covered in that case and running twice
        # would only be noise.
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    changed = env["res.partner"]._sapian_apply_bot_identity()
    _logger.info(
        "sapian_theme_mail migration %s (end stage, after every module loaded):"
        " system partner %s",
        version,
        "renamed" if changed else "already carried our identity",
    )
