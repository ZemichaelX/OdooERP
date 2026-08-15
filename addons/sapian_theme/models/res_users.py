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

WHAT THE DEFAULT CANNOT REACH, AND WHY PROVISIONING HAS TO
----------------------------------------------------------
`default_get` supplies a value only where none was given, so it never touches a
user that already exists. That is correct, and it is also not enough — measured,
not reasoned:

    [1] odoo -d demo -i base            -> admin created here.
                                           'is_redirect_home' in u._fields = False
                                           (web_responsive is not installed yet)
    [3] odoo -d demo -i ...,web_responsive
                                        -> admin  is_redirect_home=False  theme=milk
                                           a user created NOW: True / community

The admin of a demo or a client tenant is created in phase 1, before the module
that owns the field exists. The column default therefore wins for the one user
who is in every screen recording and every handover — and the product default
never applies to them. A build that installs web_responsive and stops has a
launcher nobody lands on.

So provisioning applies the defaults explicitly, via
``_sapian_apply_launcher_defaults`` below. That is a provisioning step, not a
migration: it is invoked by name, it defaults to a dry run, it only moves users
that are still on web_responsive's own defaults, and it says what it changed.
Nothing calls it on install.
"""

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

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

    # ---- the explicit provisioning command ---------------------------------

    @api.model
    def _sapian_apply_launcher_defaults(self, dry_run=True):
        """Move users still on web_responsive's own defaults onto ours.

        WHY THIS EXISTS AT ALL
        ----------------------
        See the module docstring: the admin of a demo or client tenant is
        created in the `-i base` phase, before web_responsive owns the field,
        so `default_get` never sees it and the column default wins. Without
        this, `scripts/build_demo.sh` and `scripts/provision_client.sh` would
        install the launcher and hand over a tenant whose only user still lands
        on the Module Catalog in Odoo's lilac.

        WHY IT IS NOT A MIGRATION
        -------------------------
        It never runs by itself — an operator or a provisioning script has to
        ask for it, and `dry_run=True` means the accident is a report rather
        than a rewrite. Same shape as `res.company._sapian_apply_brand`, and
        for the same reason.

        WHAT IT CANNOT TELL APART, SAID PLAINLY
        --------------------------------------
        `is_redirect_home = False` is BOTH web_responsive's shipped default and
        the value a user who dislikes the launcher would set for themselves.
        They are the same stored value, so this command cannot distinguish them
        and does not pretend to: it moves every internal user still on the
        upstream values, and on a tenant where somebody has deliberately opted
        out it will opt them back in.

        That is why it is a provisioning command and not a migration hook. Run
        it when a tenant is built, before anyone has a preference to lose. On a
        tenant that has been in use, run the dry run first — it prints the
        logins it would move — and decide with that list in front of you.
        `res.company._sapian_apply_brand` can be more careful because a company
        colour that differs from ours is unambiguous evidence of a choice; a
        boolean at its default is not.

        Internal users only (`share = False`): portal and public users never
        see a backend launcher. Archived users are included deliberately —
        `base.template_user` is inactive and is the template new users are
        copied from, so leaving it behind would quietly reintroduce the old
        default on every user created through the invite flow.

        Returns the affected users either way, and logs what it actually did,
        so a run that changed nothing is distinguishable from a run that
        worked.
        """
        missing = [name for name in SAPIAN_LAUNCHER_DEFAULTS if name not in self._fields]
        if missing:
            _logger.info(
                "sapian_theme: web_responsive is not installed (no %s on "
                "res.users); there is no launcher to default. Nothing to do.",
                ", ".join(missing),
            )
            return self.browse()

        # web_responsive's own shipped defaults. A user on any other value has
        # expressed a preference and is left alone.
        upstream = [("share", "=", False), ("is_redirect_home", "=", False)]
        stale = self.sudo().with_context(active_test=False).search(upstream)
        stale |= (
            self.sudo()
            .with_context(active_test=False)
            .search([("share", "=", False), ("apps_menu_theme", "=", "milk")])
        )
        names = ", ".join(sorted(stale.mapped("login")))

        if not stale:
            _logger.info(
                "sapian_theme: every internal user is already on the SapianERP "
                "launcher defaults; nothing to apply. (Users who chose "
                "something else are not counted and are never touched.)"
            )
            return stale
        if dry_run:
            _logger.info(
                "sapian_theme: DRY RUN — %d user%s would move to the app "
                "launcher (%s): %s. Nothing was written. Re-run with "
                "dry_run=False to apply.",
                len(stale),
                "" if len(stale) == 1 else "s",
                ", ".join("%s=%r" % item for item in SAPIAN_LAUNCHER_DEFAULTS.items()),
                names,
            )
            return stale

        stale.write(dict(SAPIAN_LAUNCHER_DEFAULTS))
        _logger.info(
            "sapian_theme: APPLIED the app launcher defaults to %d user%s: %s. "
            "They now land on the launcher in the house brand instead of on a "
            "configuration screen.",
            len(stale),
            "" if len(stale) == 1 else "s",
            names,
        )
        return stale
