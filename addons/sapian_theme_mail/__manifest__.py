# -*- coding: utf-8 -*-
{
    "name": "SapianERP Theme — Mail bridge",
    # 1.4.0 carries the send-time debrand. NO migration directory, and that is
    # not an omission: this version changes CODE, not records. A `-u` reloads
    # the Python and `mail.mail._prepare_outgoing_body` is ours from the next
    # mail onwards, on every tenant, with nothing to backfill. The rule the
    # bot's rename needed — a post_init_hook cannot reach an existing database
    # — applies to data, and there is none here.
    #
    # 1.3.0 carries the system partner's rename (SapianBot). The number is
    # LOAD-BEARING, not decoration: migrations/19.0.1.3.0/end-bot_identity.py
    # runs only when the installed version is below this one, and that script
    # is the only thing that reaches a tenant which already has this module.
    # Lowering it, or landing the rename without raising it, silently limits
    # the fix to databases created afterwards.
    #
    # 1.2.0 shipped the same rename from a `post-` script. That script ran at
    # the module's own position in the graph, which is exactly the ordering
    # this version stops relying on — see the migration for why `end-` is not
    # a cosmetic rename of the file.
    "version": "19.0.1.4.0",
    "summary": "Brands OUTGOING EMAIL: the call-to-action button takes the "
    "house colour, and the footer stops attributing the client's invoices to "
    "Odoo. Renames the system partner from OdooBot to SapianBot.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Theme/Backend",
    "license": "LGPL-3",
    # A BRIDGE, and it has to be one.
    #
    # `sapian_theme` depends on base + web ONLY, and its manifest says why:
    # "This module must install on a database that carries no other sapian
    # module, and must not drag product modules in behind it." A CI job asserts
    # it installs and passes entirely alone.
    #
    # Everything in here needs `mail`:
    #   * `email_primary_color` / `email_secondary_color` are fields `mail`
    #     adds to res.company (mail/models/res_company.py:28-33). Referencing
    #     them from sapian_theme would be a NameError on a database without
    #     mail.
    #   * `mail.mail_notification_layout` and `mail.mail_notification_light`
    #     are `mail`'s templates. Inheriting a view that does not exist aborts
    #     the install.
    #
    # So the choice was between widening sapian_theme's dependency — breaking
    # the one property its own manifest promises — and a bridge. Same shape as
    # `sapian_theme_website` and the `l10n_et_calendar_*` bridges.
    # `mail_bot` IS THE ORDER FIX, and it costs nothing.
    #
    # The rename was order-dependent: this module and `mail_bot` are both
    # `auto_install` with `mail` as their dependency, which makes them SIBLINGS
    # in the graph. Odoo orders siblings arbitrarily, so across identical runs
    # this module moved between position 26 and 27 of 30 — and the bot's name
    # moved with it. A fix that depends on which sibling the graph happens to
    # visit second is a coin toss, not a fix.
    #
    # Naming `mail_bot` as a dependency makes the order TOTAL: mail, then
    # mail_bot, then us. Odoo guarantees a dependency loads first, so nothing
    # that touches the bot can load after our hook.
    #
    # It installs no module that was not already there: `mail_bot` is itself
    # `auto_install` on `mail`, and we depend on `mail`, so every database that
    # can carry this module already carries mail_bot. The declaration buys
    # ordering, not scope.
    "depends": ["sapian_theme", "mail", "mail_bot"],
    # auto_install: `mail` is a dependency of almost everything, so in practice
    # this appears on every real tenant the moment sapian_theme is installed —
    # which is the point. Outgoing email is the most externally visible surface
    # in the product; branding it must not be something a deployment can
    # forget to tick.
    "auto_install": True,
    "data": [
        "views/mail_attribution.xml",
        # The attribution switch, in mail's own "Email Templates" settings
        # block. A permission the client cannot find is not a permission.
        "views/res_config_settings.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # Three narrow patches for Odoo's name and face in Discuss. The
            # bot's own name, email and avatar are NOT here — they are a
            # record, written from Python, for the reason set out in
            # models/res_partner.py.
            "sapian_theme_mail/static/src/js/sapian_bot.js",
        ],
    },
    # Seeds the email button colour on companies that never chose one, and
    # gives the system partner our name and mark. Existing tenants keep mailing
    # Odoo purple otherwise — the fields carry a column default, so there is no
    # empty state for a create-time default to fill.
    #
    # The hook is the INSTALL half. The upgrade half is
    # migrations/19.0.1.3.0/end-bot_identity.py, and both halves are needed:
    # a hook never runs on an upgrade, so on its own it would reach new
    # databases only — which is every database CI builds and no database a
    # client runs.
    "post_init_hook": "post_init_hook",
}
