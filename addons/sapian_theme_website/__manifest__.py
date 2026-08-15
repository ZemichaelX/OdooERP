# -*- coding: utf-8 -*-
{
    "name": "SapianERP Theme — Website bridge",
    "version": "19.0.1.0.0",
    "summary": "Keeps public sign-up closed on a SapianERP tenant once "
    "`website` is installed.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Theme/Backend",
    "license": "LGPL-3",
    # A BRIDGE, and it has to be one — this is not a stylistic choice.
    #
    # `res.users._get_signup_invitation_scope()` is what the login controller
    # asks (auth_signup/controllers/main.py:132). Two modules define it and
    # NEITHER calls super():
    #
    #     auth_signup/models/res_users.py:88   returns the config parameter
    #     website/models/res_users.py:66       returns the per-website column
    #                                          `or` the parameter
    #
    # So whichever sits highest in the MRO ends the chain. Measured on the
    # 36-app database, with the override placed in sapian_theme:
    #
    #     MRO: [website.res_users, auth_signup.res_users, sapian_theme.res_users]
    #     _get_signup_invitation_scope() -> 'b2c'
    #
    # sapian_theme is LAST because it depends on base + web only, so it loads
    # before both — and its override was dead code in every configuration. A
    # module can only win this by depending on `website`, and sapian_theme must
    # stay installable on a database carrying nothing else of ours. Hence a
    # bridge, exactly as l10n_et_calendar_account exists so l10n_et_calendar
    # never has to depend on `account`.
    #
    # auto_install means it appears by itself the moment both sides are
    # present — which matters here more than for the calendar bridges, because
    # the thing it prevents is a security default flipping under a client who
    # bought an unrelated module.
    "depends": ["sapian_theme", "website"],
    "auto_install": True,
    # No new model, no view, no record, and no install hook: ONE method
    # override. An earlier version also normalised the stored
    # `website.auth_signup_uninvited` rows at install, so that Settings >
    # Website would not read 'Free sign up' on a tenant where sign-up is
    # closed. It was removed because it cannot win: `website_sale`'s own
    # post-install hook rewrites those rows, and in two of the three real
    # install orders it runs after ours. Measured — the bridge's own test
    # caught it on `-i sapian_theme,website,website_sale`. Keeping a
    # best-effort write would have meant a guarantee that holds only when
    # the modules happen to install in the right order, which is the same
    # class of thing this module exists to remove. Nothing to grant access
    # to.
}
