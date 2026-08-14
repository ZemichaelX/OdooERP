# -*- coding: utf-8 -*-
"""The app rail, asserted in a real browser.

WHY A BROWSER AND NOT A SOURCE ASSERTION
----------------------------------------
The rail is an OWL component. `/odoo` serves a bootstrap shell; the rail does
not exist in that HTML, and no amount of grepping the served page or the
compiled bundle proves it renders. The login defect (README.md, "prefer assets
to template inheritance") is the precedent: the SCSS said teal, the bundle
contained the brand seven times, and the button rendered Odoo purple. Every
source-level assertion available at the time passed.

So these tests drive headless Chrome, log in, load the web client, and look at
the DOM the user gets.

THE INVARIANT, NOT A NUMBER
---------------------------
There is no expected tile count in this file. The expectation is derived per
run from `/web/webclient/load_menus` — the same endpoint the rail's own data
comes from — so the guard stays correct on a database with 3 apps, 36, or 60.
Writing 36 here would turn "the rail shows every app" into "the rail shows
thirty-six things", and the first client to install one more module would get a
red build for a working product.

A NOTE ON THE BROWSER
---------------------
`HttpCase.browser_js` raises `unittest.SkipTest` when no Chrome is found
(odoo/tests/common.py:2153), and a skip is a success signal produced by doing
nothing — the exact shape CLAUDE.md forbids. It is therefore not enough that
these tests exist: the CI job that runs them (`rail-render` in
.github/workflows/ci.yml) greps the log for the `SAPIAN-RAIL ...` line these
tests print from inside the browser, and fails when it is absent. A skipped
run cannot produce that line.
"""

from odoo.tests import HttpCase, tagged

# ---------------------------------------------------------------------------
# The check itself, defined once and used by both the assertion and the
# discrimination proof. It RETURNS a problem list rather than throwing, so the
# discrimination test can run the very same code against a deliberately broken
# DOM and assert that it complains.
# ---------------------------------------------------------------------------
RAIL_REPORT_JS = """
async function sapianRailReport() {
    const problems = [];
    const rail = document.querySelector('.o_sapian_rail');
    if (!rail) {
        problems.push('no .o_sapian_rail element in the DOM');
        return { problems, tiles: 0, apps: null, loaded: 0, visible: 0 };
    }
    // The expectation comes from the server, never from a constant here.
    const menus = await (await fetch('/web/webclient/load_menus',
                                     { cache: 'no-store' })).json();
    const apps = menus.root.children.length;
    const tiles = [...rail.querySelectorAll('.o_sapian_rail_app')];
    if (tiles.length !== apps) {
        problems.push('rail shows ' + tiles.length + ' tiles for ' + apps
                      + ' root apps');
    }
    const imgs = tiles.map((t) => t.querySelector('img.o_sapian_rail_icon'));
    // data: URIs decode fast but not synchronously.
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline && imgs.some((i) => i && !i.complete)) {
        await new Promise((r) => setTimeout(r, 100));
    }
    let loaded = 0;
    let visible = 0;
    tiles.forEach((tile, i) => {
        const img = imgs[i];
        const label = tile.dataset.menuXmlid
            || tile.getAttribute('aria-label') || ('#' + i);
        const box = tile.getBoundingClientRect();
        if (box.top >= 0 && box.bottom <= window.innerHeight) {
            visible++;
        }
        if (!img) {
            problems.push(label + ': no <img> — fell back to the text initial');
        } else if (!img.getAttribute('src')) {
            problems.push(label + ': <img> has an empty src');
        } else if (!img.naturalWidth) {
            problems.push(label + ': <img> src did not decode to an image');
        } else {
            loaded++;
        }
    });
    return { problems, tiles: tiles.length, apps, loaded, visible };
}
"""

RAIL_RENDERS_JS = RAIL_REPORT_JS + """
(async () => {
    const report = await sapianRailReport();
    const rail = document.querySelector('.o_sapian_rail');

    // Everything must be REACHABLE. Nothing is truncated: scrolling to the
    // bottom must actually bring the last app into the viewport.
    let lastReachable = false;
    if (rail && report.tiles) {
        rail.scrollTop = rail.scrollHeight;
        await new Promise((r) => requestAnimationFrame(() => r()));
        const last = [...rail.querySelectorAll('.o_sapian_rail_app')].pop()
                     .getBoundingClientRect();
        lastReachable = last.top >= -1 && last.bottom <= window.innerHeight + 1;
        rail.scrollTop = 0;
        await new Promise((r) => requestAnimationFrame(() => r()));
    }

    // One line of positive evidence in the server log. A run that skipped, or
    // never reached the browser, cannot print this.
    console.log('SAPIAN-RAIL viewport=' + window.innerWidth + 'x'
        + window.innerHeight
        + ' apps=' + report.apps + ' tiles=' + report.tiles
        + ' loaded=' + report.loaded
        + ' visibleWithoutScrolling=' + report.visible
        + ' lastReachableByScrolling=' + lastReachable);

    if (report.problems.length) {
        throw new Error('rail: ' + report.problems.join(' | '));
    }
    const style = getComputedStyle(rail);
    if (style.position !== 'fixed') {
        throw new Error('the rail is not fixed: position=' + style.position);
    }
    if (style.display === 'none') {
        throw new Error('the rail is hidden on a desktop viewport');
    }
    if (!lastReachable) {
        throw new Error('the last app is not reachable by scrolling the rail — '
            + 'apps are being truncated');
    }
    // The rail must not sit ON TOP of the content it is next to.
    const body = document.querySelector('.o_web_client');
    const padding = parseFloat(getComputedStyle(body).paddingLeft) || 0;
    const width = rail.getBoundingClientRect().width;
    if (padding + 0.5 < width) {
        throw new Error('the web client is padded ' + padding
            + 'px for a rail ' + width + 'px wide — the rail overlaps content');
    }
    console.log('test successful');
})();
"""

RAIL_DISCRIMINATES_JS = RAIL_REPORT_JS + """
(async () => {
    // Prove the check goes red for each thing it claims to check, by breaking
    // that thing on purpose. An untested guard is one more thing that passes
    // by doing nothing.
    const rail = document.querySelector('.o_sapian_rail');
    const anchor = rail.nextSibling;
    const parent = rail.parentNode;

    // 1. no rail at all
    rail.remove();
    let report = await sapianRailReport();
    if (!report.problems.length) {
        throw new Error('DISCRIMINATION FAILED: the check passed with no rail '
            + 'in the DOM');
    }
    console.log('SAPIAN-RAIL-DISCRIMINATION no-rail -> ' + report.problems[0]);
    parent.insertBefore(rail, anchor);

    // 2. one app missing from the rail
    const tile = rail.querySelector('.o_sapian_rail_app');
    const tileAnchor = tile.nextSibling;
    tile.remove();
    report = await sapianRailReport();
    if (!report.problems.length) {
        throw new Error('DISCRIMINATION FAILED: the check passed with a tile '
            + 'missing');
    }
    console.log('SAPIAN-RAIL-DISCRIMINATION missing-tile -> '
        + report.problems[0]);
    rail.insertBefore(tile, tileAnchor);

    // 3. a tile with no icon
    const img = tile.querySelector('img.o_sapian_rail_icon');
    const imgAnchor = img.nextSibling;
    img.remove();
    report = await sapianRailReport();
    if (!report.problems.length) {
        throw new Error('DISCRIMINATION FAILED: the check passed with a tile '
            + 'that has no icon');
    }
    console.log('SAPIAN-RAIL-DISCRIMINATION iconless-tile -> '
        + report.problems[0]);
    tile.insertBefore(img, imgAnchor);

    // 4. and it recovers — a check that reports a problem unconditionally
    //    would have passed 1-3 while being useless.
    report = await sapianRailReport();
    if (report.problems.length) {
        throw new Error('the check does not recover once the DOM is restored: '
            + report.problems.join(' | '));
    }
    console.log('SAPIAN-RAIL-DISCRIMINATION restored -> clean');
    console.log('test successful');
})();
"""

RAIL_OVERFLOWS_JS = RAIL_REPORT_JS + """
(async () => {
    const rail = document.querySelector('.o_sapian_rail');
    const tiles = [...rail.querySelectorAll('.o_sapian_rail_app')];
    if (tiles.length < 2) {
        throw new Error('need at least two apps to test scrolling; found '
            + tiles.length);
    }

    // CREATE the condition rather than wait for a database that happens to
    // have it. A short viewport was tried first and it does not work: with
    // `website` + `sapian_theme` alone there are 4 root apps, 192px of tiles,
    // which fits any plausible viewport — so the test failed its own
    // precondition on a perfectly healthy build. Forcing the rail shorter than
    // its content exercises the overflow path on ANY database, from two apps
    // to sixty.
    //
    // `height` wins over `bottom` on an over-constrained fixed box, so this is
    // one property, not a rewrite of the element's positioning.
    //
    // Size it from the TILES, not from scrollHeight: when the content is
    // shorter than the box, scrollHeight reports the BOX height, so halving it
    // just produces a smaller box that still fits — measured, scrollHeight 900
    // <= clientHeight 900 on a four-app database, twice in a row.
    const tileHeight = tiles[0].getBoundingClientRect().height;
    const forced = Math.floor(tileHeight * (tiles.length - 1));
    rail.style.height = forced + 'px';
    await new Promise((r) => requestAnimationFrame(() => r()));

    if (rail.scrollHeight <= rail.clientHeight) {
        rail.style.height = '';
        throw new Error('could not force the rail to overflow (scrollHeight '
            + rail.scrollHeight + ' <= clientHeight ' + rail.clientHeight
            + '), so this test proves nothing about scrolling');
    }

    // Visibility is measured against the RAIL's own box, not the viewport,
    // because the rail is now deliberately shorter than the screen.
    const inRail = (tile) => {
        const box = tile.getBoundingClientRect();
        const railBox = rail.getBoundingClientRect();
        return box.top >= railBox.top - 1 && box.bottom <= railBox.bottom + 1;
    };
    const before = tiles.filter(inRail).length;
    if (before >= tiles.length) {
        rail.style.height = '';
        throw new Error('every tile is still visible; nothing to scroll to');
    }

    rail.scrollTop = rail.scrollHeight;
    await new Promise((r) => requestAnimationFrame(() => r()));
    const reachable = inRail(tiles[tiles.length - 1]);

    console.log('SAPIAN-RAIL-OVERFLOW forcedRailHeight=' + forced
        + ' contentHeight=' + rail.scrollHeight
        + ' tiles=' + tiles.length
        + ' visibleWithoutScrolling=' + before
        + ' lastReachableByScrolling=' + reachable);

    rail.style.height = '';
    rail.scrollTop = 0;
    await new Promise((r) => requestAnimationFrame(() => r()));

    if (!reachable) {
        throw new Error('the rail overflows and the last app CANNOT be reached '
            + 'by scrolling — apps are being silently truncated');
    }
    const report = await sapianRailReport();
    if (report.tiles !== report.apps) {
        throw new Error('overflow dropped tiles: ' + report.tiles + ' of '
            + report.apps);
    }
    console.log('test successful');
})();
"""

RAIL_HIDDEN_JS = """
(async () => {
    const rail = document.querySelector('.o_sapian_rail');
    if (!rail) {
        throw new Error('the rail element should still exist in the DOM below '
            + 'md — it is hidden by CSS, not by a template condition');
    }
    const display = getComputedStyle(rail).display;
    const body = document.querySelector('.o_web_client');
    const padding = parseFloat(getComputedStyle(body).paddingLeft) || 0;
    console.log('SAPIAN-RAIL-SMALL viewport=' + window.innerWidth + 'x'
        + window.innerHeight + ' display=' + display
        + ' padding-left=' + padding);
    if (display !== 'none') {
        throw new Error('the rail is showing below md: display=' + display);
    }
    if (padding > 0.5) {
        throw new Error('the web client is indented ' + padding + 'px for a '
            + 'rail that is not shown');
    }
    console.log('test successful');
})();
"""


class RailBrowserCase(HttpCase):
    """Shared setup for the browser-driven rail tests."""

    def setUp(self):
        super().setUp()
        # Odoo's onboarding tour auto-starts on /odoo for an admin whose
        # `tour_enabled` was stored True, and then clicks its way around the UI
        # — including into a different app, which moves the very highlight
        # these tests look at. Observed: the tour clicked
        # `.o_app[data-menu-xmlid="crm.crm_menu_root"]` and the ready-check
        # timed out behind it. Nothing here is about tours; turn them off.
        admin = self.env.ref("base.user_admin")
        if "tour_enabled" in admin._fields:
            admin.sudo().tour_enabled = False
            self.env.flush_all()


@tagged("post_install", "-at_install")
class TestSapianAppRailRendered(RailBrowserCase):
    """Desktop. 900px tall on purpose: it is the height the design was sized
    against, and it is where 36 apps stop fitting."""

    browser_size = "1366x900"

    def test_the_rail_renders_one_loaded_icon_per_app(self):
        self.browser_js(
            "/odoo",
            RAIL_RENDERS_JS,
            # If the rail never renders, this never becomes true and the test
            # fails on the ready check rather than silently asserting nothing.
            # It must evaluate to a BOOLEAN: ChromeBrowser._wait_ready compares
            # the CDP result against {'type': 'boolean', 'value': True}
            # (odoo/tests/common.py:1877), so a bare querySelector returning an
            # Element is never "ready" and the test times out looking healthy.
            "!!document.querySelector('.o_sapian_rail .o_sapian_rail_app')",
            login="admin",
        )

    def test_the_rail_check_discriminates(self):
        self.browser_js(
            "/odoo",
            RAIL_DISCRIMINATES_JS,
            "!!document.querySelector('.o_sapian_rail .o_sapian_rail_app')",
            login="admin",
        )


@tagged("post_install", "-at_install")
class TestSapianAppRailOverflow(RailBrowserCase):
    """The design decision, asserted.

    36 apps do not fit on a laptop screen and the rail refuses to hide any of
    them, so it scrolls. This test forces the rail shorter than its own content
    so that the overflow path is exercised on EVERY database — a two-app CI
    install as much as a 36-app tenant — instead of only on the ones that
    happen to be crowded.
    """

    browser_size = "1366x900"

    def test_every_app_stays_reachable_when_the_rail_overflows(self):
        self.browser_js(
            "/odoo",
            RAIL_OVERFLOWS_JS,
            "!!document.querySelector('.o_sapian_rail .o_sapian_rail_app')",
            login="admin",
        )


@tagged("post_install", "-at_install")
class TestSapianAppRailSmallScreen(RailBrowserCase):
    """Below md the rail must be gone AND the gap it leaves must be gone with
    it. Odoo's own drawer (web.NavBar.AppsMenu.Sidebar) draws the icons there,
    so nothing is lost."""

    browser_size = "375x667"

    def test_the_rail_is_absent_below_md(self):
        self.browser_js(
            "/odoo",
            RAIL_HIDDEN_JS,
            "!!document.querySelector('.o_main_navbar')",
            login="admin",
        )


@tagged("post_install", "-at_install")
class TestAppRailDataOverHttp(HttpCase):
    """The rail's data source, fetched over HTTP as a logged-in user.

    This one needs no browser, so it runs everywhere the suite runs. It cannot
    prove the rail renders — that is what the tests above are for — but it does
    catch the regression that would empty it, and it catches it in every CI job
    rather than only in the one that installs Chrome.
    """

    def test_every_root_app_reaches_the_browser_with_icon_data(self):
        self.authenticate("admin", "admin")
        response = self.url_open("/web/webclient/load_menus")
        self.assertEqual(response.status_code, 200)
        menus = response.json()

        children = menus["root"]["children"]
        self.assertTrue(children, "no root apps at all — the rail would be empty")

        iconless = [
            menus[str(app_id)]["xmlid"] or menus[str(app_id)]["name"]
            for app_id in children
            if not menus[str(app_id)].get("webIconData")
        ]
        self.assertFalse(
            iconless,
            "root apps reach the browser with no webIconData, so the rail has "
            "nothing to draw for them: %s" % ", ".join(iconless),
        )
