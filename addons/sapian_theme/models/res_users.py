# -*- coding: utf-8 -*-
"""SapianERP's opinion about the two web_responsive settings that decide what a
user sees the moment they arrive.

WHAT THIS CHANGES
-----------------
`web_responsive` adds two per-user fields, and ships both at values that are
wrong for this product:

  is_redirect_home   False   -> login lands on whatever the default app is,
                               which on our databases is the Module Catalog:
                               a configuration screen. The fullscreen launcher
                               is the entire reason the module was vendored.
  apps_menu_theme    'milk'  -> paints the launcher a pale lilac. The
                               'community' theme derives the same background
                               from $o-brand-primary, which
                               sapian_variables.scss already sets to the
                               SapianERP brand. 'milk' is Odoo's colour on our
                               screen — the same defect class as the login page
                               rendering Odoo purple, one layer up.

Both stay PER-USER fields. Anyone who wants the old behaviour can set it on
their own record and keep it; what changes is only what a user gets when
nobody has expressed a preference. A default is the product's opinion, and the
product's opinion is the launcher.

WHY HERE AND NOT IN THE VENDORED MODULE
---------------------------------------
vendor/oca_web/web_responsive is upstream code pinned by tree hash
(vendor/README.md, scripts/check_vendor.sh). Editing it would make our build a
version of web_responsive that exists nowhere else, and the next refresh would
revert the change silently. A default is our opinion, so it lives in our
module.

WHY NOT A DEPENDS ON web_responsive
-----------------------------------
sapian_theme depends on base + web only, and must install on a database
carrying no other product module (see __manifest__.py). Adding a dependency
here would drag the launcher into every database that wants our branding.
Instead the fields are looked up at call time: when web_responsive is absent
the loop does nothing, and when it is installed afterwards the defaults start
applying with no update of this module. That check is `name in self._fields`,
the same runtime-presence test the rail's own tests use for `tour_enabled`.

WHAT THIS DOES NOT DO
---------------------
It does not touch users that already exist. `default_get` supplies a value
only where none was given, so an existing database keeps every user exactly as
it found them — including the admin of an already-built demo tenant, who will
still land on the Module Catalog until someone sets the field. Rewriting
stored per-user preferences is a migration, and a migration that silently
overrides a choice a user made is not a default.
"""

from odoo import api, models

# The fields are web_responsive's; the values are ours.
SAPIAN_LAUNCHER_DEFAULTS = {
    "is_redirect_home": True,
    "apps_menu_theme": "community",
}


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def default_get(self, fields_list):
        """Apply the SapianERP launcher defaults where the caller expressed none.

        `_add_missing_default_values` calls this for every field absent from
        the values dict, so this reaches records created through the ORM as
        well as through the user form — the two are the same code path.
        """
        defaults = super().default_get(fields_list)
        for name, value in SAPIAN_LAUNCHER_DEFAULTS.items():
            # Absent unless web_responsive is installed. Checked per call, not
            # at load time, so installing it later needs no update of this
            # module.
            if name not in self._fields or name not in fields_list:
                continue
            # An explicit `default_<field>` in the context is a caller saying
            # what it wants, and beats the product default. Without this
            # guard, `with_context(default_apps_menu_theme='milk')` would be
            # silently ignored, which is worse than having no default at all.
            if f"default_{name}" in self.env.context:
                continue
            defaults[name] = value
        return defaults
