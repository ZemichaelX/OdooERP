# -*- coding: utf-8 -*-
{
    "name": "SapianERP Theme",
    "version": "19.0.1.3.0",
    "summary": "SapianERP house identity: one brand colour driving the backend, "
    "the login page and printed documents, plus the app rail that makes the "
    "app icons visible on desktop. Horizontal — no client and no sector "
    "styling. Re-brand by editing one value in "
    "static/src/scss/sapian_variables.scss.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    # base + web only. This module must install on a database that carries no
    # other sapian module, and must not drag product modules in behind it.
    "depends": ["base", "web"],
    "data": [
        # The mark first: login_templates.xml t-calls it.
        "views/sapian_mark.xml",
        "views/login_templates.xml",
        # The other emitter of "Powered by Odoo" — reached by the portal,
        # and by the login page itself when `website` is installed.
        "views/brand_promotion.xml",
        # Last: a drift check that only warns. See the file for why it never
        # fixes anything on its own.
        "data/brand_drift_check.xml",
    ],
    "assets": {
        # PREPEND, not append: primary_variables.scss declares $o-brand-primary
        # with !default, so ours only wins if it is compiled first.
        # This one bundle is reached by the backend, the login page and the
        # report/PDF bundle alike — see the header of sapian_variables.scss.
        "web._assets_primary_variables": [
            ("prepend", "sapian_theme/static/src/scss/sapian_variables.scss"),
        ],
        "web.assets_backend": [
            "sapian_theme/static/src/scss/sapian_backend.scss",
            # The app rail. A component in the `main_components` registry —
            # nothing patched, nothing inherited. See app_rail.js for the
            # precedent counts behind that choice.
            "sapian_theme/static/src/scss/sapian_rail.scss",
            "sapian_theme/static/src/js/app_rail.js",
            "sapian_theme/static/src/xml/app_rail.xml",
            # The backend footer: same shape as the rail — a component in
            # `main_components`, position: fixed, one padding rule.
            "sapian_theme/static/src/scss/sapian_footer.scss",
            "sapian_theme/static/src/js/backend_footer.js",
            "sapian_theme/static/src/xml/backend_footer.xml",
        ],
        # The login page needs its own rule: the frontend bundle never consults
        # $o-brand-primary. See the header of sapian_frontend.scss.
        "web.assets_frontend": [
            "sapian_theme/static/src/scss/sapian_frontend.scss",
        ],
    },
    "post_init_hook": "post_init_hook",
}
