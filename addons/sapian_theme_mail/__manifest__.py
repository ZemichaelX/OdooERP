# -*- coding: utf-8 -*-
{
    "name": "SapianERP Theme — Mail bridge",
    "version": "19.0.1.0.0",
    "summary": "Brands OUTGOING EMAIL: the call-to-action button takes the "
    "house colour, and the footer stops attributing the client's invoices to "
    "Odoo.",
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
    "depends": ["sapian_theme", "mail"],
    # auto_install: `mail` is a dependency of almost everything, so in practice
    # this appears on every real tenant the moment sapian_theme is installed —
    # which is the point. Outgoing email is the most externally visible surface
    # in the product; branding it must not be something a deployment can
    # forget to tick.
    "auto_install": True,
    "data": [
        "views/mail_attribution.xml",
    ],
    # Seeds the email button colour on companies that never chose one. Existing
    # tenants keep mailing Odoo purple otherwise — the fields carry a column
    # default, so there is no empty state for a create-time default to fill.
    "post_init_hook": "post_init_hook",
}
