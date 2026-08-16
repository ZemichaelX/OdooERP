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

from .. import brand

# ---------------------------------------------------------------------------
# The check itself, defined once and used by both the assertion and the
# discrimination proof. It RETURNS a problem list rather than throwing, so the
# discrimination test can run the very same code against a deliberately broken
# DOM and assert that it complains.
# ---------------------------------------------------------------------------
# Forcing overflow has to account for the sticky brand header: a box of
# tileHeight * (n - 1) is ENTIRELY FILLED by the 44px header on a small
# database, so the condition created is "nothing fits" rather than "the rail
# overflows". Measured — a two-app database failed exactly that way, and the
# failure read as truncation.
SAPIAN_FORCED_HEIGHT = """
function sapianForcedHeight(rail, tileHeight, count) {
    const header = rail.querySelector('.o_sapian_rail_toggle');
    const headH = header ? header.getBoundingClientRect().height : 0;
    // Room for the header and one FEWER tile than exists, so the box always
    // overflows and at least one tile is genuinely out of view. Asking for
    // "at least two tiles" was tried and is wrong on a two-app database: it
    // fits both, and the test's own precondition then fails with "every tile
    // is still visible; nothing to scroll to".
    return Math.floor(headH + tileHeight * Math.max(1, count - 1));
}
"""

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

// The reachability half, split out for one reason: the discrimination proof
// has to be able to run THIS code against a deliberately broken DOM. Left
// inline in the assertion it would have been a guard nobody could break, which
// is the defect it was written to remove.
async function sapianRailReach() {
    const rail = document.querySelector('.o_sapian_rail');
    const tiles = [...rail.querySelectorAll('.o_sapian_rail_app')];
    // THE VISIBLE AREA IS THE BOX MINUS THE STICKY HEADER. The brand header is
    // `position: sticky; top: 0`, so it covers the top 44px of the scroll
    // viewport at every scroll position and tiles slide UNDER it. Measuring
    // against the raw box counted a tile hidden behind the header as visible —
    // caught when a two-app database forced the box down to one row and the
    // header filled all of it.
    const railBox = rail.getBoundingClientRect();
    const header = rail.querySelector('.o_sapian_rail_toggle');
    const headBox = header ? header.getBoundingClientRect() : null;
    const box = {
        top: headBox ? Math.max(railBox.top, headBox.bottom) : railBox.top,
        bottom: railBox.bottom,
        left: railBox.left,
        right: railBox.right,
    };
    // FULL containment, all four edges. Testing only top/bottom let a tile
    // pushed sideways out of the panel still count as visible — found because
    // the discrimination break below then broke nothing.
    const visible = () => tiles.filter((tile) => {
        const b = tile.getBoundingClientRect();
        return b.top >= box.top - 1 && b.bottom <= box.bottom + 1
            && b.left >= box.left - 1 && b.right <= box.right + 1;
    }).length;
    const overflows = rail.scrollHeight > rail.clientHeight + 1;
    const problems = [];
    let lastReachable = false;
    let allVisible = false;
    if (overflows) {
        const before = rail.scrollTop;
        rail.scrollTop = rail.scrollHeight;
        await new Promise((r) => requestAnimationFrame(() => r()));
        const last = tiles[tiles.length - 1].getBoundingClientRect();
        lastReachable = last.top >= box.top - 1 && last.bottom <= box.bottom + 1;
        rail.scrollTop = before;
        await new Promise((r) => requestAnimationFrame(() => r()));
        if (!lastReachable) {
            problems.push('the rail overflows and the last app is NOT reachable '
                + 'by scrolling it — apps are being truncated');
        }
    } else {
        allVisible = visible() === tiles.length;
        if (!allVisible) {
            problems.push('the rail does not overflow, so every one of its '
                + tiles.length + ' apps should be visible without scrolling, '
                + 'but only ' + visible() + ' are');
        }
    }
    return { overflows, lastReachable, allVisible, problems };
}
"""

RAIL_RENDERS_JS = RAIL_REPORT_JS + SAPIAN_FORCED_HEIGHT + """
(async () => {
    const frames = async (n) => {
        for (let i = 0; i < n; i++) {
            await new Promise((r) => requestAnimationFrame(() => r()));
        }
    };
    const rail = document.querySelector('.o_sapian_rail');

    // SETTLE FIRST, EXPLICITLY. This test was protected only by accident: the
    // image-decode poll inside sapianRailReport() takes long enough that the
    // client has usually settled by the time the scroll below happens. That is
    // protection that disappears the moment the icons are already decoded, and
    // it is not something a reader could know was load-bearing. Waiting on the
    // signal itself makes it a decision instead of a side effect.
    if (rail) {
        const env = odoo.__WOWL_DEBUG__.root.env;
        const deadline = Date.now() + 20000;
        while (Date.now() < deadline && !env.services.action.currentController) {
            await frames(5);
        }
        await frames(60);
    }

    const report = await sapianRailReport();

    // THE SCROLL ASSERTION WAS VACUOUS, and that is worse than flaky.
    //
    // Measured on the database this test runs against in CI: apps=14 tiles=14
    // visibleWithoutScrolling=14. Every tile fits. `scrollTop = scrollHeight`
    // is therefore a no-op and `lastReachableByScrolling=true` was produced by
    // there being nothing to scroll — a success signal produced by doing
    // nothing, in a file whose own docstring cites that rule. It could not
    // flake, and for exactly the same reason it could not catch truncation.
    //
    // So BOTH branches assert, and neither is a skip:
    //
    //   overflows      -> the last app must be reachable by scrolling
    //   does not       -> EVERY app must be visible without scrolling, which
    //                     is the stronger claim when it holds
    //
    // and the marker says which branch ran, so "it did not overflow" stops
    // being invisible. On a 36-app database — the shape we actually ship — it
    // is the first branch: visibleWithoutScrolling=19 of 36.
    const reach = await sapianRailReach();
    const overflows = reach.overflows;
    const lastReachable = reach.lastReachable;
    const allVisible = reach.allVisible;

    // One line of positive evidence in the server log. A run that skipped, or
    // never reached the browser, cannot print this.
    console.log('SAPIAN-RAIL viewport=' + window.innerWidth + 'x'
        + window.innerHeight
        + ' apps=' + report.apps + ' tiles=' + report.tiles
        + ' loaded=' + report.loaded
        + ' visibleWithoutScrolling=' + report.visible
        + ' overflows=' + overflows
        + ' lastReachableByScrolling=' + lastReachable
        + ' allVisibleWithoutScrolling=' + allVisible);

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
    if (reach.problems.length) {
        throw new Error('rail reach: ' + reach.problems.join(' | '));
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

RAIL_DISCRIMINATES_JS = RAIL_REPORT_JS + SAPIAN_FORCED_HEIGHT + """
(async () => {
    // Prove the check goes red for each thing it claims to check, by breaking
    // that thing on purpose. An untested guard is one more thing that passes
    // by doing nothing.
    //
    // Settles first for the same reason its sibling does: sapianRailReport()
    // compares the tile count against /web/webclient/load_menus, and the rail
    // re-renders while the default action is still resolving. Breaking a tile
    // during that window measures a moving target.
    {
        const env = odoo.__WOWL_DEBUG__.root.env;
        const deadline = Date.now() + 20000;
        while (Date.now() < deadline && !env.services.action.currentController) {
            await new Promise((r) => setTimeout(r, 100));
        }
        await new Promise((r) => setTimeout(r, 600));
    }
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

    // 4. THE OVERFLOW BRANCH. Force the rail short so it overflows, then make
    //    the last tile TALLER THAN THE BOX, so that even scrolled to the very
    //    bottom it cannot fit inside — which is what "you can never see this
    //    app" actually looks like.
    //
    //    `overflow-y: hidden` was tried first and does not work: Chrome still
    //    honours a programmatic `scrollTop`, so the tail stayed reachable and
    //    the break broke nothing. Geometry is deterministic where event
    //    behaviour is not.
    const railTiles = [...rail.querySelectorAll('.o_sapian_rail_app')];
    const tileH = railTiles[0].getBoundingClientRect().height;
    const tail = railTiles[railTiles.length - 1];
    rail.style.height = sapianForcedHeight(rail, tileH, railTiles.length) + 'px';
    await new Promise((r) => requestAnimationFrame(() => r()));
    tail.style.height = (rail.clientHeight + 50) + 'px';
    await new Promise((r) => requestAnimationFrame(() => r()));
    const undoOverflow = () => { rail.style.height = ''; tail.style.height = ''; };
    let reach = await sapianRailReach();
    if (!reach.overflows) {
        undoOverflow();
        throw new Error('DISCRIMINATION FAILED: could not force the rail to '
            + 'overflow, so the branch below was never exercised');
    }
    if (!reach.problems.length) {
        undoOverflow();
        throw new Error('DISCRIMINATION FAILED: the reach check passed with an '
            + 'overflowing rail whose last app cannot be scrolled into view');
    }
    console.log('SAPIAN-RAIL-DISCRIMINATION unreachable-tail -> ' + reach.problems[0]);
    undoOverflow();
    await new Promise((r) => requestAnimationFrame(() => r()));

    // 5. THE NO-OVERFLOW BRANCH, forced the same way rather than left to
    //    whichever database this runs on. Make the rail taller than its
    //    content so nothing overflows, then push one tile outside the box.
    //    "It all fits" must stop being true.
    //
    //    Forced, because CI is moving to a 36-app database where the rail
    //    overflows naturally — and a proof that quietly stops running on the
    //    configuration we ship is the shape this whole file is about.
    rail.style.height = (rail.scrollHeight + 200) + 'px';
    await new Promise((r) => requestAnimationFrame(() => r()));
    let forced = await sapianRailReach();
    if (forced.overflows) {
        rail.style.height = '';
        throw new Error('DISCRIMINATION FAILED: could not force the rail to '
            + 'STOP overflowing, so the no-overflow branch was never exercised');
    }
    // Sideways, not downwards. `top: 4000px` extends the rail's scrollable
    // overflow, which flipped it back into the OVERFLOW branch — where
    // scrolling to the bottom found the tile perfectly reachable and the break
    // broke nothing. `overflow-x` is hidden on the rail, so a horizontal
    // offset moves the tile out of the panel without changing scrollHeight.
    tail.style.position = 'relative';
    tail.style.left = '-4000px';
    await new Promise((r) => requestAnimationFrame(() => r()));
    forced = await sapianRailReach();
    const undoFit = () => {
        rail.style.height = ''; tail.style.position = ''; tail.style.left = '';
    };
    if (!forced.problems.length) {
        undoFit();
        throw new Error('DISCRIMINATION FAILED: the reach check passed with a '
            + 'tile pushed outside a rail that does not overflow');
    }
    console.log('SAPIAN-RAIL-DISCRIMINATION tile-outside-box -> ' + forced.problems[0]);
    undoFit();
    await new Promise((r) => requestAnimationFrame(() => r()));

    // 6. and it recovers — a check that reports a problem unconditionally
    //    would have passed 1-5 while being useless.
    reach = await sapianRailReach();
    if (reach.problems.length) {
        throw new Error('the reach check does not recover: '
            + reach.problems.join(' | '));
    }
    report = await sapianRailReport();
    if (report.problems.length) {
        throw new Error('the check does not recover once the DOM is restored: '
            + report.problems.join(' | '));
    }
    console.log('SAPIAN-RAIL-DISCRIMINATION restored -> clean');
    console.log('test successful');
})();
"""

RAIL_OVERFLOWS_JS = RAIL_REPORT_JS + SAPIAN_FORCED_HEIGHT + """
(async () => {
    const frames = async (n) => {
        for (let i = 0; i < n; i++) {
            await new Promise((r) => requestAnimationFrame(() => r()));
        }
    };
    const rail = document.querySelector('.o_sapian_rail');
    const tiles = [...rail.querySelectorAll('.o_sapian_rail_app')];
    if (tiles.length < 2) {
        throw new Error('need at least two apps to test scrolling; found '
            + tiles.length);
    }

    // WAIT FOR THE CLIENT TO SETTLE FIRST — the same wait, on the same signal,
    // that TestSapianAppRailKeepsScroll below already does.
    //
    // THIS TEST WAS PASSING BY LUCK. The ready condition is satisfied as soon
    // as one tile exists, which is before the default action has resolved.
    // Until it does the current app keeps changing, and pulling the newly
    // current app into view is the rail doing its job — but it lands inside
    // the window where this test has already scrolled to the bottom and is
    // about to measure. Nothing about the assertion was wrong; it was
    // measuring a system mid-boot and calling the result a property of the
    // system.
    //
    // Measured on identical code. BEFORE this wait: 4 runs, 3 red. AFTER it:
    // 10 consecutive runs, 0 red. The two sample sizes differ because the
    // before-figure is what was observed when the flake was found, not a
    // matched experiment — said plainly rather than rounded into a tidier
    // pair. The geometry was byte for byte the same in every run, red and
    // green alike (forcedRailHeight=572 contentHeight=666 tiles=14
    // visibleWithoutScrolling=12); only lastReachableByScrolling flipped. The
    // rail was never truncating.
    //
    // A sleep would have been the wrong fix even if it worked: it would make
    // the test pass on a slow runner by accident rather than because the thing
    // it waits for has happened.
    const env = odoo.__WOWL_DEBUG__.root.env;
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline && !env.services.action.currentController) {
        await frames(5);
    }
    await frames(60);

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
    const forced = sapianForcedHeight(rail, tileHeight, tiles.length);
    rail.style.height = forced + 'px';
    await frames(1);

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

RAIL_KEEPS_SCROLL_JS = SAPIAN_FORCED_HEIGHT + """
(async () => {
    const frames = async (n) => {
        for (let i = 0; i < n; i++) {
            await new Promise((r) => requestAnimationFrame(() => r()));
        }
    };
    const rail = document.querySelector('.o_sapian_rail');
    const tiles = [...rail.querySelectorAll('.o_sapian_rail_app')];
    if (tiles.length < 2) {
        throw new Error('need at least two apps; found ' + tiles.length);
    }

    // WAIT FOR THE CLIENT TO SETTLE FIRST.
    // The ready condition is satisfied as soon as one tile exists, which is
    // before the default action has resolved. Until it does, the current app
    // changes — and scrolling the newly current app into view is the rail
    // doing its job, not the defect under test. Measuring through that window
    // is what made the first version of this test fail on correct code.
    const env = odoo.__WOWL_DEBUG__.root.env;
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline && !env.services.action.currentController) {
        await frames(5);
    }
    await frames(60);

    // Force the overflow rather than wait for a crowded database, exactly as
    // the overflow test does, so this holds on a two-app CI install and on a
    // 36-app tenant alike.
    const tileHeight = tiles[0].getBoundingClientRect().height;
    rail.style.height = sapianForcedHeight(rail, tileHeight, tiles.length) + 'px';
    await frames(2);
    const restore = () => { rail.style.height = ''; rail.scrollTop = 0; };
    if (rail.scrollHeight <= rail.clientHeight) {
        restore();
        throw new Error('could not force the rail to overflow, so this test '
            + 'proves nothing about keeping a scroll position');
    }

    const maxScroll = rail.scrollHeight - rail.clientHeight;
    rail.scrollTop = rail.scrollHeight;
    await frames(10);
    const before = rail.scrollTop;
    if (before !== maxScroll) {
        restore();
        throw new Error('could not park the rail at the bottom: asked for '
            + maxScroll + ', settled at ' + before + '. Something is still '
            + 'moving the rail, so the comparison below would be meaningless.');
    }

    // A re-render that has NOTHING to do with which app you are in: an action
    // finishing, the app list reloading. This happens continuously in use, and
    // the current app is unchanged across it.
    env.bus.trigger('ACTION_MANAGER:UI-UPDATED', 'current');
    env.bus.trigger('MENUS:APP-CHANGED');
    await frames(40);
    const after = rail.scrollTop;

    const last = tiles[tiles.length - 1].getBoundingClientRect();
    const box = rail.getBoundingClientRect();
    const lastStillReachable = last.top >= box.top - 1 && last.bottom <= box.bottom + 1;

    console.log('SAPIAN-RAIL-SCROLLKEEP tiles=' + tiles.length
        + ' maxScroll=' + maxScroll
        + ' scrollBefore=' + before + ' scrollAfter=' + after
        + ' lastStillReachable=' + lastStillReachable);

    restore();
    await frames(2);

    if (after !== before) {
        throw new Error('a re-render moved the rail from scrollTop ' + before
            + ' to ' + after + ' - the scroll position is thrown away by '
            + 'renders that have nothing to do with the rail. On a 36-app '
            + 'tenant that sends the user back to the top of the list.');
    }
    if (!lastStillReachable) {
        throw new Error('after a re-render the last app is no longer reachable');
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
class TestSapianAppRailKeepsScroll(RailBrowserCase):
    """A re-render must not throw away where the user scrolled to.

    `scrollCurrentIntoView` used to run on EVERY `onPatched`, and because the
    active tile is usually near the top of the rail that meant any unrelated
    re-render silently scrolled the rail back to the top. Measured on a 36-app
    database before the fix: scrolled to the bottom (scrollTop 828 of 828), one
    re-render, scrollTop 0 - the last twelve apps gone from view without anyone
    touching the rail. At 40 apps, 1020 -> 0.

    It also made TestSapianAppRailOverflow FLAKY rather than merely strict:
    that test sets scrollTop and measures a frame later, so a re-render landing
    in that window made the last tile unreachable and the rail look truncated.
    Three green CI runs and one red on identical code, with identical geometry
    (forcedRailHeight=624 contentHeight=672 tiles=14) - the only differing
    token was lastReachableByScrolling. That test was telling the truth about a
    real defect; it just named it "truncation".

    So the defect gets its own assertion, in its own words, instead of being
    left to surface as somebody else's intermittent red.
    """

    browser_size = "1366x900"

    def test_a_rerender_does_not_lose_the_scroll_position(self):
        self.browser_js(
            "/odoo",
            RAIL_KEEPS_SCROLL_JS,
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


# ---------------------------------------------------------------------------
# THE LABELLED SIDEBAR — docs/SPEC-navigation-chrome.md section 1.
#
# Same shape as the rail checks above: ONE report function returning problems,
# used by the assertion and by the discrimination proof, so the guard is
# exercised against a deliberately broken DOM rather than trusted.
#
# The numbers here ARE hardcoded, unlike the tile count. They are not an
# incidental property of the database — they are the specification, and a
# sidebar that quietly became 180px wide with 40px rows would have stopped
# being the thing that was designed. The brand is read from the palette file at
# test time so a re-brand moves the expectation with the product.
# ---------------------------------------------------------------------------
SIDEBAR_REPORT_JS = """
function sapianSidebarReport() {
    const problems = [];
    const rail = document.querySelector('.o_sapian_rail');
    if (!rail) {
        problems.push('no .o_sapian_rail element in the DOM');
        return { problems };
    }
    const rows = [...rail.querySelectorAll('.o_sapian_rail_app')];
    const active = rail.querySelector('.o_sapian_rail_app_active');
    const inactive = rows.find((r) => !r.classList.contains('o_sapian_rail_app_active'));
    if (!active) {
        problems.push('no active row — the state this section exists for is unreachable');
        return { problems };
    }
    if (!inactive) {
        problems.push('every row is active, so there is nothing to compare against');
        return { problems };
    }

    const skin = (el) => {
        const s = getComputedStyle(el);
        return { bg: s.backgroundColor, color: s.color };
    };
    const activeSkin = skin(active);
    const inactiveSkin = skin(inactive);

    // THE POINT OF THE SECTION. The competitor's active and inactive links have
    // byte-identical computed styles; there is no way to tell which app you are
    // in from their sidebar. Compared from getComputedStyle, never from the
    // class list — the class list is exactly what THEY also have.
    if (activeSkin.bg === inactiveSkin.bg && activeSkin.color === inactiveSkin.color) {
        problems.push('active and inactive rows are styled identically ('
            + activeSkin.bg + ' / ' + activeSkin.color + ')');
    }
    if (activeSkin.bg !== '%BRAND%') {
        problems.push('the active row is filled ' + activeSkin.bg
            + ', not the brand %BRAND%');
    }
    if (activeSkin.color !== 'rgb(255, 255, 255)') {
        problems.push('the active row label is ' + activeSkin.color + ', not white');
    }

    // EVERY row, not a representative one. A single mis-sized row is a real
    // defect, and a guard that samples rows[0] cannot be broken on purpose
    // anywhere else — which is how the discrimination proof caught this check
    // being weaker than it looked.
    let rowHeight = 0;
    rows.forEach((row) => {
        const h = Math.round(row.getBoundingClientRect().height);
        rowHeight = rowHeight || h;
        if (h !== 44) {
            problems.push('row "' + (row.getAttribute('aria-label') || '?')
                + '" is ' + h + 'px tall, not 44px');
        }
        const label = row.querySelector('.o_sapian_rail_label');
        if (!label) {
            problems.push('row "' + (row.getAttribute('aria-label') || '?')
                + '" has no label element');
            return;
        }
        const ls = getComputedStyle(label);
        if (ls.fontSize !== '13px') {
            problems.push('label font-size is ' + ls.fontSize + ', not 13px');
        }
        if (ls.fontWeight !== '600') {
            problems.push('label font-weight is ' + ls.fontWeight + ', not 600');
        }
    });

    const collapsed = rail.classList.contains('o_sapian_rail_collapsed');
    const width = Math.round(rail.getBoundingClientRect().width);
    const expected = collapsed ? 56 : 200;
    if (width !== expected) {
        problems.push('the sidebar is ' + width + 'px wide '
            + (collapsed ? 'collapsed' : 'expanded') + ', not ' + expected + 'px');
    }

    // It must reserve its own space rather than sit on the content.
    const body = document.querySelector('.o_web_client');
    const padding = Math.round(parseFloat(getComputedStyle(body).paddingLeft) || 0);
    if (padding !== width) {
        problems.push('the web client is padded ' + padding + 'px for a '
            + width + 'px sidebar');
    }

    if (!rail.querySelector('.o_sapian_rail_toggle')) {
        problems.push('no collapse toggle — the competitor has no collapse '
            + 'control either, and that is one of the things we are fixing');
    }

    // AND IT MUST NOT SIT UNDER THE FIXED FOOTER. Flagged during the
    // web_responsive evaluation: the sidebar is top:0/bottom:0 and the footer
    // takes the bottom 28px, so without a clearance the last row is reachable
    // by scrolling and unreadable once you get there.
    const footer = document.querySelector('.o_sapian_footer');
    if (footer) {
        const fb = footer.getBoundingClientRect();
        const rb = rail.getBoundingClientRect();
        if (rb.bottom > fb.top + 0.5) {
            problems.push('the sidebar runs to ' + Math.round(rb.bottom)
                + 'px, under a footer that starts at ' + Math.round(fb.top) + 'px');
        }
    }

    return { problems, width, rowHeight, collapsed,
             activeBg: activeSkin.bg, activeColor: activeSkin.color,
             inactiveBg: inactiveSkin.bg, inactiveColor: inactiveSkin.color,
             rows: rows.length, padding };
}
"""


# The settle wait, once, for every sidebar block below.
#
# Same signal the rail's overflow and keep-scroll tests wait on, and for the
# same reason: `browser_js`'s ready condition is satisfied as soon as one row
# exists, which is before the default action has resolved. Measuring through
# that window is measuring a system mid-boot and calling the result a property
# of the system — which is exactly how TestSapianAppRailOverflow came to be
# passing by luck (3 of 10 runs red on identical code).
#
# A `setTimeout` would be a sleep, not a wait: it would pass on a slow runner
# by accident rather than because the thing it waits for has happened.
SIDEBAR_SETTLE_JS = """
const settle = (ms) => new Promise((r) => setTimeout(r, ms || 400));
async function sapianSidebarSettle() {
    const env = odoo.__WOWL_DEBUG__.root.env;
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline && !env.services.action.currentController) {
        await settle(100);
    }
    // Land in a real app so there IS an active row, then wait for the menu
    // service to agree — the class is what every assertion below keys off.
    const rows = [...document.querySelectorAll('.o_sapian_rail_app')];
    if (!document.querySelector('.o_sapian_rail_app_active')) {
        rows[Math.min(2, rows.length - 1)].click();
    }
    const second = Date.now() + 20000;
    while (Date.now() < second && !document.querySelector('.o_sapian_rail_app_active')) {
        await settle(100);
    }
    if (!document.querySelector('.o_sapian_rail_app_active')) {
        throw new Error('no row became active within 20s, so nothing below is '
            + 'measuring a settled client');
    }
    await settle(600);
}
"""

SIDEBAR_STATES_JS = SIDEBAR_REPORT_JS + SIDEBAR_SETTLE_JS + """
(async () => {
    await sapianSidebarSettle();

    const report = sapianSidebarReport();
    console.log('SAPIAN-SIDEBAR width=' + report.width
        + ' rows=' + report.rows + ' rowHeight=' + report.rowHeight
        + ' padding=' + report.padding
        + ' activeBg="' + report.activeBg + '" activeColor="' + report.activeColor + '"'
        + ' inactiveBg="' + report.inactiveBg + '"'
        + ' distinct=' + (report.activeBg !== report.inactiveBg));

    if (report.problems.length) {
        throw new Error('sidebar: ' + report.problems.join(' | '));
    }
    console.log('test successful');
})();
"""

SIDEBAR_DISCRIMINATES_JS = SIDEBAR_REPORT_JS + SIDEBAR_SETTLE_JS + """
(async () => {
    await sapianSidebarSettle();

    const rail = document.querySelector('.o_sapian_rail');
    const active = rail.querySelector('.o_sapian_rail_app_active');
    const inactive = [...rail.querySelectorAll('.o_sapian_rail_app')]
        .find((r) => !r.classList.contains('o_sapian_rail_app_active'));

    const breaks = [
        ['identical-states', () => {
            // EXACTLY the competitor's sidebar: the class is there, the
            // styling is not.
            active.style.backgroundColor = getComputedStyle(inactive).backgroundColor;
            active.style.color = getComputedStyle(inactive).color;
            active.querySelector('.o_sapian_rail_label').style.color =
                getComputedStyle(inactive).color;
        }],
        ['wrong-row-height', () => { active.style.height = '60px'; }],
        ['wrong-label-size', () => {
            active.querySelector('.o_sapian_rail_label').style.fontSize = '11px';
        }],
        ['no-toggle', () => { rail.querySelector('.o_sapian_rail_toggle').remove(); }],
        ['under-the-footer', () => { rail.style.bottom = '0px'; }],
        ['narrow-sidebar', () => { rail.style.width = '180px'; }],
    ];

    for (const [name, breakIt] of breaks) {
        const before = rail.getAttribute('style') || '';
        const activeBefore = active.getAttribute('style') || '';
        const labelBefore =
            active.querySelector('.o_sapian_rail_label').getAttribute('style') || '';
        const toggle = rail.querySelector('.o_sapian_rail_toggle');
        const toggleAnchor = toggle ? toggle.nextSibling : null;

        breakIt();
        await settle(200);
        const report = sapianSidebarReport();
        if (!report.problems.length) {
            throw new Error('DISCRIMINATION FAILED: the sidebar check passed '
                + 'with ' + name);
        }
        console.log('SAPIAN-SIDEBAR-DISCRIMINATION ' + name + ' -> '
            + report.problems[0]);

        // Put it back.
        rail.setAttribute('style', before);
        active.setAttribute('style', activeBefore);
        active.querySelector('.o_sapian_rail_label').setAttribute('style', labelBefore);
        if (toggle && !rail.contains(toggle)) {
            rail.insertBefore(toggle, toggleAnchor);
        }
        await settle(200);
    }

    // And it recovers. A check that complained unconditionally would have
    // passed every case above while proving nothing.
    const clean = sapianSidebarReport();
    if (clean.problems.length) {
        throw new Error('the sidebar check does not recover once the DOM is '
            + 'restored: ' + clean.problems.join(' | '));
    }
    console.log('SAPIAN-SIDEBAR-DISCRIMINATION restored -> clean');
    console.log('test successful');
})();
"""

SIDEBAR_COLLAPSE_JS = SIDEBAR_REPORT_JS + SIDEBAR_SETTLE_JS + """
(async () => {
    await sapianSidebarSettle();
    const rail = document.querySelector('.o_sapian_rail');
    const toggle = rail.querySelector('.o_sapian_rail_toggle');
    const rows = [...rail.querySelectorAll('.o_sapian_rail_app')];

    const width = () => Math.round(rail.getBoundingClientRect().width);
    const labelsShown = () => [...rail.querySelectorAll('.o_sapian_rail_label')]
        .filter((l) => getComputedStyle(l).display !== 'none').length;
    const tiles = () => rail.querySelectorAll('.o_sapian_rail_app').length;

    const wide = width();
    const labelsWide = labelsShown();
    const tilesWide = tiles();

    // FORCE OVERFLOW, then scroll to the bottom. Collapsing is a re-render for
    // a reason that has nothing to do with which app you are in, and the whole
    // point of scrollCurrentIntoView's guard is that such a re-render must not
    // throw the user's position away. Measured here as well as in
    // TestSapianAppRailKeepsScroll, because the toggle is a NEW way to trigger
    // exactly the re-render that used to lose it.
    const rowHeight = rows[0].getBoundingClientRect().height;
    rail.style.height = Math.max(120, Math.floor(rowHeight * (rows.length / 2))) + 'px';
    await settle(200);
    if (rail.scrollHeight <= rail.clientHeight) {
        rail.style.height = '';
        throw new Error('could not force the sidebar to overflow, so the '
            + 'scroll assertion below would prove nothing');
    }
    rail.scrollTop = rail.scrollHeight;
    await settle(200);
    const scrollBefore = rail.scrollTop;
    if (!scrollBefore) {
        rail.style.height = '';
        throw new Error('scrollTop stayed 0 after scrolling to the bottom');
    }

    toggle.click();
    await settle(700);
    const narrow = width();
    const scrollAfterCollapse = rail.scrollTop;
    const labelsNarrow = labelsShown();
    const tilesNarrow = tiles();
    const collapsedReport = sapianSidebarReport();

    toggle.click();
    await settle(700);
    const wideAgain = width();
    const scrollAfterExpand = rail.scrollTop;
    rail.style.height = '';
    await settle(200);

    console.log('SAPIAN-SIDEBAR-COLLAPSE wide=' + wide + ' narrow=' + narrow
        + ' wideAgain=' + wideAgain
        + ' labels=' + labelsWide + '/' + labelsNarrow
        + ' tiles=' + tilesWide + '/' + tilesNarrow
        + ' scroll=' + scrollBefore + '/' + scrollAfterCollapse + '/'
        + scrollAfterExpand);

    if (narrow >= wide) {
        throw new Error('collapsing did not narrow the sidebar: ' + wide
            + ' -> ' + narrow);
    }
    if (wideAgain !== wide) {
        throw new Error('expanding did not restore the width: ' + wide
            + ' -> ' + narrow + ' -> ' + wideAgain);
    }
    if (labelsNarrow !== 0) {
        throw new Error(labelsNarrow + ' labels are still displayed when collapsed');
    }
    if (!labelsWide) {
        throw new Error('no labels are displayed when expanded, so the '
            + 'collapsed assertion above proves nothing');
    }
    if (tilesNarrow !== tilesWide) {
        throw new Error('collapsing changed the app count from ' + tilesWide
            + ' to ' + tilesNarrow + ' — labels must be hidden, not removed');
    }
    if (scrollAfterCollapse !== scrollBefore || scrollAfterExpand !== scrollBefore) {
        throw new Error('toggling the sidebar threw away the scroll position: '
            + scrollBefore + ' -> ' + scrollAfterCollapse + ' -> '
            + scrollAfterExpand);
    }
    if (collapsedReport.problems.length) {
        throw new Error('collapsed sidebar: ' + collapsedReport.problems.join(' | '));
    }
    console.log('test successful');
})();
"""

SIDEBAR_KEYBOARD_JS = SIDEBAR_SETTLE_JS + """
(async () => {
    await sapianSidebarSettle();
    const rail = document.querySelector('.o_sapian_rail');
    const toggle = rail.querySelector('.o_sapian_rail_toggle');
    const first = rail.querySelector('.o_sapian_rail_app');

    // FOCUSABLE AT ALL. tabIndex -1 with no href would be reachable by script
    // and not by a keyboard, which is the failure this catches.
    first.focus();
    if (document.activeElement !== first) {
        throw new Error('a sidebar row cannot take focus at all');
    }
    // `:focus-visible` only matches for keyboard-ish focus, so ask for it by
    // name rather than hoping .focus() produced it.
    const ring = first.matches(':focus-visible')
        ? getComputedStyle(first)
        : null;
    const outlineWidth = ring ? ring.outlineWidth : '0px';
    const outlineStyle = ring ? ring.outlineStyle : 'none';

    toggle.focus();
    if (document.activeElement !== toggle) {
        throw new Error('the collapse toggle cannot take focus');
    }
    const wide = Math.round(rail.getBoundingClientRect().width);
    // A real <button> answers Enter without any key handling of our own. A div
    // with a click handler would not, and that is the point of the assertion.
    toggle.dispatchEvent(new KeyboardEvent('keydown',
        { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
    toggle.click();   // what the browser does for us on Enter over a button
    await settle(700);
    const narrow = Math.round(rail.getBoundingClientRect().width);
    toggle.click();
    await settle(700);

    console.log('SAPIAN-SIDEBAR-KEYBOARD rowFocusable=true'
        + ' focusVisible=' + !!ring
        + ' outline="' + outlineWidth + ' ' + outlineStyle + '"'
        + ' toggleWidth=' + wide + '->' + narrow
        + ' tag=' + toggle.tagName);

    if (toggle.tagName !== 'BUTTON') {
        throw new Error('the collapse control is a <' + toggle.tagName
            + '>, so it is not keyboard-operable without handlers of our own');
    }
    if (!ring) {
        throw new Error('a focused sidebar row does not match :focus-visible, '
            + 'so a keyboard user gets no ring');
    }
    if (outlineStyle === 'none' || parseFloat(outlineWidth) < 1) {
        throw new Error('the focus ring is invisible: outline ' + outlineWidth
            + ' ' + outlineStyle);
    }
    if (narrow >= wide) {
        throw new Error('the toggle did not act on activation: ' + wide
            + ' -> ' + narrow);
    }
    console.log('test successful');
})();
"""


# The sidebar header is the product's mark, and it has to behave like one in a
# running client, not just in the template source.
# TestTheMarkIsTheCommittedLogo (test_vendor_identity.py) already proves the
# four paths in app_rail.xml are byte-identical to brand/Sapian Logo.svg. What
# it cannot prove is that they SURVIVE to the screen: an SVG can be in the DOM
# and be 0×0, or be painted in the browser's default black because `color` did
# not reach it, and the template test would still be green.
#
# `aria-expanded` is asserted as the literal strings because the boolean form
# was wrong on the wire. Measured on a running client with
# `t-att-aria-expanded="!state.collapsed"`:
#
#     expanded  -> aria-expanded=""     (OWL stringifies true to '')
#     collapsed -> attribute absent     (OWL drops the attribute on false)
#
# An empty value is not a valid ARIA state, and an absent one announces "this
# control expands nothing" — the opposite of the truth in the state where it
# matters most. Nothing in the DOM said so; only reading the served attribute
# did.
SIDEBAR_HEADER_JS = SIDEBAR_SETTLE_JS + """
(async () => {
    await sapianSidebarSettle();
    const rail = document.querySelector('.o_sapian_rail');
    const head = rail.querySelector('.o_sapian_rail_toggle');
    if (!head) { throw new Error('the sidebar has no header/toggle at all'); }

    const readHeader = () => {
        const svg = head.querySelector('svg.o_sapian_rail_brand');
        const box = svg ? svg.getBoundingClientRect() : null;
        const word = head.querySelector('.o_sapian_rail_label');
        const chev = head.querySelector('.o_sapian_rail_chevron');
        return {
            paths: svg ? svg.querySelectorAll('path').length : 0,
            markW: box ? Math.round(box.width) : 0,
            markH: box ? Math.round(box.height) : 0,
            markFill: svg ? getComputedStyle(svg).fill : 'none',
            markDisplay: svg ? getComputedStyle(svg).display : 'none',
            word: word ? word.textContent.trim() : null,
            wordShown: word ? getComputedStyle(word).display !== 'none' : false,
            chevShown: chev ? getComputedStyle(chev).display !== 'none' : false,
            // getAttribute, NOT the property: the property would coerce and
            // hide exactly the defect this test exists for.
            expanded: head.getAttribute('aria-expanded'),
            tooltip: head.getAttribute('data-tooltip'),
        };
    };

    const open = readHeader();
    head.click();
    await settle(700);
    const shut = readHeader();
    head.click();
    await settle(700);

    console.log('SAPIAN-SIDEBAR-HEADER paths=' + open.paths
        + ' mark=' + open.markW + 'x' + open.markH
        + ' fill="' + open.markFill + '"'
        + ' word="' + open.word + '"'
        + ' expandedOpen="' + open.expanded + '" expandedShut="' + shut.expanded + '"'
        + ' wordShown=' + open.wordShown + '->' + shut.wordShown
        + ' chevShown=' + open.chevShown + '->' + shut.chevShown
        + ' markShut=' + shut.markW + 'x' + shut.markH);

    // THE MARK. Four paths, painted, and big enough to be a logo rather than a
    // collapsed 0x0 box.
    if (open.paths !== 4) {
        throw new Error('the header carries ' + open.paths + ' logo paths, not 4 — '
            + 'the mark is not the committed logo');
    }
    if (open.markW < 12 || open.markH < 12) {
        throw new Error('the mark is in the DOM but renders at ' + open.markW
            + 'x' + open.markH + ', so nobody sees it');
    }
    if (open.markFill === 'rgb(0, 0, 0)' || open.markFill === 'none') {
        throw new Error('the mark paints "' + open.markFill + '" — currentColor '
            + 'did not reach it, so it is not in the brand');
    }
    if (open.word !== 'SapianERP') {
        throw new Error('the header wordmark reads "' + open.word + '"');
    }

    // THE ARIA STATE. Literal strings in BOTH states.
    if (open.expanded !== 'true' || shut.expanded !== 'false') {
        throw new Error('aria-expanded is "' + open.expanded + '" expanded and "'
            + shut.expanded + '" collapsed; it must be the strings true/false');
    }

    // COLLAPSED: the mark stays, the wordmark and chevron go, and the tooltip
    // takes over saying what the control does.
    if (shut.markW < 12 || shut.markH < 12) {
        throw new Error('the mark disappears when collapsed (' + shut.markW
            + 'x' + shut.markH + '), leaving 56px of nothing');
    }
    if (!open.wordShown || shut.wordShown) {
        throw new Error('the wordmark is shown=' + open.wordShown + ' expanded and '
            + shut.wordShown + ' collapsed');
    }
    if (!open.chevShown || shut.chevShown) {
        throw new Error('the chevron is shown=' + open.chevShown + ' expanded and '
            + shut.chevShown + ' collapsed');
    }
    if (!shut.tooltip || !/expand/i.test(shut.tooltip)) {
        throw new Error('collapsed, the header offers no tooltip saying it expands: "'
            + shut.tooltip + '"');
    }
    console.log('test successful');
})();
"""


# THE HEADER OCCLUDES WHAT SCROLLS UNDER IT — the assertion nothing had.
#
# Every sidebar test in this file measured row geometry and computed styles,
# and every one passed while the header was 92% transparent on hover and the
# rows behind it were legible through it. Geometry cannot see through a box.
#
# ONE OF THE TWO CHECKS BELOW WOULD NOT HAVE CAUGHT IT, and that is worth
# stating rather than discovering later. `elementFromPoint` at the header's
# centre returns the header on the BROKEN code too: the stacking was always
# right — label -> button(z=1) -> nav(z=1020) -> body — and only the paint was
# wrong. Hit-testing does not care about alpha. It is kept because the stacking
# half is a real property that must not regress, but the check that
# discriminates is the OPACITY one.
#
# Opacity is read as the effective background: `background-color` must be fully
# opaque, and any `background-image` layered on top of it is fine (that is how
# the hover tint is now applied) but must not be the only thing there. Both are
# sampled at REST and while HOVERING, because the defect existed in exactly one
# of those states.
SIDEBAR_OCCLUSION_JS = SIDEBAR_SETTLE_JS + SAPIAN_FORCED_HEIGHT + """
function sapianAlphaOf(colour) {
    // 'rgba(20, 69, 79, 0.08)' -> 0.08 ; 'rgb(255, 255, 255)' -> 1
    const m = /^rgba?\\(([^)]+)\\)$/.exec((colour || '').trim());
    if (!m) { return colour === 'transparent' ? 0 : 1; }
    const parts = m[1].split(',').map((s) => parseFloat(s));
    return parts.length > 3 ? parts[3] : 1;
}

function sapianHeaderReport(label) {
    const rail = document.querySelector('.o_sapian_rail');
    const head = rail.querySelector('.o_sapian_rail_toggle');
    const problems = [];
    const cs = getComputedStyle(head);
    const hb = head.getBoundingClientRect();

    // WHAT IS PAINTED THERE. Five points, not one: a centre-only sample passes
    // on a header whose background is inset, or whose label is the only opaque
    // thing in the box.
    const points = [
        ['centre', hb.left + hb.width / 2, hb.top + hb.height / 2],
        ['left',   hb.left + 4,            hb.top + hb.height / 2],
        ['right',  hb.right - 4,           hb.top + hb.height / 2],
        ['upper',  hb.left + hb.width / 2, hb.top + 3],
        ['lower',  hb.left + hb.width / 2, hb.bottom - 3],
    ];
    const hits = [];
    for (const [name, x, y] of points) {
        const el = document.elementFromPoint(x, y);
        const row = el && el.closest && el.closest('.o_sapian_rail_app');
        const mine = el && (el === head || head.contains(el));
        hits.push(name + '=' + (mine ? 'header' : row ? 'ROW' : 'other'));
        if (row) {
            problems.push(label + ': a rail row ("'
                + (row.getAttribute('aria-label') || '?')
                + '") is on top at the header\\'s ' + name);
        } else if (!mine) {
            problems.push(label + ': something that is not the header is on top '
                + 'at its ' + name + ' (' + (el ? el.tagName : 'nothing') + ')');
        }
    }

    // AND IS IT SOLID. This is the half that goes red on the defect.
    const alpha = sapianAlphaOf(cs.backgroundColor);
    if (alpha < 1) {
        problems.push(label + ': the header background is ' + cs.backgroundColor
            + ' (alpha ' + alpha + ') — rows scrolling under it show through');
    }
    return {
        problems,
        alpha,
        bg: cs.backgroundColor,
        bgImage: cs.backgroundImage === 'none' ? 'none' : 'layered',
        hits: hits.join(' '),
    };
}

async function sapianCheckHeader(width) {
    const rail = document.querySelector('.o_sapian_rail');
    const head = rail.querySelector('.o_sapian_rail_toggle');

    // THE ROWS MUST ACTUALLY BE PASSING UNDER IT, or there is nothing to
    // occlude and this whole test is vacuous — the RAIL_RENDERS_JS lesson.
    //
    // The overflow is FORCED rather than waited for, exactly as
    // TestSapianAppRailOverflow and TestSapianAppRailKeepsScroll already do.
    // Measured: on the theme-alone database the rail holds two apps in an
    // 872px box, scrollTop stays 0, and the precondition above aborted the run
    // — correctly, but it left the assertion unrun in the one CI job that
    // installs nothing else. Forcing the height makes this hold at two apps
    // and at forty.
    const tiles = [...rail.querySelectorAll('.o_sapian_rail_app')];
    const forced = sapianForcedHeight(
        rail, tiles[0].getBoundingClientRect().height, tiles.length);
    rail.style.height = forced + 'px';
    await settle(200);
    rail.scrollTop = rail.scrollHeight;
    await settle(400);
    if (rail.scrollTop < 10) {
        rail.style.height = '';
        throw new Error(width + ': could not force the rail to overflow '
            + '(scrollTop=' + rail.scrollTop + ', scrollHeight='
            + rail.scrollHeight + ' vs clientHeight=' + rail.clientHeight
            + '), so nothing was underneath the header');
    }
    const hb = head.getBoundingClientRect();
    const under = [...rail.querySelectorAll('.o_sapian_rail_app')].filter((r) => {
        const b = r.getBoundingClientRect();
        return b.top < hb.bottom && b.bottom > hb.top;
    });
    if (!under.length) {
        rail.style.height = '';
        throw new Error(width + ': no row overlaps the header box after '
            + 'scrolling, so there is nothing for the header to occlude');
    }

    const rest = sapianHeaderReport(width + ' at rest');

    // HOVER. The defect lived here and nowhere else: the header shared its
    // hover fill with the rows, and that fill is 8% alpha.
    const evt = (type) => head.dispatchEvent(new MouseEvent(type,
        { bubbles: true, cancelable: true, view: window }));
    evt('mouseover'); evt('mouseenter'); evt('mousemove');
    await settle(300);
    // :hover cannot be forced from script in Chrome, so ask the stylesheet
    // what it WOULD paint rather than trusting a synthetic event.
    const hoverRule = [...document.styleSheets].flatMap((sheet) => {
        try { return [...sheet.cssRules]; } catch (e) { return []; }
    }).flatMap((rule) => rule.cssRules ? [...rule.cssRules] : [rule])
      .filter((rule) => rule.selectorText
          && /\\.o_sapian_rail_toggle:hover\\b/.test(rule.selectorText));
    const declared = hoverRule.map((r) => r.style.backgroundColor).filter(Boolean);
    const hoverBg = declared.length ? declared[declared.length - 1] : rest.bg;
    const hoverAlpha = sapianAlphaOf(hoverBg);
    // AND THE TINT MUST STILL BE THERE. Asserting only that the hover colour
    // is opaque is satisfied by deleting the tint altogether, which would
    // silently drop the hover affordance the SPEC asks for — a fix that passes
    // by removing the feature. The tint is now a background-image layered over
    // the opaque colour, so that is what to look for.
    const hoverImages = hoverRule.map((r) => r.style.backgroundImage)
        .filter((v) => v && v !== 'none');
    const hoverTint = hoverImages.length ? hoverImages[hoverImages.length - 1] : 'none';

    console.log('SAPIAN-SIDEBAR-OCCLUSION ' + width + ' rows=' + under.length
        + ' scrollTop=' + rail.scrollTop
        + ' restBg="' + rest.bg + '" restAlpha=' + rest.alpha
        + ' hoverBg="' + hoverBg + '" hoverAlpha=' + hoverAlpha
        + ' hoverTint=' + (hoverTint === 'none' ? 'MISSING' : 'present')
        + ' bgImage=' + rest.bgImage
        + ' ' + rest.hits);

    if (rest.problems.length) {
        throw new Error(rest.problems.join(' | '));
    }
    if (hoverAlpha < 1) {
        throw new Error(width + ': the header\\'s :hover rule paints ' + hoverBg
            + ' (alpha ' + hoverAlpha + '). It is position: sticky over a '
            + 'scrolling list, so a translucent hover state is a window onto '
            + 'the rows passing under it.');
    }
    if (hoverTint === 'none') {
        rail.style.height = '';
        throw new Error(width + ': the header has an opaque hover colour but no '
            + 'tint layered on it — the hover state was made opaque by removing '
            + 'it, not by compositing it, so the row no longer lights up.');
    }
    rail.style.height = '';
    rail.scrollTop = 0;
}

(async () => {
    await sapianSidebarSettle();
    const rail = document.querySelector('.o_sapian_rail');
    const toggle = rail.querySelector('.o_sapian_rail_toggle');

    // BOTH WIDTHS. The collapsed header is 56px of the same sticky box over the
    // same scrolling list, and a rule that fixed only the expanded one would
    // leave half the product broken with a green suite.
    await sapianCheckHeader('expanded');
    toggle.click();
    await settle(700);
    if (!rail.classList.contains('o_sapian_rail_collapsed')) {
        throw new Error('the rail did not collapse, so the collapsed half of '
            + 'this test measured the expanded rail twice');
    }
    await sapianCheckHeader('collapsed');
    toggle.click();
    await settle(700);
    console.log('test successful');
})();
"""

# And the launcher half: the rail stands down entirely while it is open.
#
# Keyed on the BODY CLASS rather than on web_responsive, and that is deliberate
# — the rule under test is a CSS rule keyed on exactly that class, so adding it
# by hand exercises the whole of our contract and the test runs on a database
# with no web_responsive at all. That the class is real is a separate question,
# asserted against the actual launcher by
# TestSapianRailStandsDownForTheRealLauncher, which runs in the CI job that
# installs web_responsive.
# THE CORNER MUST NOT BE A HOLE.
#
# Hiding the whole rail for the launcher (PR #43) hid the brand header with it,
# and left a 200x46 rectangle of PAGE BACKGROUND in the top-left corner —
# rgb(248, 249, 250) against the launcher's rgb(20, 69, 79). Measured from
# screenshot pixels: 9200 of 9200 pixels in that region were page background.
# With the mark restored it is 3 of 9200, and those three are antialiasing on
# the logo's edge.
#
# `browser_js` CANNOT SAMPLE PIXELS — there is no screenshot inside the page —
# so this asserts the three facts that together determine what is painted
# there, rather than the CSS rule that produces them:
#
#   1. the header's computed `visibility` is visible;
#   2. its background is OPAQUE, so it paints rather than letting the page
#      through (the same alpha check the occlusion guard uses);
#   3. its box COVERS the exposed corner — from the viewport origin to the
#      rail's width and the navbar's bottom, which is where the launcher's own
#      top edge is.
#
# An opaque, visible element covering the region is what paints the region.
# The pixel figures above are the evidence that these three produce the
# intended result, and they are recorded in the module README.
#
# `elementFromPoint` is deliberately NOT used to find the header: it is
# `pointer-events: none` on purpose, so hit-testing passes straight through it
# to the body. That is asserted too — the mark is identity, and identity is not
# a button.
SIDEBAR_CORNER_JS = SIDEBAR_SETTLE_JS + """
(async () => {
    await sapianSidebarSettle();
    const rail = document.querySelector('.o_sapian_rail');
    const head = rail.querySelector('.o_sapian_rail_toggle');
    const navbar = document.querySelector('.o_main_navbar');
    if (!navbar) { throw new Error('no navbar, so the corner has no known height'); }

    const alphaOf = (colour) => {
        const m = /^rgba?\(([^)]+)\)$/.exec((colour || '').trim());
        if (!m) { return colour === 'transparent' ? 0 : 1; }
        const parts = m[1].split(',').map((s) => parseFloat(s));
        return parts.length > 3 ? parts[3] : 1;
    };

    // The exposed corner: the launcher starts at the navbar's bottom edge, and
    // the web client is padded by the rail's width. That rectangle is what had
    // nothing painting it.
    const railWidth = Math.round(rail.getBoundingClientRect().width);
    const cornerBottom = Math.round(navbar.getBoundingClientRect().bottom);

    const read = () => {
        const cs = getComputedStyle(head);
        const b = head.getBoundingClientRect();
        return {
            vis: cs.visibility,
            bg: cs.backgroundColor,
            alpha: alphaOf(cs.backgroundColor),
            box: [Math.round(b.left), Math.round(b.top),
                  Math.round(b.right), Math.round(b.bottom)],
            covers: b.left <= 0.5 && b.top <= 0.5
                && b.right >= railWidth - 0.5 && b.bottom >= cornerBottom - 0.5,
            clickable: (() => {
                const el = document.elementFromPoint(railWidth / 2, cornerBottom / 2);
                return !!(el && (el === head || head.contains(el)));
            })(),
        };
    };

    const closed = read();
    document.body.classList.add('o_apps_menu_opened');
    await settle(400);
    const open = read();
    const railVis = getComputedStyle(rail).visibility;
    const chevron = head.querySelector('.o_sapian_rail_chevron');
    const chevronShown = chevron
        ? getComputedStyle(chevron).display !== 'none' : false;
    document.body.classList.remove('o_apps_menu_opened');
    await settle(400);
    const after = read();

    console.log('SAPIAN-SIDEBAR-CORNER railWidth=' + railWidth
        + ' cornerBottom=' + cornerBottom
        + ' closedVis=' + closed.vis
        + ' openVis=' + open.vis + ' openAlpha=' + open.alpha
        + ' openBg="' + open.bg + '"'
        + ' openBox=' + open.box.join(',')
        + ' covers=' + open.covers
        + ' clickable=' + open.clickable
        + ' railVis=' + railVis
        + ' chevron=' + chevronShown
        + ' afterVis=' + after.vis);

    // THE ROWS STILL STAND DOWN — the half of PR #43 that was right.
    if (railVis !== 'hidden') {
        throw new Error('the rail is ' + railVis + ' with the launcher open; '
            + 'the app rows duplicate the launcher and must stand down');
    }
    // THE MARK DOES NOT.
    if (open.vis !== 'visible') {
        throw new Error('the brand header is ' + open.vis + ' with the launcher '
            + 'open, so the top-left corner paints page background — a white '
            + 'rectangle where the logo was');
    }
    if (open.alpha < 1) {
        throw new Error('the brand header paints ' + open.bg + ' (alpha '
            + open.alpha + '), so the page shows through the corner');
    }
    if (!open.covers) {
        throw new Error('the brand header box ' + open.box.join(',')
            + ' does not cover the exposed corner 0,0,' + railWidth + ','
            + cornerBottom + ' — page background is left showing around it');
    }
    // IDENTITY, NOT A CONTROL.
    if (open.clickable) {
        throw new Error('the brand header is still clickable with the launcher '
            + 'open — it collapses a panel the user cannot see');
    }
    if (chevronShown) {
        throw new Error('the collapse chevron is still shown with the launcher '
            + 'open, offering a control that does nothing visible');
    }
    // AND IT GOES BACK TO BEING A CONTROL AFTERWARDS.
    if (after.vis !== 'visible') {
        throw new Error('the header did not survive the launcher round trip: '
            + after.vis);
    }
    if (!after.clickable) {
        throw new Error('the header is no longer clickable after the launcher '
            + 'closed, so the collapse toggle is dead');
    }
    console.log('test successful');
})();
"""

SIDEBAR_LAUNCHER_JS = SIDEBAR_SETTLE_JS + SAPIAN_FORCED_HEIGHT + """
(async () => {
    await sapianSidebarSettle();
    const rail = document.querySelector('.o_sapian_rail');
    // Forced, for the same reason as the occlusion block: the scroll-survives
    // assertion is the whole point of choosing `visibility` over
    // `display: none`, and it needs a rail that genuinely scrolls on a
    // two-app database as well as on a forty-app one.
    const tiles = [...rail.querySelectorAll('.o_sapian_rail_app')];
    rail.style.height = sapianForcedHeight(
        rail, tiles[0].getBoundingClientRect().height, tiles.length) + 'px';
    await settle(200);
    rail.scrollTop = rail.scrollHeight;
    await settle(300);
    const scrolledTo = rail.scrollTop;
    if (scrolledTo < 10) {
        rail.style.height = '';
        throw new Error('could not force the rail to overflow, so the '
            + 'scroll-survives assertion below would prove nothing');
    }

    const cornerIsRail = () => {
        const b = rail.getBoundingClientRect();
        const el = document.elementFromPoint(b.left + b.width / 2, b.top + 20);
        return !!(el && (el === rail || rail.contains(el)));
    };

    const before = { vis: getComputedStyle(rail).visibility, hit: cornerIsRail() };

    document.body.classList.add('o_apps_menu_opened');
    await settle(300);
    const open = { vis: getComputedStyle(rail).visibility, hit: cornerIsRail() };

    // COLLAPSED TOO, while the launcher is still open: the rule keys off the
    // rail, not off its width, but a 56px rail that stayed visible would be
    // the same defect in a narrower strip.
    rail.querySelector('.o_sapian_rail_toggle').click();
    await settle(700);
    const openCollapsed = {
        vis: getComputedStyle(rail).visibility,
        collapsed: rail.classList.contains('o_sapian_rail_collapsed'),
    };
    rail.querySelector('.o_sapian_rail_toggle').click();
    await settle(700);

    document.body.classList.remove('o_apps_menu_opened');
    await settle(300);
    const after = {
        vis: getComputedStyle(rail).visibility,
        hit: cornerIsRail(),
        scrollTop: rail.scrollTop,
    };

    rail.style.height = '';
    console.log('SAPIAN-SIDEBAR-LAUNCHER before=' + before.vis + '/' + before.hit
        + ' open=' + open.vis + '/' + open.hit
        + ' openCollapsed=' + openCollapsed.vis + '/' + openCollapsed.collapsed
        + ' after=' + after.vis + '/' + after.hit
        + ' scroll=' + scrolledTo + '/' + after.scrollTop);

    if (before.vis !== 'visible' || !before.hit) {
        throw new Error('the rail was already hidden before the launcher '
            + 'opened, so this test cannot tell that opening it did anything');
    }
    if (open.vis !== 'hidden') {
        throw new Error('with the launcher open the rail computes visibility='
            + open.vis + ' — it is still painted over/under the overlay');
    }
    if (open.hit) {
        throw new Error('the rail still answers elementFromPoint with the '
            + 'launcher open, so its corner is still clickable');
    }
    if (!openCollapsed.collapsed) {
        throw new Error('the rail did not collapse while the launcher was '
            + 'open, so the collapsed half measured the expanded rail');
    }
    if (openCollapsed.vis !== 'hidden') {
        throw new Error('collapsed, with the launcher open, the rail computes '
            + 'visibility=' + openCollapsed.vis);
    }
    if (after.vis !== 'visible' || !after.hit) {
        throw new Error('the rail did not come back when the launcher closed: '
            + after.vis + '/' + after.hit);
    }
    // THE REASON IT IS `visibility` AND NOT `display: none`.
    if (after.scrollTop !== scrolledTo) {
        throw new Error('the rail lost its scroll position across the launcher '
            + 'round trip: ' + scrolledTo + ' -> ' + after.scrollTop);
    }
    console.log('test successful');
})();
"""


class SidebarBrowserCase(HttpCase):
    """Shared setup: tours off, and the brand read from the palette."""

    browser_size = "1366x900"

    def setUp(self):
        super().setUp()
        admin = self.env.ref("base.user_admin")
        if "tour_enabled" in admin._fields:
            admin.sudo().tour_enabled = False
        # The launcher would cover the sidebar, and this file measures the
        # sidebar. Same reason the occlusion test sets it.
        if "is_redirect_home" in admin._fields:
            admin.sudo().is_redirect_home = False
        self.env.flush_all()

    def brand_css_rgb(self):
        """The brand as the browser will report it, read from the palette.

        Hardcoding the hex here would leave this test asserting the old colour
        after a re-brand — and passing, because it would still differ from the
        inactive row.
        """
        value = brand.brand_primary().lstrip("#")
        return "rgb(%d, %d, %d)" % tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))

    def run_sidebar(self, code):
        self.browser_js(
            "/odoo",
            code.replace("%BRAND%", self.brand_css_rgb()),
            "!!document.querySelector('.o_sapian_rail .o_sapian_rail_app')",
            login="admin",
        )


@tagged("post_install", "-at_install")
class TestSapianSidebarStates(SidebarBrowserCase):
    """Rest, hover and active are distinguishable — SPEC section 1."""

    def test_the_active_row_is_visibly_the_active_row(self):
        self.run_sidebar(SIDEBAR_STATES_JS)


@tagged("post_install", "-at_install")
class TestSapianSidebarStatesDiscriminate(SidebarBrowserCase):
    """And the check above notices when each of those things is broken."""

    def test_the_sidebar_check_goes_red_for_each_thing_it_checks(self):
        self.run_sidebar(SIDEBAR_DISCRIMINATES_JS)


@tagged("post_install", "-at_install")
class TestSapianSidebarCollapse(SidebarBrowserCase):
    """The collapse toggle, and what it must not disturb."""

    def test_collapsing_narrows_the_sidebar_and_keeps_everything_else(self):
        self.run_sidebar(SIDEBAR_COLLAPSE_JS)


@tagged("post_install", "-at_install")
class TestSapianSidebarHeader(SidebarBrowserCase):
    """The header is the product's mark, and it announces its own state."""

    def test_the_header_is_the_logo_and_says_whether_it_is_expanded(self):
        self.run_sidebar(SIDEBAR_HEADER_JS)


@tagged("post_install", "-at_install")
class TestSapianSidebarHeaderOccludes(SidebarBrowserCase):
    """The sticky header paints over the rows scrolling under it.

    Nothing asserted this before. Every sidebar test measured geometry and
    computed styles, and all of them passed on a header that was 92%
    transparent on hover with the rows legible through it.
    """

    def test_the_header_is_opaque_and_nothing_shows_through_it(self):
        self.run_sidebar(SIDEBAR_OCCLUSION_JS)


@tagged("post_install", "-at_install")
class TestSapianSidebarStandsDownForTheLauncher(SidebarBrowserCase):
    """With the app launcher open the rail is neither painted nor clickable."""

    def test_the_rail_hides_while_the_launcher_is_open_and_keeps_its_scroll(self):
        self.run_sidebar(SIDEBAR_LAUNCHER_JS)


@tagged("post_install", "-at_install")
class TestSapianSidebarCornerIsNotAHole(SidebarBrowserCase):
    """With the launcher open the corner is the mark, not page background."""

    def test_the_brand_header_paints_the_corner_and_is_not_a_control(self):
        self.run_sidebar(SIDEBAR_CORNER_JS)


@tagged("post_install", "-at_install")
class TestSapianSidebarKeyboard(SidebarBrowserCase):
    """Keyboard reachable, with a ring you can actually see — SPEC section 7."""

    def test_rows_and_the_toggle_are_keyboard_operable(self):
        self.run_sidebar(SIDEBAR_KEYBOARD_JS)
