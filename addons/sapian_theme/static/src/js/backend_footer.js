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
 * WHERE THE TEXT COMES FROM
 * -------------------------
 * The same system parameter as the login page, `sapian_theme.support_contact`,
 * delivered through `session_info` (see models/ir_http.py). One setting, two
 * surfaces. A second setting meaning the same thing is how one of them goes
 * stale.
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

    get company() {
        return session.sapian_footer_company || "";
    }

    get support() {
        return session.sapian_support_contact || "";
    }
}

registry.category("main_components").add("sapian_theme.BackendFooter", {
    Component: SapianBackendFooter,
});
