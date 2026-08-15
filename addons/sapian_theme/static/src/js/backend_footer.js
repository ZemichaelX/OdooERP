/**
 * The SapianERP backend footer — a copyright and support line on every page.
 *
 * WHY IT EXISTS
 * -------------
 * A competing Ethiopian ERP carries "© <year> <Company>. All Rights Reserved.
 * For Support: +251… +251…" across the bottom of every backend screen. It is
 * doing two jobs at once: it signs the software as the client's, and it puts
 * the support number in front of a user at the moment they are stuck — which
 * is the moment they are least likely to go looking for it.
 *
 * WHERE THE TEXT COMES FROM — AND WHOSE IT IS
 * -------------------------------------------
 * `sapian_theme/vendor.py`, delivered through `session_info` (see
 * models/ir_http.py). SAPIAN's name and SAPIAN's support line, from constants
 * a tenant admin cannot rewrite.
 *
 * It used to be `res.company.name` and the tenant's
 * `sapian_theme.support_contact` — so a tenant installed for Golbon Trading
 * told its users, at the bottom of every page, that the software was Golbon's.
 * The competitor whose footer this copies gets that half right: theirs carries
 * the CONSULTANCY's name and numbers.
 *
 * The tenant's parameter is NOT gone; it still drives the LOGIN page, where a
 * client's staff are the audience and the number they need is their own. The
 * two contacts stopped meaning the same thing, so they stopped sharing a
 * setting.
 *
 * WHY main_components — THE SAME ARGUMENT AS THE RAIL
 * --------------------------------------------------
 * Registered in the `main_components` registry, `position: fixed`, one
 * padding-bottom rule on `.o_web_client`, nothing patched and nothing
 * inherited. That is the shape the app rail already established on this tree
 * (20 registrations into that registry across 7 shipped modules; 1 module
 * patches the navbar; 0 inherit the web client) and the reasoning has not
 * changed — see app_rail.js for the counts.
 *
 * It also hides itself in the two situations where a fixed bar at the bottom
 * of the viewport is wrong:
 *   - a fullscreen action (`ACTION_MANAGER:UI-UPDATED`), exactly as the rail
 *     and WebClient itself do;
 *   - below the md breakpoint, where vertical space is the scarce thing. That
 *     is done in SCSS, in the same media query as the padding rule, so the two
 *     cannot disagree.
 *
 * The year is taken from the browser clock. It is a copyright line, not an
 * accounting date: nothing is computed from it, and a client whose laptop
 * clock is wrong has larger problems than a footer.
 */

import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { session } from "@web/session";

import { Component, useState } from "@odoo/owl";

export class SapianBackendFooter extends Component {
    static template = "sapian_theme.BackendFooter";
    static props = {};

    setup() {
        this.state = useState({ fullscreen: false });
        // The same event and the same guard WebClient.setup and the app rail
        // both use. `mode === "new"` means a dialog opened, which does not
        // change the underlying page — only "fullscreen" should hide us.
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", ({ detail: mode }) => {
            if (mode !== "new") {
                this.state.fullscreen = mode === "fullscreen";
            }
        });
    }

    get year() {
        return new Date().getFullYear();
    }

    /**
     * "© 2026 " — and THE TRAILING SPACE IS THE POINT.
     *
     * It is a getter rather than template text because our name became a
     * link, and the space between the year and the link cannot live in the
     * template: OWL removes whitespace-only text nodes between elements, so
     *
     *     © <t t-esc="year"/>
     *     <a …><t t-esc="company"/></a>
     *
     * renders "© 2026Sapian Technologies PLC." — measured on a running
     * client, not theorised. A non-breaking-space entity does not help
     * either, because JavaScript's \s matches U+00A0 and OWL's trim would
     * take it too. A string set through `t-esc` is written as textContent at
     * runtime, where nothing trims it.
     *
     * `sapianFooterReport` asserts the whole line against one regex with a
     * single space in it, so deleting this space fails a test rather than
     * shipping.
     */
    get copyrightPrefix() {
        return `© ${this.year} `;
    }

    /**
     * SAPIAN'S name, not the tenant's.
     *
     * This used to be `session.sapian_footer_company`, which was
     * `res.company.name` — so a tenant installed for Golbon Trading signed
     * every backend page as Golbon's software. The values now come from
     * `sapian_theme/vendor.py`, which is a constant a tenant admin cannot
     * rewrite; see models/ir_http.py.
     */
    get company() {
        return session.sapian_vendor_company || "";
    }

    get support() {
        return session.sapian_vendor_support || "";
    }

    get url() {
        return session.sapian_vendor_url || "";
    }
}

registry.category("main_components").add("sapian_theme.BackendFooter", {
    Component: SapianBackendFooter,
});
