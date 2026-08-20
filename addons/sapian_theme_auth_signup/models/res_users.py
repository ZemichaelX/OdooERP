# -*- coding: utf-8 -*-
"""Public sign-up is off unless somebody turned it on. On EVERY tenant.

WHAT WAS ALREADY TRUE, AND WHY IT WAS NOT ENOUGH
-------------------------------------------------
Measured before this module had a model, on tenants built exactly the way
`provision_client.sh` builds them (CI job "A stranger cannot get an account"):

    client tenant, default modules (no website)   signup_get=404  created=0
    client tenant + website + website_sale        signup_get=404  created=0

Both closed. But they were closed for two different reasons and only one of them
was the product's:

  * with `website`, `sapian_theme_website` overrides
    `res.users._get_signup_invitation_scope()` — read on every request, so it
    holds whatever is installed and whenever;
  * without it, the tenant was closed because **phase 4 of a shell script had
    run once** and written `auth_signup.invitation_scope = b2b`.

Odoo's own default for that setting is **b2c — free sign-up**
(`auth_signup/models/res_config_settings.py`). So a database that did not go
through that script — a restored backup, a second database created from the
database manager, a tenant somebody built by hand, or any tenant provisioned
before phase 4 existed — is open to the internet. "Closed because a script ran"
is not a default; it is a step somebody can skip, and nothing tells them.

This module makes it a property of the product. The check is here rather than in
`sapian_theme` because `sapian_theme` must stay installable on a database
carrying nothing else of ours, and only a module that DEPENDS on `auth_signup`
can be more derived than it in the MRO. That is the same reasoning that put the
website half in `sapian_theme_website` — see that file.

THE ESCAPE HATCH IS THE SAME ONE
---------------------------------
    ir.config_parameter  sapian_theme.allow_public_signup = 1

One switch for both halves, defined on `sapian_theme`. Set it and both bridges
stand down and Odoo resolves sign-up exactly as it normally would. Off by
default, because a private company ERP that anybody on the internet can open an
account on is not a misconfiguration, it is a breach.

EXISTING TENANTS
-----------------
The override only exists on a tenant where this module's code is loaded, so a
tenant running an older checkout is unaffected until it is upgraded. `-u
sapian_theme_auth_signup` is enough; the module is `auto_install` and is already
present on every real tenant, because `auth_signup` is itself auto-installed on
(base_setup, mail, web).
"""

import logging

from odoo import api, models

from odoo.addons.sapian_theme.models.res_users import ALLOW_PUBLIC_SIGNUP_PARAM

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _get_signup_invitation_scope(self):
        """Invitation only, unless public sign-up was explicitly allowed.

        `super()` is still called rather than returning 'b2b' outright, so an
        operator who opts in gets Odoo's real resolution — the per-website
        column if `website` is installed, the parameter otherwise — instead of
        ours. We narrow the answer; we never widen it.
        """
        scope = super()._get_signup_invitation_scope()
        if scope == "b2c" and not self._sapian_public_signup_allowed():
            _logger.debug(
                "sapian_theme_auth_signup: sign-up scope resolved to 'b2c' but %s "
                "is not set; serving 'b2b' (invitation only).",
                ALLOW_PUBLIC_SIGNUP_PARAM,
            )
            return "b2b"
        return scope
