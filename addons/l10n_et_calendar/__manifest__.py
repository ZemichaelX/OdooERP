# -*- coding: utf-8 -*-
{
    "name": "Ethiopian Calendar",
    "version": "19.0.1.0.0",
    "summary": "The Ethiopian (Ge'ez) calendar: a conversion library with a "
    "golden-tested reference implementation, a reusable mixin that mirrors any "
    "Gregorian date field onto a stored, searchable Ethiopian one, and two "
    "company settings for how Ethiopian dates display and which calendar "
    "prints on documents.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    # base + base_setup only. This module must install on a database carrying no
    # other sapian or l10n_et module — it is the calendar, not a tax feature,
    # and a dependency on l10n_et_base would drag a chart of accounts onto a
    # client who only wanted Ethiopian dates on a purchase order.
    #
    # base_setup is here because the two company settings live on the Settings
    # page, whose view (base_setup.res_config_settings_view_form) this module
    # inherits: referencing another module's XML id without depending on it
    # works only for as long as somebody else happens to install it. base_setup
    # itself depends on base and web only, so it drags nothing.
    "depends": ["base", "base_setup"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    # No new models with records, so no ir.model.access.csv: the mixin is
    # abstract and the two settings are fields on res.company, which carries
    # its own access rules. CLAUDE.md rule 8 is satisfied by there being
    # nothing new to grant access to.
}
