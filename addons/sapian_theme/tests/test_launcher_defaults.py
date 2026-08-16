# -*- coding: utf-8 -*-
"""The two launcher defaults, proved from the wire rather than from the field.

WHY NOT JUST ASSERT THE FIELD VALUE
-----------------------------------
`self.assertTrue(user.is_redirect_home)` proves a column holds True. It does
not prove the user lands on the launcher, and `apps_menu_theme == 'community'`
does not prove a single teal pixel reaches the screen. This repository has been
caught by exactly that gap once already: the SCSS said teal, the compiled
bundle contained the brand seven times, and the button rendered Odoo purple —
every source-level assertion available at the time passed (README.md, "prefer
assets to template inheritance").

So these tests create real users, log in as them in headless Chrome, and look
at the page: what the client actually loaded, and what colour the launcher
actually computed.

AND THEY PROVE THEY CAN FAIL
----------------------------
Each browser test carries a CONTROL user created with the opposite value
through `default_<field>` in the context. If the product default were not
reaching the page, both users would behave identically and the control would
stop discriminating — which the tests assert. A guard that cannot go red is
one more thing that passes by doing nothing (CLAUDE.md).

WHY THESE ARE TAGGED OFF THE STANDARD SUITE
-------------------------------------------
They require `web_responsive`, which sapian_theme deliberately does not depend
on. `/module` and `/module:Class` selectors implicitly require the `standard`
tag (odoo/tests/tag_selector.py), so tagging the browser classes `-standard`
keeps them out of every run that has no launcher to look at, and the
`sapian_launcher` tag selects them in the CI job that installs both. They are
therefore never *skipped* — they are either selected and run, or not selected
at all, and the job that selects them greps the log for the marker lines they
print from inside the page.
"""

import pathlib
import re

from odoo.tests import HttpCase, TransactionCase, tagged

MODULE_ROOT = pathlib.Path(__file__).resolve().parents[1]
PALETTE_FILE = MODULE_ROOT / "static" / "src" / "scss" / "sapian_variables.scss"

# The launcher's 'community' theme derives its background from
# $o-brand-primary, which sapian_variables.scss sets to $sapian-brand. Read the
# brand from the palette instead of repeating it here, so a re-brand — the one
# edit this module promises — does not leave this test asserting the old colour
# and passing for the wrong reason.
BRAND_RE = re.compile(r"^\$sapian-brand:\s*(#[0-9A-Fa-f]{6})\s*;", re.MULTILINE)

# web_responsive's own default, which is what we are overriding.
MILK_RGB = (233, 230, 249)


def brand_rgb():
    match = BRAND_RE.search(PALETTE_FILE.read_text(encoding="utf-8"))
    assert match, "could not read $sapian-brand from %s" % PALETTE_FILE
    value = match.group(1)
    return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))


def css_rgb(rgb):
    return "rgb(%d, %d, %d)" % rgb


@tagged("post_install", "-at_install")
class TestLauncherDefaultValues(TransactionCase):
    """The defaults themselves, on whatever database this happens to run on.

    This one is in the STANDARD suite on purpose: sapian_theme claims it stays
    installable with no dependency on web_responsive, and that claim needs a
    check on the databases where web_responsive is absent — which is most of
    them. So it asserts the behaviour appropriate to what is actually
    installed, and reports which branch it took.
    """

    def test_the_defaults_apply_only_where_the_fields_exist(self):
        fields = self.env["res.users"]._fields
        installed = "is_redirect_home" in fields
        defaults = self.env["res.users"].default_get(
            ["is_redirect_home", "apps_menu_theme", "login"]
        )

        if not installed:
            # No web_responsive: our override must invent nothing. If it did,
            # `create` would raise on an unknown field and every user creation
            # on a themed database would break.
            self.assertNotIn("is_redirect_home", defaults)
            self.assertNotIn("apps_menu_theme", defaults)
            user = self.env["res.users"].create(
                {"login": "launcher.nofields.user", "name": "No Launcher Here"}
            )
            self.assertTrue(user.id, "a user must still be creatable without web_responsive")
            return

        self.assertTrue(defaults.get("is_redirect_home"))
        self.assertEqual(defaults.get("apps_menu_theme"), "community")

        # And it reaches a created record, not just default_get: `create` goes
        # through _add_missing_default_values, which calls default_get for
        # every field absent from the values dict.
        user = self.env["res.users"].create(
            {"login": "launcher.created.user", "name": "Created User"}
        )
        self.assertTrue(
            user.is_redirect_home,
            "a user created with no explicit value must get the product default",
        )
        self.assertEqual(user.apps_menu_theme, "community")

    def test_an_explicit_caller_default_still_wins(self):
        """`default_<field>` in the context is a caller stating a preference.

        Without this the demo builders, the control user in the browser tests
        below, and anyone scripting a user import would silently get the
        product default instead of the value they asked for — and the
        discrimination proof in this file would quietly stop discriminating.
        """
        if "is_redirect_home" not in self.env["res.users"]._fields:
            return
        defaults = (
            self.env["res.users"]
            .with_context(default_is_redirect_home=False, default_apps_menu_theme="milk")
            .default_get(["is_redirect_home", "apps_menu_theme"])
        )
        self.assertFalse(defaults.get("is_redirect_home"))
        self.assertEqual(defaults.get("apps_menu_theme"), "milk")


@tagged("post_install", "-at_install")
class TestLauncherProvisioningCommand(TransactionCase):
    """`_sapian_apply_launcher_defaults`, the step the build scripts call.

    The product default cannot reach the one user that matters. Measured:
    `build_demo.sh` and `provision_client.sh` create the admin in their
    `-i base` phase, where `is_redirect_home` does not exist yet, so
    `default_get` never sees it and web_responsive's column default wins. A
    build that installs the launcher and stops hands over a tenant whose only
    user still lands on the Module Catalog.

    Like the class above, this runs on every database and asserts the behaviour
    appropriate to what is installed, so the no-web_responsive path is covered
    too — the build scripts can be pointed at such a database.
    """

    def _has_fields(self):
        return "is_redirect_home" in self.env["res.users"]._fields

    def test_it_says_so_and_does_nothing_without_web_responsive(self):
        if self._has_fields():
            return
        moved = self.env["res.users"]._sapian_apply_launcher_defaults(dry_run=False)
        self.assertFalse(moved, "there is no launcher to default, so nothing may move")

    def test_a_dry_run_reports_and_writes_nothing(self):
        if not self._has_fields():
            return
        stuck = self.env["res.users"].create(
            {
                "login": "provisioning.dryrun.user",
                "name": "Dry Run",
                "is_redirect_home": False,
                "apps_menu_theme": "milk",
            }
        )
        would_move = self.env["res.users"]._sapian_apply_launcher_defaults()
        self.assertIn(stuck, would_move, "the dry run must report the user it would move")
        self.assertFalse(stuck.is_redirect_home, "a DRY RUN wrote to the database")
        self.assertEqual(stuck.apps_menu_theme, "milk", "a DRY RUN wrote to the database")

    def test_applying_it_moves_the_user_the_default_could_not_reach(self):
        if not self._has_fields():
            return
        # Exactly the state build_demo.sh leaves the admin in: created before
        # web_responsive existed, so sitting on the column defaults.
        stuck = self.env["res.users"].create(
            {
                "login": "provisioning.stuck.user",
                "name": "Created Before The Module",
                "is_redirect_home": False,
                "apps_menu_theme": "milk",
            }
        )
        moved = self.env["res.users"]._sapian_apply_launcher_defaults(dry_run=False)
        self.assertIn(stuck, moved)
        self.assertTrue(stuck.is_redirect_home)
        self.assertEqual(stuck.apps_menu_theme, "community")

    def test_it_is_idempotent(self):
        """A second run must report nothing to do, not move everybody again.

        Both build scripts call this on every run, so a command that always
        claimed to have changed something would make its own log useless as
        evidence.
        """
        if not self._has_fields():
            return
        self.env["res.users"].create(
            {
                "login": "provisioning.idempotent.user",
                "name": "Twice",
                "is_redirect_home": False,
                "apps_menu_theme": "milk",
            }
        )
        first = self.env["res.users"]._sapian_apply_launcher_defaults(dry_run=False)
        self.assertTrue(first)
        second = self.env["res.users"]._sapian_apply_launcher_defaults(dry_run=False)
        self.assertFalse(second, "a second run found work to do, so it is not idempotent")

    def test_it_clears_the_home_action_that_outranks_both_fields(self):
        """`action_id` decides the landing before either field is consulted.

        Odoo 19 puts it in `session_info['home_action_id']`, the action service
        falls back to it when the URL carries no action, `loadState()` then
        returns true — and `WebClient.loadRouterState` skips `_loadDefaultApp`,
        which is the only method web_responsive patches and the only place
        `is_redirect_home` is read. So a user with a home action never reaches
        the launcher branch at all.

        Writing True over that produces a user whose settings say launcher and
        whose screen shows a list view a second after login. The provisioning
        command therefore treats a home action as both a reason to move a user
        and something the move removes.
        """
        if not self._has_fields():
            return
        home = self.env.ref("base.action_res_users")
        homed = self.env["res.users"].create(
            {
                "login": "provisioning.homeaction.user",
                "name": "Has A Home Action",
                "action_id": home.id,
            }
        )
        # MEASURED, and the reason this is not merely theoretical: our own
        # `default_get` supplies is_redirect_home=True at create time, and an
        # explicit value beats an editable stored compute. So web_responsive's
        # `_compute_redirect_home` does NOT protect us here — creating a user
        # with a home action produces the lying pair by itself.
        self.assertTrue(
            homed.is_redirect_home,
            "premise changed: the product default no longer wins over "
            "_compute_redirect_home, so this fixture is not the state a tenant "
            "is found in",
        )

        moved = self.env["res.users"]._sapian_apply_launcher_defaults(dry_run=False)
        self.assertIn(homed, moved)
        self.assertFalse(
            homed.action_id,
            "the home action survived, so this user still lands on it and the "
            "launcher flag below is a value the page never delivers",
        )
        # And the flag actually took: `is_redirect_home` is a stored EDITABLE
        # compute depending on action_id, so writing both in one call could
        # have left the compute holding the pen. Asserted, not reasoned about.
        self.assertTrue(homed.is_redirect_home)
        self.assertEqual(homed.apps_menu_theme, "community")

    def test_a_dry_run_names_the_home_action_it_would_remove(self):
        """The one thing here that destroys a deliberate choice must be legible.

        A count of users tells an operator nothing about what they are about to
        lose; the login and the action's name do.
        """
        if not self._has_fields():
            return
        home = self.env.ref("base.action_res_users")
        homed = self.env["res.users"].create(
            {
                "login": "provisioning.dryhome.user",
                "name": "Dry Home",
                "action_id": home.id,
            }
        )
        with self.assertLogs("odoo.addons.sapian_theme.models.res_users", "INFO") as logs:
            would_move = self.env["res.users"]._sapian_apply_launcher_defaults()
        self.assertIn(homed, would_move)
        # `.id`, not the recordset: `res.users.action_id` points at the
        # ir.actions.actions BASE table, so the same row browses as a different
        # model than the act_window it was read from and never compares equal.
        self.assertEqual(homed.action_id.id, home.id, "a DRY RUN wrote to the database")
        reported = "\n".join(logs.output)
        self.assertIn("provisioning.dryhome.user -> %s" % home.name, reported)

    def test_it_leaves_portal_and_public_users_alone(self):
        """`share = True` users never see a backend launcher.

        Writing the fields on them would be harmless but dishonest: the command
        reports how many users it moved, and a count inflated by portal users
        is a count nobody can act on.
        """
        if not self._has_fields():
            return
        portal = self.env["res.users"].create(
            {
                "login": "provisioning.portal.user",
                "name": "Portal",
                "is_redirect_home": False,
                "apps_menu_theme": "milk",
                "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        self.assertTrue(portal.share, "this fixture is only meaningful for a share user")
        moved = self.env["res.users"]._sapian_apply_launcher_defaults(dry_run=False)
        self.assertNotIn(portal, moved)
        self.assertFalse(portal.is_redirect_home)


# ---------------------------------------------------------------------------
# The browser half. Everything below needs web_responsive installed.
# ---------------------------------------------------------------------------

# "Did an action load?" is asked of the action service, not of the DOM.
#
# Two DOM-shaped answers were tried first and both were wrong. The breadcrumb
# is absent on several of Odoo 19's configuration screens. A view-class
# selector misses CLIENT actions entirely — the control user lands on Discuss,
# which renders no `.o_list_view` and no `.o_view_controller`, so the test
# reported "landed nowhere" about a user looking at a perfectly good app.
#
# `action.currentController` is the web client's own answer to the question,
# and it also yields the action's NAME, which is what the landing assertion is
# really about: the launcher, or the Module Catalog.
# A `target="new"` action counts as landing somewhere, too. On a database
# carrying sapian_core the default app is the onboarding wizard, which opens as
# a DIALOG — `currentController` stays null for it, so an earlier version of
# this probe reported "landed nowhere" about a user staring at a modal that
# filled the screen. The control user must be credited with that landing, or it
# stops discriminating on exactly the databases we ship.
ACTION_PROBE = """
    const _svc = (window.odoo && odoo.__WOWL_DEBUG__ && odoo.__WOWL_DEBUG__.root
        && odoo.__WOWL_DEBUG__.root.env.services.action) || null;
    const _ctrl = _svc ? _svc.currentController : null;
    const _dlg = document.querySelector('.modal.d-block, .o_dialog');
    const actionLoaded = !!_ctrl || !!_dlg;
    let actionName = '';
    if (_ctrl && _ctrl.action) {
        actionName = _ctrl.action.name || _ctrl.action.tag || _ctrl.action.xml_id || '?';
    } else if (_dlg) {
        const _t = _dlg.querySelector('.modal-title, header h4, h4');
        actionName = 'dialog: ' + (_t ? _t.innerText.trim() : '?');
    }
"""

LANDING_JS = """
(async () => {
    // The launcher opens during the web client's boot, not synchronously with
    // page load, so poll rather than sample once.
    const currentAction = () => {
        %ACTION_PROBE%
        return actionLoaded;
    };
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline && !document.querySelector('.app-menu-container')
           && !currentAction()) {
        await new Promise((r) => setTimeout(r, 150));
    }
    // Let whichever arrived finish settling: the action manager can render a
    // shell before the view, and the launcher listens for action updates.
    await new Promise((r) => setTimeout(r, 1500));

    %ACTION_PROBE%
    const container = document.querySelector('.app-menu-container');
    const crumb = document.querySelector('.o_breadcrumb');
    const crumbText = crumb ? crumb.innerText.trim().split('\\n')[0] : '';
    const grid = document.querySelector('.o_grid_apps_menu');

    let background = '';
    if (container) {
        background = getComputedStyle(container).backgroundImage || '';
    }

    console.log('SAPIAN-LAUNCHER user=%USER% launcherOpen=' + !!container
        + ' actionLoaded=' + actionLoaded
        + ' action="' + actionName + '"'
        + ' breadcrumb="' + crumbText + '"'
        + ' theme=' + (grid ? grid.dataset.theme : 'none')
        + ' items=' + (container ? container.querySelectorAll('.o-app-menu-item').length : 0)
        + ' brandInBackground=' + background.includes('%BRAND%')
        + ' milkInBackground=' + background.includes('%MILK%'));

    %ASSERTIONS%

    console.log('test successful');
})();
"""

LANDS_ON_LAUNCHER = """
    if (!container) {
        throw new Error('the launcher did not open on login — landed on "'
            + (actionName || crumbText || document.title) + '" instead');
    }
    if (actionLoaded) {
        throw new Error('an action loaded behind the launcher: "' + actionName + '"');
    }
    if (!container.querySelectorAll('.o-app-menu-item').length) {
        throw new Error('the launcher opened with no apps in it');
    }
    if (!background.includes('%BRAND%')) {
        throw new Error('the launcher background does not carry the brand %BRAND%; '
            + 'computed background-image was: ' + background);
    }
    if (background.includes('%MILK%')) {
        throw new Error('the launcher is still painted the web_responsive milk '
            + 'lilac %MILK%');
    }
"""

LANDS_ON_AN_ACTION = """
    if (container) {
        throw new Error('CONTROL FAILED: the control user opted OUT of the '
            + 'redirect and still landed on the launcher, so this file cannot '
            + 'tell a working default from a broken one');
    }
    if (!actionLoaded) {
        throw new Error('CONTROL FAILED: no launcher and no action either — '
            + 'the control user landed nowhere, so it discriminates nothing');
    }
"""

MILK_CONTROL = """
    if (!container) {
        throw new Error('CONTROL FAILED: the milk control user did not reach '
            + 'the launcher, so its colour proves nothing');
    }
    if (!background.includes('%MILK%')) {
        throw new Error('CONTROL FAILED: apps_menu_theme=milk did not produce '
            + 'the milk lilac %MILK%, so the colour assertion is not reading '
            + 'the theme; computed background-image was: ' + background);
    }
    if (background.includes('%BRAND%')) {
        throw new Error('CONTROL FAILED: the milk theme carries the brand '
            + '%BRAND% anyway, so the brand check cannot discriminate');
    }
"""


class LauncherBrowserCase(HttpCase):
    """Shared fixtures: real users, real passwords, tours off."""

    def setUp(self):
        super().setUp()
        # Odoo's onboarding tour auto-starts on /odoo and clicks its way around
        # the UI, including into a different app — which is precisely the
        # landing this file measures. Same reason test_app_rail.py does it.
        for user in self.env["res.users"].search([]):
            if "tour_enabled" in user._fields:
                user.sudo().tour_enabled = False
        self.env.flush_all()

    def make_user(self, login, **context):
        """A user whose password equals its login, because `browser_js` calls
        `authenticate(login, login)` (odoo/tests/common.py). group_system so
        the default app is the same configuration screen the admin gets —
        otherwise the control user would land somewhere else for an unrelated
        reason and prove nothing."""
        return (
            self.env["res.users"]
            .with_context(**context)
            .create(
                {
                    "login": login,
                    "password": login,
                    "name": login,
                    "group_ids": [
                        (
                            6,
                            0,
                            [
                                self.env.ref("base.group_user").id,
                                self.env.ref("base.group_system").id,
                            ],
                        )
                    ],
                }
            )
        )

    def run_landing(self, login, assertions):
        code = (
            LANDING_JS.replace("%ASSERTIONS%", assertions)
            .replace("%USER%", login)
            .replace("%ACTION_PROBE%", ACTION_PROBE)
            .replace("%BRAND%", css_rgb(brand_rgb()))
            .replace("%MILK%", css_rgb(MILK_RGB))
        )
        self.browser_js(
            "/odoo",
            code,
            # Must evaluate to a BOOLEAN: ChromeBrowser._wait_ready compares the
            # CDP result against {'type': 'boolean', 'value': True}, so a bare
            # querySelector returning an Element is never "ready".
            "!!document.querySelector('.o_main_navbar')",
            login=login,
        )


@tagged("post_install", "-at_install", "-standard", "sapian_launcher")
class TestLauncherLandingOnTheWire(LauncherBrowserCase):
    """Requirement 1 and 2: the landing page, and the colour it is painted."""

    browser_size = "1366x900"

    def test_a_fresh_user_lands_on_the_launcher_in_our_brand(self):
        login = "launcher.default.user"
        user = self.make_user(login)
        # The field is only the premise; the page is the proof.
        self.assertTrue(user.is_redirect_home)
        self.assertEqual(user.apps_menu_theme, "community")
        self.run_landing(login, LANDS_ON_LAUNCHER)

    def test_a_user_who_opts_out_still_lands_on_the_configuration_screen(self):
        """The discrimination proof for the redirect.

        If this user ALSO reached the launcher, the test above would pass on a
        database where the default did nothing.
        """
        login = "launcher.control.user"
        user = self.make_user(login, default_is_redirect_home=False)
        self.assertFalse(user.is_redirect_home)
        self.run_landing(login, LANDS_ON_AN_ACTION)

    def test_the_milk_theme_still_paints_lilac(self):
        """The discrimination proof for the colour.

        Proves the assertion reads the theme rather than matching whatever the
        launcher happens to be painted.
        """
        login = "launcher.milk.user"
        user = self.make_user(login, default_apps_menu_theme="milk")
        self.assertEqual(user.apps_menu_theme, "milk")
        self.run_landing(login, MILK_CONTROL)


# ---------------------------------------------------------------------------
# The landing has to HOLD, not merely happen.
# ---------------------------------------------------------------------------

# Measured on demo_selam, admin with is_redirect_home=True and a home action:
#
#   1205 ms   /odoo             launcher visible, 12 tiles
#   1442 ms   /odoo             list view mounted underneath
#   1562 ms   /odoo/action-101  launcher gone
#
# Every assertion above this line samples inside the first window and passes.
# The launcher renders correctly and is then replaced, which is why this guard
# waits for the client to go quiet and then sits still for another 2.5 seconds
# before it looks. It also reads `location.pathname`, because the URL is the
# thing an operator actually reported and the thing a screen recording shows.
STAYS_PUT_JS = """
(async () => {
    const settled = async () => {
        const deadline = Date.now() + 20000;
        while (Date.now() < deadline) {
            %ACTION_PROBE%
            if (actionLoaded || document.querySelector('.app-menu-container')) {
                return;
            }
            await new Promise((r) => setTimeout(r, 150));
        }
    };
    await settled();

    const early = {
        url: location.pathname,
        launcher: !!document.querySelector('.app-menu-container'),
    };

    // THE DWELL. Not a guess at a duration: the whole defect is that the
    // override arrives AFTER the launcher has painted, so a check that samples
    // once cannot see it. 2500 ms is comfortably past the 357 ms gap measured
    // above, on a machine an order of magnitude slower than the one that
    // produced it.
    await new Promise((r) => setTimeout(r, 2500));

    %ACTION_PROBE%
    const container = document.querySelector('.app-menu-container');
    const items = container ? container.querySelectorAll('.o-app-menu-item').length : 0;

    console.log('SAPIAN-LAUNCHER-STAYS user=%USER%'
        + ' earlyUrl=' + early.url + ' earlyLauncher=' + early.launcher
        + ' url=' + location.pathname
        + ' launcher=' + !!container + ' items=' + items
        + ' actionLoaded=' + actionLoaded + ' action="' + actionName + '"');

    if (!early.launcher) {
        throw new Error('the launcher never appeared at all, so this test is '
            + 'not measuring what it claims to; landed on ' + early.url);
    }
    if (location.pathname !== '/odoo') {
        throw new Error('the client navigated away from the launcher on its '
            + 'own: ' + early.url + ' -> ' + location.pathname
            + ' (action "' + actionName + '"). Nobody clicked anything.');
    }
    if (!container) {
        throw new Error('the launcher was replaced in place — still at /odoo, '
            + 'but the app grid is gone and "' + actionName + '" is loaded');
    }
    if (actionLoaded) {
        throw new Error('an action loaded behind the launcher: "' + actionName
            + '" — it will take the screen as soon as the launcher closes');
    }
    if (!items) {
        throw new Error('the launcher is still there but empty');
    }

    console.log('test successful');
})();
"""


@tagged("post_install", "-at_install", "-standard", "sapian_launcher")
class TestLauncherStaysOnTheLauncher(LauncherBrowserCase):
    """A provisioned user lands on the launcher AND IS STILL THERE 2.5s later.

    WHY THE FIXTURE SETS A HOME ACTION
    ----------------------------------
    Because that is the only thing in this stack that produces the defect, and
    a guard that cannot go red is decoration (CLAUDE.md). The user is created
    with `action_id` set, then handed to the same provisioning command the build
    scripts call — so this measures the command's output, not a hand-made state.

    Against the code before this change the command wrote `is_redirect_home =
    True`, left the home action alone, and this test fails with
    `/odoo -> /odoo/action-N`. Proof of that red run is in the PR body.
    """

    browser_size = "1366x900"

    def test_a_provisioned_user_stays_on_the_launcher(self):
        login = "launcher.stays.user"
        user = self.make_user(login)
        # The state a tenant is actually found in: somebody set a home action
        # in Preferences, which switches the flag off by web_responsive's own
        # compute.
        user.action_id = self.env.ref("base.action_res_users").id
        self.assertFalse(user.is_redirect_home)

        moved = self.env["res.users"]._sapian_apply_launcher_defaults(dry_run=False)
        self.assertIn(user, moved, "provisioning did not consider this user at all")
        self.env.flush_all()

        code = STAYS_PUT_JS.replace("%USER%", login).replace("%ACTION_PROBE%", ACTION_PROBE)
        self.browser_js(
            "/odoo",
            code,
            "!!document.querySelector('.o_main_navbar')",
            login=login,
        )


# ---------------------------------------------------------------------------
# Requirement 3: the occlusion the rail's own tests do not cover.
# ---------------------------------------------------------------------------

OCCLUSION_JS = """
// Returns a description of WHO OWNS THE PIXEL at the rail's centre. The rail's
// existing tests assert geometry and content — tile count, icon decoding,
// padding — all of which stay true while something paints on top of it. This
// is the missing question, and it is answered with elementFromPoint rather
// than by comparing z-index values, because stacking contexts make the CSS a
// bad predictor of what the user can actually click.
async function railOcclusion() {
    const rail = document.querySelector('.o_sapian_rail');
    if (!rail) {
        return {error: 'no .o_sapian_rail in the DOM'};
    }
    const box = rail.getBoundingClientRect();
    const cx = box.left + box.width / 2;
    const cy = box.top + Math.min(box.height / 2, 300);
    const top = document.elementFromPoint(cx, cy);
    return {
        railReachable: !!(top && rail.contains(top)),
        topOwner: top ? top.tagName + '.' + (top.className || '') : 'nothing',
        launcherOpen: !!document.querySelector('.app-menu-container'),
        tiles: rail.querySelectorAll('.o_sapian_rail_app').length,
        display: getComputedStyle(rail).display,
        visibility: getComputedStyle(rail).visibility,
        // The class our CSS keys off. web_responsive puts it on <body>
        // (apps_menu.esm.js:28); sapian_rail.scss hides the rail from it.
        bodyClass: document.body.classList.contains('o_apps_menu_opened'),
        scrollTop: rail.scrollTop,
    };
}

(async () => {
    const settle = () => new Promise((r) => setTimeout(r, 400));
    const waitFor = async (predicate, ms) => {
        const deadline = Date.now() + ms;
        while (Date.now() < deadline) {
            if (predicate()) { return true; }
            await new Promise((r) => setTimeout(r, 100));
        }
        return false;
    };
    const launcherIsOpen = () => !!document.querySelector('.app-menu-container');

    // The web client is still loading its default action when the page becomes
    // ready, and AppsMenu closes itself on every ACTION_MANAGER:UI-UPDATED. A
    // click landing in that window opens the launcher and then loses it, which
    // reads exactly like "the button does not work". Wait for quiet first.
    await waitFor(() => {
        %ACTION_PROBE%
        return actionLoaded;
    }, 20000);
    await new Promise((r) => setTimeout(r, 1500));

    // A default app that opens as a dialog (sapian_core's onboarding wizard
    // does) owns every click on the page, including the launcher button. Clear
    // it first, or this test fails reporting "the launcher did not open" about
    // a button that was simply behind a modal backdrop.
    for (let i = 0; i < 3 && document.querySelector('.modal.d-block'); i++) {
        const close = document.querySelector(
            '.modal.d-block .btn-close, .modal.d-block button[aria-label="Close"]');
        if (close) {
            close.click();
        } else {
            document.body.dispatchEvent(
                new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
        }
        await settle();
    }
    if (document.querySelector('.modal.d-block')) {
        throw new Error('a dialog is covering the page and would not close, so '
            + 'nothing below could click the launcher');
    }
    await settle();

    // 1. Launcher closed: the rail must own its own pixels.
    const closed = await railOcclusion();
    if (closed.error) { throw new Error(closed.error); }
    if (closed.launcherOpen) {
        throw new Error('the launcher was already open before this test '
            + 'opened it, so the closed-state measurement means nothing');
    }
    if (!closed.railReachable) {
        throw new Error('the rail is covered by ' + closed.topOwner
            + ' with the launcher CLOSED — something is on top of it that '
            + 'should not be');
    }

    // 2. Open the launcher. THE RAIL NOW STANDS DOWN COMPLETELY.
    //
    //    AMENDED. This step used to assert only that the launcher COVERS the
    //    rail, and it passed while a 200x44 strip of rail stuck out above the
    //    overlay in the top-left corner — the launcher is fixed at z-index
    //    1024 with the box [0, 46, 1366, 854], the rail is z-index 1020 from
    //    y=0, so the top 46px was never covered by construction. It was
    //    hoverable and clickable there, and hovering it is how the header's
    //    transparency was found.
    //
    //    This probe could not see that: it samples the rail's centre at
    //    y = min(height/2, 300), which the overlay does cover. Sampling one
    //    point and calling it occlusion is the same shape of mistake as
    //    measuring the login card and calling it the page.
    //
    //    So the decision on the record has changed: the rail is HIDDEN while
    //    the launcher is open, not merely covered. The launcher already lists
    //    every app; the rail lists the same apps; a strip too small to
    //    navigate by and large enough to misclick is the worst of both.
    document.querySelector('.o_grid_apps_menu__button').click();
    if (!await waitFor(launcherIsOpen, 5000)) {
        // One retry: a late action update can swallow the first click.
        document.querySelector('.o_grid_apps_menu__button').click();
        await waitFor(launcherIsOpen, 5000);
    }
    await settle();
    const open = await railOcclusion();
    if (!open.launcherOpen) {
        throw new Error('the launcher did not open, so this test proves '
            + 'nothing about occlusion');
    }
    if (open.railReachable) {
        throw new Error('the launcher is open but the rail is still on top of '
            + 'it (owner: ' + open.topOwner + ') — the overlay is not covering '
            + 'the full width, which means the rail is painting over the app '
            + 'grid');
    }
    if (open.tiles !== closed.tiles) {
        throw new Error('opening the launcher changed the rail from '
            + closed.tiles + ' tiles to ' + open.tiles);
    }
    if (!open.bodyClass) {
        throw new Error('the launcher is open but <body> does not carry '
            + 'o_apps_menu_opened — that class is what sapian_rail.scss keys '
            + 'off, so the rule under test is keyed to something that does '
            + 'not happen');
    }
    if (open.visibility !== 'hidden') {
        throw new Error('the launcher is open but the rail computes '
            + 'visibility=' + open.visibility + ' — it should stand down '
            + 'entirely, not merely be covered where the overlay reaches');
    }
    // STILL IN THE DOM, and this half of the old assertion is kept unchanged.
    // `visibility` was chosen over `display: none` and over unmounting
    // precisely so the element keeps its box and its scrollTop across a round
    // trip the user makes constantly.
    if (open.display === 'none') {
        throw new Error('opening the launcher REMOVED the rail from layout; it '
            + 'must stay laid out so its scroll position survives');
    }

    // 3. Dismiss it. The rail must be reachable again, undamaged.
    document.body.dispatchEvent(
        new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
    await settle();
    let after = await railOcclusion();
    if (after.launcherOpen) {
        // Escape is web_responsive's hotkey; fall back to clicking the toggle
        // so a hotkey-service change cannot fail this test for the wrong
        // reason.
        document.querySelector('.o_grid_apps_menu__button').click();
        await settle();
        after = await railOcclusion();
    }
    if (after.launcherOpen) {
        throw new Error('the launcher would not close');
    }
    if (!after.railReachable) {
        throw new Error('the launcher closed but the rail is STILL covered by '
            + after.topOwner + ' — the overlay left something behind');
    }
    if (after.tiles !== closed.tiles) {
        throw new Error('the rail came back with ' + after.tiles
            + ' tiles instead of ' + closed.tiles);
    }
    if (after.visibility !== 'visible') {
        throw new Error('the launcher closed but the rail is still '
            + 'visibility=' + after.visibility);
    }
    if (after.scrollTop !== closed.scrollTop) {
        throw new Error('the rail lost its scroll position across the launcher '
            + 'round trip: ' + closed.scrollTop + ' -> ' + after.scrollTop
            + ' — which is what `display: none` would have cost');
    }

    console.log('SAPIAN-RAIL-OCCLUSION closed=' + closed.railReachable
        + ' open=' + open.railReachable + ' owner="' + open.topOwner + '"'
        + ' reopened=' + after.railReachable
        + ' visibility=' + closed.visibility + '/' + open.visibility
        + '/' + after.visibility
        + ' bodyClass=' + closed.bodyClass + '/' + open.bodyClass
        + ' scroll=' + closed.scrollTop + '/' + after.scrollTop
        + ' tiles=' + closed.tiles + '/' + open.tiles + '/' + after.tiles);
    console.log('test successful');
})();
"""


@tagged("post_install", "-at_install", "-standard", "sapian_launcher")
class TestRailOcclusionUnderTheLauncher(HttpCase):
    """The rail stands down while the launcher is up, and returns intact.

    Added because the rail's existing suite asserts geometry and content but
    not occlusion, so it would stay green if the launcher started covering the
    rail permanently, or stopped covering it and let the rail paint over the
    app grid.

    AMENDED once already, and the amendment is the lesson: asserting occlusion
    at ONE point (the rail's centre) passed while a 200x44 strip of rail stuck
    out above the overlay at the top-left corner, where this probe does not
    look. It now asserts the rail's computed `visibility` — a property of the
    whole element — and that the body class our CSS keys off is really set by
    the real launcher, which is the half a hand-added class in
    `test_app_rail.py` cannot prove.
    """

    browser_size = "1366x900"

    def setUp(self):
        super().setUp()
        admin = self.env.ref("base.user_admin")
        if "tour_enabled" in admin._fields:
            admin.sudo().tour_enabled = False
        # The admin must NOT land on the launcher here: this test opens and
        # closes it deliberately, and needs a known starting state.
        if "is_redirect_home" in admin._fields:
            admin.sudo().is_redirect_home = False
        self.env.flush_all()

    def test_the_launcher_covers_the_rail_and_gives_it_back(self):
        self.browser_js(
            "/odoo",
            OCCLUSION_JS.replace("%ACTION_PROBE%", ACTION_PROBE),
            "!!document.querySelector('.o_sapian_rail .o_sapian_rail_app') "
            "&& !!document.querySelector('.o_grid_apps_menu__button')",
            login="admin",
        )
