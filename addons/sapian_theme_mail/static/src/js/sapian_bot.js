/**
 * Odoo's name and face, where Discuss puts them in front of a client's staff.
 *
 * THREE PATCHES, and each one is as narrow as it can be. The bot's NAME,
 * EMAIL and AVATAR are not here at all — those are a record, written by
 * `res.partner._sapian_apply_bot_identity` (see models/res_partner.py), which
 * is why the "Turn on notifications" prompt needed no code: its only leak was
 * `store.odoobot.avatarUrl`, and that follows the record.
 *
 * WHAT A GUARD CAN AND CANNOT SAY ABOUT THESE
 * -------------------------------------------
 * Stated plainly because it shapes tests/test_bot_identity.py. A patch ADDS
 * code to the bundle; it never removes the code it patches. So `"Install
 * Odoo"` remains a string inside the served `web.assets_backend` even when the
 * menu renders "Install SapianERP", and no assertion of the form "Odoo's
 * string is absent from the bundle" can ever pass. What CAN be asserted, and
 * is:
 *
 *   * ours is IN the served bundle — which is the failure that actually
 *     happens (a module installed but absent from the serving process's
 *     addons_path delivers zero JS in silence; see CLAUDE.md);
 *   * the strings we intercept are still the ones upstream ships, read out of
 *     the served bundle, so an upstream rewording turns a test red instead of
 *     turning a patch into a no-op;
 *   * the set of Odoo-identity strings on this surface has not GROWN, which is
 *     how the next Odoo release gets caught reintroducing one.
 */

import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { OutOfFocusService } from "@mail/core/common/out_of_focus_service";
import { notificationPermissionService } from "@mail/core/common/notification_permission_service";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

/**
 * The product name, from `sapian_theme/vendor.py` by way of `session_info`
 * (sapian_theme/models/ir_http.py) — never a literal here. The backend is an
 * OWL application and cannot reach a Python constant any other way, and the
 * whole point of that file is that a re-brand is one edit.
 *
 * The fallback is the string, not the empty string: a session payload that
 * somehow lacks the key must still not render "Install undefined".
 */
export const SAPIAN_PRODUCT = session.sapian_vendor_product || "SapianERP";

/**
 * The icon Odoo hands to `Notification` when a message has no author, in
 * `OutOfFocusService.notify`. It is a bare string literal in the middle of a
 * method, so it cannot be overridden by any means other than recognising it.
 * Exported so the test can assert this exact path is still what the served
 * mail bundle contains — the day upstream renames the file, that assertion
 * goes red rather than this interception quietly doing nothing.
 */
export const ODOO_PUSH_ICON = "/mail/static/src/img/odoobot_transparent.png";
export const SAPIAN_PUSH_ICON = "/sapian_theme_mail/static/src/img/sapian_bot.png";

/**
 * 1. "Install Odoo" in the messaging menu.
 *
 * A getter returning a fresh object each call, so the patch rebuilds it from
 * `super` and replaces one key. Everything else — the body copy, the click
 * handler, the visibility rule, and the icon, which is the bot's avatar and
 * therefore already ours — is carried across untouched.
 */
patch(MessagingMenu.prototype, {
    get installationRequest() {
        return {
            ...super.installationRequest,
            displayName: _t("Install %(product)s", { product: SAPIAN_PRODUCT }),
        };
    },
});

/**
 * 2. "Odoo will send notifications on this device!" and its denied twin.
 *
 * These two live inside a closure built in `start()`, not in a method, so
 * there is nothing to override — the only seam is the returned `state`. So the
 * patch wraps `requestPermission` and reimplements the four lines that emit
 * the toasts.
 *
 * Reimplementing upstream logic is a cost, and it is bounded here: the
 * permission call and the normalisation are still upstream's, called through
 * `this`. Should Odoo add a third outcome, the user sees no toast for it
 * rather than an Odoo-branded one, and the bundle sweep in the tests goes red
 * on the new string.
 */
patch(notificationPermissionService, {
    async start(env, services) {
        const state = await super.start(env, services);
        const notification = services.notification;
        const service = this;
        state.requestPermission = async () => {
            if (!browser.Notification || state.permission !== "prompt") {
                return;
            }
            state.permission = service._normalizePermission(
                await browser.Notification.requestPermission()
            );
            if (state.permission === "denied") {
                notification.add(
                    _t("%(product)s will not send notifications on this device.", {
                        product: SAPIAN_PRODUCT,
                    }),
                    { type: "warning", title: _t("Notifications blocked") }
                );
            } else if (state.permission === "granted") {
                notification.add(
                    _t("%(product)s will send notifications on this device!", {
                        product: SAPIAN_PRODUCT,
                    }),
                    { type: "success", title: _t("Notifications allowed") }
                );
            }
        };
        return state;
    },
});

/**
 * 3. Odoo's face on desktop push notifications.
 *
 * Intercepted at `sendNotification` rather than in `notify`, where the literal
 * lives, because `notify` is forty lines of message formatting we would have
 * to copy to change one of them. This substitutes the default icon and touches
 * nothing else: when a message HAS an author, `notify` has already replaced
 * the icon with that author's avatar and the condition below is false.
 *
 * Our replacement is transparent-backed, which the OS tray requires — measured
 * on the shipped file: 45.5% of its pixels are fully transparent and all four
 * corners are alpha 0. Odoo keeps two images for exactly this reason
 * (`odoobot.png` is a filled purple tile, 0% transparent; only
 * `odoobot_transparent.png` is safe over an unknown background).
 */
patch(OutOfFocusService.prototype, {
    async sendNotification(params) {
        if (params?.icon === ODOO_PUSH_ICON) {
            params = { ...params, icon: SAPIAN_PUSH_ICON };
        }
        return super.sendNotification(params);
    },
});
