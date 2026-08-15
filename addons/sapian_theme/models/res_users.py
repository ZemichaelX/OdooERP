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

THE THIRD FIELD, WHICH IS NOT web_responsive's AND OUTRANKS BOTH
----------------------------------------------------------------
`res.users.action_id` — "Home Action" on the Preferences tab — decides the
landing page BEFORE either of the two above is consulted, and by a code path
that never reaches web_responsive at all:

    session_info['home_action_id']            (base/models/ir_http.py)
      -> user.homeActionId                    (web/static/src/core/user.js)
      -> action_service._getActionParams()    falls back to it when the URL
                                              carries no action
      -> loadState() returns TRUE
      -> WebClient.loadRouterState() therefore SKIPS _loadDefaultApp()

`_loadDefaultApp` is the only method web_responsive patches, and that patch is
the only code in the stack that reads `is_redirect_home`. So a user with a home
action never reaches the branch that would honour the launcher.

What that looks like on screen is the part worth writing down, because it reads
as a race and is not one. `AppsMenu.setup()` opens the launcher on its own, off
`user.context.is_redirect_to_home`, independently of `_loadDefaultApp` — so the
launcher paints, correctly, with every tile. Then the home action's controller
mounts, fires `ACTION_MANAGER:UI-UPDATED`, and `AppsMenu` closes itself on that
event. Measured on demo_selam at 1366x900, admin with `is_redirect_home = True`
and `action_id` = the Module Catalog:

    1205 ms   /odoo             launcher visible, 12 tiles
    1442 ms   /odoo             list view mounted underneath
    1562 ms   /odoo/action-101  launcher gone

Roughly one second of a correct launcher, then a configuration screen, with
nobody touching the mouse. With `action_id` empty the same measurement holds at
the launcher indefinitely — 8 boots at 6x CPU throttling and 300 ms latency,
12 tiles every time, no navigation.

The two settings are therefore not independent, and the pair
`is_redirect_home = True` with a home action set is not a preference — it is a
field that says one thing while the page does another. web_responsive says so
itself, from both ends: `_compute_redirect_home` forces `is_redirect_home` to
False whenever `action_id` is set, and its user view renders the checkbox with
`invisible="action_id"`. Upstream's model is that you get one or the other.
`_sapian_apply_launcher_defaults` below is what keeps that true on our side,
because writing `is_redirect_home = True` on top of a home action is precisely
how the lie gets manufactured.

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

# `action_id` is base's, not web_responsive's, so it is always present and is
# handled separately from the dict above (which is skipped wholesale when the
# launcher is not installed). Empty is not a SapianERP opinion about home
# actions — it is the only value at which the two fields above can reach the
# page at all. See the module docstring.
SAPIAN_NO_HOME_ACTION = {"action_id": False}


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

        IT CLEARS THE HOME ACTION, AND HAS TO
        -------------------------------------
        `action_id` outranks both of the fields this command writes, by a code
        path that never reaches web_responsive (module docstring, with the
        measurement). Writing `is_redirect_home = True` and leaving a home
        action behind produces a user whose stored settings say "launcher" and
        whose screen shows a list view one second after login — the exact defect
        this command exists to prevent, manufactured by the command itself.

        So a home action is BOTH a reason to move a user and something the move
        clears. The command's contract is "these users land on the launcher",
        not "these two fields hold these two values"; a field value that the
        page does not deliver is the failure this repo keeps finding.

        Archived users matter here more than anywhere else: `copy()` copies
        `action_id`, and `base.template_user` is the inactive record the invite
        flow copies. A home action left on the template is inherited by every
        user created afterwards, which is a defect that spreads rather than one
        that sits still.

        WHAT IT CANNOT TELL APART, SAID PLAINLY
        --------------------------------------
        `is_redirect_home = False` is BOTH web_responsive's shipped default and
        the value a user who dislikes the launcher would set for themselves.
        They are the same stored value, so this command cannot distinguish them
        and does not pretend to: it moves every internal user still on the
        upstream values, and on a tenant where somebody has deliberately opted
        out it will opt them back in.

        A home action is the opposite case: it is unambiguous evidence of a
        choice, the way a company colour is in `res.company._sapian_apply_brand`
        — nothing sets it but a person. It is cleared anyway, because it cannot
        coexist with the launcher, and the dry run therefore names the action it
        would remove for each user rather than only the login. That list is the
        thing to read before running this on a tenant that has been in use.

        That is why it is a provisioning command and not a migration hook. Run
        it when a tenant is built, before anyone has a preference to lose. On a
        tenant that has been in use, run the dry run first and decide with its
        report in front of you.

        Internal users only (`share = False`): portal and public users never
        see a backend launcher.

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

        internal = self.sudo().with_context(active_test=False)

        # web_responsive's own shipped defaults. A user on any other value has
        # expressed a preference and is left alone — except for a home action,
        # which is a preference the launcher cannot coexist with (docstring).
        stale = internal.search([("share", "=", False), ("is_redirect_home", "=", False)])
        stale |= internal.search([("share", "=", False), ("apps_menu_theme", "=", "milk")])
        homed = internal.search([("share", "=", False), ("action_id", "!=", False)])
        stale |= homed
        names = ", ".join(sorted(stale.mapped("login")))
        # Named, not counted: this is the one thing here that removes something
        # a person chose, so the report has to say which user loses which action.
        homes = (
            "; ".join(sorted("%s -> %s" % (u.login, u.action_id.name) for u in homed)) or "none"
        )

        if not stale:
            _logger.info(
                "sapian_theme: every internal user is already on the SapianERP "
                "launcher defaults and none carries a home action; nothing to "
                "apply. (Users who chose something else are not counted and are "
                "never touched.)"
            )
            return stale
        if dry_run:
            _logger.info(
                "sapian_theme: DRY RUN — %d user%s would move to the app "
                "launcher (%s): %s. Home actions that would be CLEARED: %s. "
                "Nothing was written. Re-run with dry_run=False to apply.",
                len(stale),
                "" if len(stale) == 1 else "s",
                ", ".join("%s=%r" % item for item in SAPIAN_LAUNCHER_DEFAULTS.items()),
                names,
                homes,
            )
            return stale

        # One write, both halves. `is_redirect_home` is a stored editable
        # compute that depends on `action_id`, so the order the two are applied
        # in decides the outcome — asserted by TestLauncherProvisioningCommand
        # rather than reasoned about here.
        stale.write(dict(SAPIAN_LAUNCHER_DEFAULTS, **SAPIAN_NO_HOME_ACTION))
        _logger.info(
            "sapian_theme: APPLIED the app launcher defaults to %d user%s: %s. "
            "Home actions cleared: %s. They now land on the launcher in the "
            "house brand instead of on a configuration screen.",
            len(stale),
            "" if len(stale) == 1 else "s",
            names,
            homes,
        )
        return stale
