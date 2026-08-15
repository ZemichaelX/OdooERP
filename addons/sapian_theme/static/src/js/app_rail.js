/**
 * The SapianERP app rail — a persistent, icon-only launcher down the left edge.
 *
 * WHY IT EXISTS
 * -------------
 * Odoo 19's DESKTOP apps menu renders no icons at all. `web.NavBar.AppsMenu`
 * has two branches: the small-screen one draws `<img t-attf-src="{{app.webIconData}}"/>`,
 * and the desktop one is a plain `DropdownItem` with `t-esc="app.name"`
 * (web/static/src/webclient/navbar/navbar.xml). So on the screen a user
 * actually works in, the ten icons in brand/icons/ are invisible — they show up
 * only in the narrow-screen drawer and the Apps list. The rail is what makes
 * them exist.
 *
 * WHY main_components AND NOT THE NAVBAR
 * --------------------------------------
 * Measured on this Odoo 19 tree, not assumed (the command is in README.md):
 *
 *   20  registration call sites into the `main_components` registry, across
 *       7 shipped modules (web, mail, website, html_editor, html_builder,
 *       point_of_sale, base_import)
 *    1  module patches `NavBar.prototype` (website) and the same module is the
 *       only one to extend the `web.NavBar` template
 *    0  modules inherit the `web.WebClient` template
 *
 * The registry is the extension point Odoo itself uses twenty times over; the
 * navbar is contested by exactly one module and the web client by none, which
 * is a measure of how unusual — not how safe — those two would be. Registering
 * a component costs nothing that another module can take away, whereas the
 * login-branding defect (README.md, "prefer assets to template inheritance")
 * was precisely a lost inheritance contest.
 *
 * THE FIVE THINGS THIS DEPENDS ON, none of them internal to the navbar:
 *   1. the `main_components` registry
 *   2. the `menu` service — getApps / getCurrentApp / selectMenu
 *   3. the `MENUS:APP-CHANGED` bus event
 *   4. the `ACTION_MANAGER:UI-UPDATED` bus event (to get out of the way of a
 *      fullscreen action, exactly as WebClient itself does)
 *   5. the `/odoo/<action-path>` URL shape, mirrored from
 *      `NavBar.getMenuItemHref` (navbar.js) so a middle-click still opens a tab
 *
 * Nothing is patched and nothing is inherited.
 */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";

import { Component, onMounted, onPatched, useRef, useState } from "@odoo/owl";

// Per BROWSER, not per user. A collapse toggle is a use-of-this-screen
// preference — the same person wants it open on a 27" monitor and shut on a
// laptop — so it does not belong in a res.users column that would follow them
// between the two. localStorage also means no write on every click, and no new
// field to add access rules for.
export const RAIL_COLLAPSED_KEY = "sapian_theme.rail_collapsed";

export class SapianAppRail extends Component {
    static template = "sapian_theme.AppRail";
    static props = {};

    setup() {
        this.menuService = useService("menu");
        this.railRef = useRef("rail");
        this.state = useState({
            fullscreen: false,
            collapsed: browser.localStorage.getItem(RAIL_COLLAPSED_KEY) === "1",
        });

        // The apps list changes when a module is installed or uninstalled, and
        // the highlight changes on every app switch. Both arrive on this event.
        useBus(this.env.bus, "MENUS:APP-CHANGED", () => this.render());

        // Same event and the same guard WebClient.setup uses to drive its own
        // `state.fullscreen`. Without this the rail would sit on top of an
        // action that asked for the whole screen.
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", ({ detail: mode }) => {
            if (mode !== "new") {
                this.state.fullscreen = mode === "fullscreen";
            }
        });

        // 36 apps do not fit on a laptop screen; the rail scrolls (see
        // README.md, "36 apps and 900 pixels"). Whatever you are IN should be
        // visible without hunting for it, so bring it into view on arrival and
        // after every app switch.
        //
        // ON APP SWITCH — not on every render. `onPatched` fires for reasons
        // that have nothing to do with which app you are in: an action
        // finishing, the fullscreen state changing, the app list reloading.
        // Scrolling on all of them threw away wherever the USER had scrolled
        // to, every time. Measured on a 36-app database: scrolled to the
        // bottom (scrollTop 828 of 828), one re-render, scrollTop 0 — the
        // last twelve apps gone from view without anyone touching the rail.
        // At 40 apps the same, 1020 -> 0.
        //
        // This is also what made the overflow test flaky rather than merely
        // strict: it sets scrollTop and measures a frame later, so a re-render
        // landing in that window made the last tile unreachable and the rail
        // look truncated. Same geometry, opposite result, three green runs and
        // one red on identical code.
        this.lastScrolledApp = undefined;
        onMounted(() => this.scrollCurrentIntoView());
        onPatched(() => this.scrollCurrentIntoView());
    }

    get apps() {
        return this.menuService.getApps();
    }

    get currentApp() {
        return this.menuService.getCurrentApp();
    }

    /**
     * Mirrors NavBar.getMenuItemHref
     * (web/static/src/webclient/navbar/navbar.js). It is three lines of URL
     * convention rather than an import, because importing it would mean
     * reaching into the navbar — the one thing this component sets out not to
     * do. If the convention ever changes, the rail's links degrade to the
     * click handler below, which does not use them.
     */
    hrefFor(app) {
        return `/odoo/${app.actionPath || "action-" + app.actionID}`;
    }

    /**
     * The template calls this through `t-on-click.prevent`, which suppresses
     * the anchor's own navigation so an app switch stays in-page.
     *
     * Ctrl/Cmd-click still opens a tab, and not by accident: WebClient
     * registers `onGlobalClick` on window with `capture: true` and calls
     * `stopImmediatePropagation()` for a modified click on an `a[href]`
     * (webclient.js), so it runs before this handler and lets the browser do
     * its normal thing. Middle-click never fires `click` at all.
     */
    onAppClick(app) {
        this.menuService.selectMenu(app);
    }

    /**
     * Collapse to icons, or expand back to icons + labels.
     *
     * The competitor has no collapse control at all and hardcodes a width per
     * breakpoint (SPEC-navigation-chrome.md, section 6). At 36 apps a 200px
     * column is a fifth of a laptop screen, and there are days when you want
     * the width back — so this is a real toggle, and it remembers.
     *
     * It does NOT touch scrollTop. Collapsing changes the rail's width, not
     * which app you are in, and `scrollCurrentIntoView` is guarded on the
     * current app's ID precisely so a re-render for an unrelated reason cannot
     * throw away where the user had scrolled to (README.md, "On app switch —
     * not on every render"). Toggling the rail is one of those unrelated
     * reasons, and TestSapianAppRailKeepsScroll covers it.
     */
    toggleCollapsed() {
        this.state.collapsed = !this.state.collapsed;
        browser.localStorage.setItem(RAIL_COLLAPSED_KEY, this.state.collapsed ? "1" : "0");
    }

    /**
     * Bring the current app into view — but only when the current app has
     * actually CHANGED since the last time we did it.
     *
     * The guard is the whole point. Without it every re-render re-ran the
     * scroll, and because the active tile is usually near the top that meant
     * silently resetting the user's scroll position to the top of the rail.
     * With 36 apps the user is two thirds of the way down the list and gets
     * sent back to the start by an action they did not connect to the rail at
     * all.
     *
     * Comparing the app ID rather than a boolean: the app object is rebuilt by
     * the menu service on reload, so identity is not stable, and "did the
     * highlight move" is exactly the question.
     */
    scrollCurrentIntoView() {
        const rail = this.railRef.el;
        if (!rail) {
            return;
        }
        const current = this.currentApp;
        const currentId = current ? current.id : null;
        if (currentId === this.lastScrolledApp) {
            return;
        }
        this.lastScrolledApp = currentId;
        const active = rail.querySelector(".o_sapian_rail_app_active");
        if (active) {
            active.scrollIntoView({ block: "nearest" });
        }
    }
}

registry.category("main_components").add("sapian_theme.AppRail", {
    Component: SapianAppRail,
});
