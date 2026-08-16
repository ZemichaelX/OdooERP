# -*- coding: utf-8 -*-
{
    "name": "SapianERP Theme — Password reset mail bridge",
    "version": "19.0.1.0.0",
    "summary": "The password-reset email stops attributing the client's ERP to "
    "Odoo, and stops signing itself 'Public user'.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Theme/Backend",
    "license": "LGPL-3",
    # A THIRD BRIDGE, and the reason is the same shape as the other two.
    #
    # `auth_signup.reset_password_email` is an ir.ui.view belonging to
    # `auth_signup`. Inheriting a view that does not exist aborts the install,
    # so whichever module carries this override must depend on `auth_signup`.
    #
    # It cannot be `sapian_theme_mail`. That module is `auto_install` on
    # (sapian_theme, mail); adding `auth_signup` to its depends would mean the
    # EMAIL COLOUR fix — which has nothing to do with signup — stops auto-
    # installing on any database without it. A bridge costs a manifest; the
    # alternative costs the colour fix its reach.
    #
    # It cannot be `sapian_theme` either, for the reason that module's own
    # manifest states: it must install on a database carrying no other sapian
    # module, and a CI job asserts exactly that.
    #
    # `sapian_theme_mail` is a dependency rather than a sibling because the
    # switch this template honours — `res.company.sapian_email_attribution` —
    # is defined there. Referencing it without the dependency would be a
    # NameError at render time, on the password-reset path, for a user who is
    # locked out. That is the worst possible place to discover a missing field.
    "depends": ["sapian_theme_mail", "auth_signup"],
    # auto_install: `auth_signup` is itself auto_install (on base_setup, mail,
    # web), so on every real tenant it is present and this bridge appears with
    # it. The password-reset mail is the one email a locked-out user is
    # guaranteed to read closely; branding it must not be a box a deployment
    # can forget to tick.
    "auto_install": True,
    "data": [
        "views/reset_password_email.xml",
    ],
    # No model, no field, no access rule: two xpaths into one template. The
    # attribution switch and the button colour both already exist on
    # res.company — see sapian_theme_mail.
}
