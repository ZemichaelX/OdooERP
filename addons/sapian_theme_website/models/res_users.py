# -*- coding: utf-8 -*-
"""Public sign-up stays off once `website` is on the tenant.

THE DEFECT
----------
Installing `website_sale` — a module in our own product catalogue, i.e.
something we sell — opens public sign-up on the client's ERP. Not as a setting
somebody left on, but as a post-install hook:

    website_sale/__init__.py:15
        env['website'].search([]).auth_signup_uninvited = 'b2c'
    website_sale/models/website.py:88
        auth_signup_uninvited = fields.Selection(default='b2c')

The first rewrites every existing website; the second makes 'b2c' the default
for any created afterwards. A tenant provisioned invitation-only becomes open
to the internet the moment a module is bought, with no screen shown to anyone.

Measured on the 36-app database before this module existed:

    ir.config_parameter auth_signup.invitation_scope   b2b
    website 'My Website'.auth_signup_uninvited         b2c
    GET /web/login                                     "Don't have an account?"

WHY THE PARAMETER WE SET STOPPED BEING THE AUTHORITY
-----------------------------------------------------
`provision_client.sh` and the demo builder both set the parameter, and it is
genuinely the authority — until `website` is installed:

    auth_signup/controllers/main.py:132
        'signup_enabled': ..._get_signup_invitation_scope() == 'b2c'
    auth_signup/models/res_users.py:88     reads the parameter, no super()
    website/models/res_users.py:66         reads the per-website column, and
                                           only falls back to super() when that
                                           column is empty — which it never is

That is the third time a guard here has been correct when written and wrong
afterwards because the system moved underneath it: `login_primary` was green
while the page said "Powered by Odoo"; `is_redirect_home` was True while
`action_id` decided the landing. The lesson each time is the same — put the fix
at the point that decides, and assert the value the served page honours.

WHY AN OVERRIDE AND NOT A WRITE
--------------------------------
This module normalised the stored rows at install first, so that Settings >
Website would not read "Free sign up" on a tenant where sign-up is closed. That
write was removed, because it cannot win: `website_sale`'s own post-install
hook rewrites those rows and in two of the three real install orders it runs
after ours — measured, and caught by this module's own test on
`-i sapian_theme,website,website_sale`. Anything written once is overwritten
later, silently. The override is read on every request, so it holds regardless
of what is installed, in what order, or when.

The consequence is stated rather than hidden: Settings > Website can read "Free
sign up" while sign-up is invitation-only. That is a display inconsistency, not
a hole, and `check_login_page.py` prints the stored rows next to the effective
value so the difference is visible to whoever looks.

THE ESCAPE HATCH, because a webshop is a legitimate thing to sell
-----------------------------------------------------------------
    ir.config_parameter  sapian_theme.allow_public_signup = 1

Set it and this module stops interfering, so `website_sale`'s customer accounts
work exactly as Odoo intends. Off by default, because a private company ERP
that anybody on the internet can open an account on is not a misconfiguration,
it is a breach.
"""

import logging

from odoo import api, models

# ONE switch, defined on sapian_theme, read by both bridges. Sign-up is decided
# in two different places depending on what is installed, and two switches for
# one property is how a tenant ends up half open.
from odoo.addons.sapian_theme.models.res_users import ALLOW_PUBLIC_SIGNUP_PARAM

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _get_signup_invitation_scope(self):
        """Invitation-only unless public sign-up was explicitly allowed.

        This module depends on `website`, so its class is more derived than
        `website`'s and this runs first — which is the whole reason the module
        exists. `super()` is still called rather than returning 'b2b' outright,
        so that an operator who opts in gets Odoo's real resolution (per-website
        column, then parameter) instead of ours.
        """
        scope = super()._get_signup_invitation_scope()
        if scope == "b2c" and not self._sapian_public_signup_allowed():
            _logger.debug(
                "sapian_theme_website: sign-up scope resolved to 'b2c' but %s is "
                "not set; serving 'b2b' (invitation only).",
                ALLOW_PUBLIC_SIGNUP_PARAM,
            )
            return "b2b"
        return scope
