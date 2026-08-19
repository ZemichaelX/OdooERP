# -*- coding: utf-8 -*-
"""The auth pages are OURS; the client's website is theirs.

THE RULE THIS ENCODES
---------------------
Inward-facing surfaces are Sapian's, outward-facing surfaces are the client's.
`/web/login`, `/web/signup` and `/web/reset_password` are the application's own
front door — every client sees the same one, in Sapian teal. The client's
public website is theirs: their logo, their colours, their copy.

Both are served from the SAME frontend bundle, which is what made this
confusing enough to ship wrong.

THE DEFECT
----------
`html_editor` is `auto_install` and rebuilds Bootstrap's `$theme-colors` from
the website EDITOR PALETTE, so `$o-brand-primary` never reaches the frontend.
The brand was therefore applied by one narrow rule scoped to `.oe_login_form`
— and only the login page has a form with that class. Measured on the demo
tenant:

    /web/login           rgb(20, 69, 79)     the brand
    /web/reset_password  rgb(113, 75, 103)   whatever the palette says

The same bundle, the same button, two colours. On a tenant whose editor palette
has been changed, that second value is the CLIENT's colour instead — the same
defect wearing different paint, and arguably worse, because the auth page then
wears the website's identity rather than an obviously-wrong purple.

WHAT THESE TESTS READ
---------------------
The SERVED CSS and the SERVED PAGES. Never the SCSS source: the source says
what we wrote, and every defect in this file's history was a gap between what
we wrote and what the browser was handed. The stylesheet is fetched from the
`<link>` the page itself carries, so a bundle rename cannot leave these tests
asserting against a file nobody loads.
"""

import json
import re

from odoo.tests import HttpCase, tagged

from .. import brand

# `/web/login` is `web`'s and exists on every database. `/web/reset_password`
# and `/web/signup` belong to `auth_signup`, which `sapian_theme` does NOT
# depend on — its manifest is base + web, and a CI job asserts it installs and
# passes entirely alone. On that database the reset route is a 404.
#
# So the list is DERIVED, never skipped: asserting against a route that does
# not exist measures Odoo's routing, not our branding, and skipping the whole
# file would take the login assertions with it.
# `test_the_route_list_did_not_quietly_shrink` is what stops the derivation
# becoming a way to test nothing.
BASE_ROUTE = "/web/login"
SIGNUP_ROUTES = ("/web/reset_password",)

# The class our inheritance of `web.login_layout` puts on <body>. It is OURS,
# which is the one way this scope is sturdier than the `.oe_login_form` it
# replaced: nobody upstream can rename it.
AUTH_SCOPE = "o_sapian_auth"


class AuthPageCase(HttpCase):
    """Fetches a page and the stylesheet that page actually links to."""

    def brand_hex(self):
        """From the palette, never a literal — a re-brand must move this."""
        return brand.brand_primary().lower()

    def auth_routes(self):
        """The auth routes that exist on THIS database."""
        routes = [BASE_ROUTE]
        if self.auth_signup_installed():
            routes.extend(SIGNUP_ROUTES)
        return tuple(routes)

    def auth_signup_installed(self):
        return bool(
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", "auth_signup"), ("state", "=", "installed")])
        )

    def _page(self, route):
        response = self.url_open(route)
        self.assertEqual(response.status_code, 200, "%s did not render" % route)
        html = response.text
        self.assertGreater(
            len(html), 1500, "%s came back too small to be a rendered page" % route
        )
        return html

    def _frontend_css(self, html, route):
        """The stylesheet the page links, fetched and returned as text.

        Taken from the page's own <link> rather than by guessing an asset
        name: the bundle URL carries a content hash and can be renamed
        upstream, and a test asserting against a file the page does not load
        is a test that passes while the user sees something else.
        """
        hrefs = re.findall(r'<link[^>]+href="([^"]+\.css[^"]*)"', html)
        self.assertTrue(hrefs, "%s links no stylesheet at all" % route)
        css = ""
        for href in hrefs:
            got = self.url_open(href)
            if got.status_code == 200:
                css += got.text
        self.assertGreater(len(css), 5000, "the stylesheets %s links came back empty" % route)
        return css


@tagged("post_install", "-at_install")
class TestAuthPagesAreOurs(AuthPageCase):
    """Every auth page carries our scope, and the served CSS paints it."""

    def test_every_auth_page_carries_the_scope(self):
        """The class has to be on the page, or the CSS below cannot apply.

        Asserted per route, because the whole defect was one route having it
        and another not.
        """
        for route in self.auth_routes():
            html = self._page(route)
            self.assertIn(
                AUTH_SCOPE,
                html,
                "%s does not carry %s, so the brand rule cannot match it and "
                "the page falls through to the website's palette" % (route, AUTH_SCOPE),
            )

    def test_the_served_css_paints_the_scope_in_the_brand(self):
        """Read out of the stylesheet the browser is handed, not the source."""
        html = self._page("/web/login")
        css = self._frontend_css(html, "/web/login")
        rules = [
            block
            for block in re.split(r"(?<=\})", css)
            if AUTH_SCOPE in block and "--btn-bg" in block
        ]
        self.assertTrue(
            rules,
            "the served CSS has no .%s rule setting --btn-bg; the auth pages "
            "are painted by whatever the editor palette says" % AUTH_SCOPE,
        )
        self.assertTrue(
            any(self.brand_hex() in block.lower() for block in rules),
            "the .%s button rule in the served CSS does not carry the brand "
            "%s" % (AUTH_SCOPE, self.brand_hex()),
        )

    def test_the_old_narrow_scope_is_gone_from_the_served_css(self):
        """`.oe_login_form` was removed only after the wider scope was proved.

        Kept as an assertion so it cannot creep back as a second, overlapping
        source of truth for the same colour.
        """
        css = self._frontend_css(self._page("/web/login"), "/web/login")
        for block in re.split(r"(?<=\})", css):
            if "--btn-bg" in block and "oe_login_form" in block:
                self.fail(
                    "the served CSS still scopes the brand button to "
                    ".oe_login_form — two rules for one colour, and the "
                    "narrow one only ever reached /web/login"
                )

    def test_the_route_list_did_not_quietly_shrink(self):
        """THE GUARD ON THE DERIVATION.

        Deriving the route list is how these tests run on a database without
        `auth_signup` instead of skipping. It is also how they could quietly
        stop covering the page the whole change is about, so: where
        `auth_signup` IS installed — which is every real tenant, and the
        configuration the defect lived in — the reset page must be in the list.
        """
        routes = self.auth_routes()
        self.assertIn(BASE_ROUTE, routes, "the login page is not being checked at all")
        if self.auth_signup_installed():
            for route in SIGNUP_ROUTES:
                self.assertIn(
                    route,
                    routes,
                    "auth_signup is installed but %s is not being checked — the "
                    "page this change exists for is going untested" % route,
                )
        else:
            self.assertEqual(
                routes,
                (BASE_ROUTE,),
                "auth_signup is absent, so only the login route can be checked",
            )

    def test_the_reset_page_is_branded_like_the_login_page(self):
        """The page the whole change is about, asserted against its sibling.

        Not "reset looks right" in isolation — the two must agree, which is
        what "the same auth surface" means.
        """
        if not self.auth_signup_installed():
            # Not a skip: the login half still runs, and the derivation guard
            # above is what proves this branch is not being taken on a database
            # where the reset page exists.
            self.assertIn(AUTH_SCOPE, self._page(BASE_ROUTE))
            return
        for name, route in (("login", BASE_ROUTE), ("reset", SIGNUP_ROUTES[0])):
            self.assertIn(
                AUTH_SCOPE, self._page(route), "the %s page lost the auth scope" % name
            )

    def _logo_slot(self, html, route):
        """The card's logo block, extracted — NOT the whole page.

        This is narrower than it first was, and the narrowing was earned. The
        first version asked whether the company's NAME appeared anywhere in the
        HTML, and it passed on a page with no logo block at all: `website`
        emits the company name into the page's JSON-LD metadata
        (`"name": "My Company"`), so the assertion was satisfied by a `<script
        type="application/ld+json">` the user never sees. Found by a red proof
        whose failure COUNT matched and whose failing TEST did not.
        """
        found = re.search(
            r'<div class="text-center pb-3 border-bottom mb-4">(.*?)</div>',
            html,
            re.S,
        )
        self.assertTrue(
            found,
            "%s has no logo block at all — the auth card renders straight into "
            "the form with nothing identifying the company" % route,
        )
        return found.group(1)

    def test_both_auth_pages_show_the_company_in_the_logo_slot(self):
        """The reset page showed NOTHING before: visibleImages 0 against 1.

        The logo lives in the shared LAYOUT now rather than on the login form,
        so both pages get it.
        """
        company = self.env.company
        for route in self.auth_routes():
            slot = self._logo_slot(self._page(route), route)
            self.assertTrue(
                "/web/binary/company_logo" in slot or company.name in slot,
                "%s renders a logo block containing neither the company logo "
                "nor its name: %s" % (route, slot[:120]),
            )

    def test_a_company_without_a_logo_degrades_to_its_name_on_both_pages(self):
        """THE DISCRIMINATION PROOF for the degradation.

        Without it, a page rendering Odoo's stock placeholder would satisfy the
        test above — `/web/binary/company_logo` always returns an image, its
        own when the company has set none. Asserted INSIDE the slot, so the
        name in the page's metadata cannot stand in for the name on the page.
        """
        self.env.company.logo = False
        self.env.flush_all()
        for route in self.auth_routes():
            slot = self._logo_slot(self._page(route), route)
            self.assertIn(
                self.env.company.name,
                slot,
                "%s does not fall back to the company NAME when there is no "
                "logo, so it is showing somebody's stock image" % route,
            )
            self.assertNotIn(
                "/web/binary/company_logo",
                slot,
                "%s still requests the stock company logo with no logo set" % route,
            )


@tagged("post_install", "-at_install")
class TestAuthScopeDoesNotLeak(AuthPageCase):
    """Our scope must reach the auth pages and stop there.

    The other half of the rule: painting the client's website teal would be the
    same mistake pointed the other way, and it is the one this change could
    plausibly have made.
    """

    def test_the_backend_does_not_carry_the_auth_scope(self):
        """The nearest non-auth page every database has.

        A database without `website` has no public site to check, so the
        backend stands in: if the class were being set globally rather than by
        the auth layout, it would appear here too.
        """
        self.authenticate("admin", "admin")
        html = self.url_open("/odoo").text
        self.assertNotIn(
            AUTH_SCOPE,
            html,
            "the auth scope is on the backend page too, so it is not being set "
            "by the auth layout — it would reach the client's website as well",
        )


# THE PROPERTY GUARD, run in a browser because "computes" is a browser word.
#
# WHAT THE PREVIOUS VERSION OF THIS FILE MISSED, and it missed it three ways.
#
# An operator reported a PURPLE FOCUS OUTLINE on the email input of
# /web/reset_password while this file's other checks reported the page clean:
# login_primary, login_disabled and login_focus_rgb were all at the brand,
# because they measure the sign-in BUTTON. A check that passes on the thing it
# looks at, while the page beside it is wrong.
#
#   1. IT LOOKED AT THE WRONG ELEMENTS. The enumeration was
#      `a, button, .btn, input[type=submit], [role=button], summary` — a plain
#      `<input type="email">` is in none of those, so the control that was
#      actually purple was never collected.
#   2. IT LOOKED AT THE WRONG PROPERTIES. `color` and `background-color` only.
#      A focus ring is `box-shadow` and `border-color`; an outline is
#      `outline-color`. None was read, so the defect had no way to appear.
#   3. IT ASSERTED NOTHING. The JS built a report, logged it, and logged
#      "test successful" unconditionally. There was no failing condition in it
#      at all — a reporter wearing a test's clothes.
#
# And a fourth, which is why nobody noticed the first three: the class was
# tagged `-standard` and selected by the bare `sapian_palette` tag, and NOTHING
# SELECTED THAT TAG. Not CI, not a script — `grep -rn sapian_palette` outside
# this file returned nothing. Its own docstring claimed "the CI job greps for
# that line, so a skipped run cannot pass"; that CI job did not exist. The
# guard had never run once.
#
# WHAT IT DOES NOW. It enumerates every interactive control on each auth page
# and, for each, resolves the colours it wears in EVERY state — rest, hover,
# focus, active, disabled, checked. Rest and focus are read from the browser
# (focus by actually focusing the element); hover, active, disabled and checked
# are resolved out of the stylesheet, because a rule that would apply on hover
# is a fact about the page whether or not a pointer is over it. `var(--x)`
# indirections are resolved against the element, so a variable pointing at
# somebody else's palette is caught rather than reported as "var(--link-color)".
#
# GREYS AND BLACKS ARE ALLOWED and that is deliberate. Body text, muted help
# text and disabled states are not brand decisions; demanding the brand for
# them would make this cry every week, and a guard that cries every week gets
# deleted. The test is "no control wears a colour that belongs to somebody
# else's palette", not "everything is teal".
CONTROL_COLOURS_JS = """
(async () => {
    const BRAND = %(brand)s;

    // ---- 1. THE STORED USER LIST ------------------------------------------
    // "Choose a user" is `web.login_user_switch`, an OWL component mounted by
    // the public-interaction service from <owl-component name="web.user_switch">.
    // It renders nothing unless localStorage carries more than one remembered
    // user, and `setup()` reads that list once, at mount — so seeding it after
    // the page has settled is too late. The seed is written by this test's
    // `ready` expression instead, which the browser evaluates from before the
    // page is interactive; by the time the interaction service starts, the
    // value is there. `switcher_controls` in the summary line is what proves it
    // worked, and the login page fails below if it did not.
    //
    // When the switcher does render, `setup()` puts `d-none` on the login form,
    // which would hide the email and password inputs from this enumeration. The
    // second pass takes that class off — the same thing "Use another user"
    // does — so both sets of controls are measured on the page that carries
    // both.
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    await sleep(300);

    // ---- 2. THE CONTROLS ---------------------------------------------------
    const SELECTOR = [
        "input:not([type=hidden])", "select", "textarea", "button", "a[href]",
        ".btn", "[role=button]", "summary", ".form-check-input",
        ".list-group-item-action", ".o_user_switch_btn",
    ].join(", ");
    const visible = (e) => {
        const b = e.getBoundingClientRect();
        const cs = getComputedStyle(e);
        return b.width > 2 && b.height > 2 && cs.visibility !== "hidden" && cs.display !== "none";
    };
    const controls = [...document.querySelectorAll(SELECTOR)].filter(visible);

    // ---- 3. COLOURS, INCLUDING THE ONES BEHIND A VARIABLE -------------------
    const PROPS = ["color", "background-color", "border-top-color", "border-right-color",
                   "border-bottom-color", "border-left-color", "outline-color",
                   "box-shadow", "accent-color", "caret-color", "text-decoration-color"];
    const resolveVars = (value, el, depth) => {
        if (depth > 3 || !value || value.indexOf("var(") === -1) return value;
        const out = value.replace(/var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,([^()]*))?\)/g, (m, name, fb) => {
            const v = getComputedStyle(el).getPropertyValue(name).trim();
            return v || (fb || "").trim();
        });
        return resolveVars(out, el, depth + 1);
    };
    const hexOf = (r, g, b) => "#" + [r, g, b].map(n => (+n).toString(16).padStart(2, "0")).join("");
    const coloursIn = (value, el) => {
        const found = [];
        if (!value) return found;
        const text = resolveVars(String(value), el, 0);
        const rgbRe = /rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)\s*(?:[,/]\s*([0-9.]+))?\s*\)/g;
        let m;
        while ((m = rgbRe.exec(text))) {
            if (m[4] !== undefined && parseFloat(m[4]) === 0) continue;
            found.push(hexOf(m[1], m[2], m[3]));
        }
        const hexRe = /#([0-9a-fA-F]{6})\b/g;
        while ((m = hexRe.exec(text))) found.push("#" + m[1].toLowerCase());
        // A bare "R, G, B" triple, which is how Bootstrap carries focus rings.
        const tripleRe = /(?:^|[^\d])(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?![\d,])/g;
        while ((m = tripleRe.exec(text))) {
            if ([m[1], m[2], m[3]].every(n => +n >= 0 && +n <= 255)) found.push(hexOf(m[1], m[2], m[3]));
        }
        return found.map(h => h.toLowerCase());
    };
    const neutral = (hex) => {
        const p = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
        return (Math.max(...p) - Math.min(...p)) <= 12;
    };
    const allowed = (hex) => neutral(hex) || BRAND.includes(hex);

    // ---- 4. STATES ---------------------------------------------------------
    // Rest and focus come from the browser. Hover, active, disabled and checked
    // are resolved from the stylesheet: a rule that WOULD apply on hover is a
    // property of this page whether or not a pointer is over it, and driving a
    // real hover in a headless browser is far less reliable than reading the
    // rule that governs it.
    const PSEUDO = [":hover", ":active", ":disabled", ":checked", ":focus-visible", ":focus"];
    const styleRules = [];
    const collect = (rules) => {
        for (const rule of rules) {
            if (rule.cssRules) { collect(rule.cssRules); continue; }
            if (rule.selectorText && rule.style) styleRules.push(rule);
        }
    };
    for (const sheet of document.styleSheets) {
        try { collect(sheet.cssRules); } catch (e) { /* cross-origin: nothing to read */ }
    }
    const declaredFor = (el, pseudo) => {
        const out = [];
        for (const rule of styleRules) {
            if (rule.selectorText.indexOf(pseudo) === -1) continue;
            for (const part of rule.selectorText.split(",")) {
                if (part.indexOf(pseudo) === -1) continue;
                const bare = part.split(pseudo).join("").trim();
                if (!bare) continue;
                let hit = false;
                try { hit = el.matches(bare); } catch (e) { continue; }
                if (!hit) continue;
                for (const prop of PROPS) {
                    const v = rule.style.getPropertyValue(prop);
                    if (v) out.push([prop, v]);
                }
                // The custom properties Bootstrap composes its colours from.
                for (let i = 0; i < rule.style.length; i++) {
                    const name = rule.style[i];
                    if (name.startsWith("--")) out.push([name, rule.style.getPropertyValue(name)]);
                }
            }
        }
        return out;
    };

    const describe = (el) => el.tagName.toLowerCase()
        + (el.id ? "#" + el.id : "")
        + (el.className ? "." + String(el.className).trim().split(/\s+/).slice(0, 3).join(".") : "")
        + (el.type ? "[" + el.type + "]" : "");

    const foreign = [];
    let stateCount = 0;
    const audit = (controls, pass) => {
      for (const el of controls) {
        const name = describe(el);
        const states = {};
        const cs = getComputedStyle(el);
        states.rest = PROPS.map(p => [p, cs.getPropertyValue(p)]);
        try {
            el.focus({preventScroll: true});
            const fs = getComputedStyle(el);
            states.focus = PROPS.map(p => [p, fs.getPropertyValue(p)]);
            el.blur();
        } catch (e) { states.focus = []; }
        for (const pseudo of PSEUDO) states[pseudo.slice(1)] = declaredFor(el, pseudo);
        for (const [state, decls] of Object.entries(states)) {
            stateCount += 1;
            const bad = [];
            for (const [prop, value] of decls) {
                for (const hex of coloursIn(value, el)) {
                    if (!allowed(hex)) bad.push(hex + " via " + prop);
                }
            }
            const verdict = bad.length ? "FOREIGN " + [...new Set(bad)].join(" ; ") : "ok";
            console.log("SAPIAN-CONTROL " + location.pathname + " [" + pass + "] | "
                + name + " | " + state + " | " + verdict);
            if (bad.length) foreign.push(pass + " " + name + " @" + state + ": " + [...new Set(bad)].join(" ; "));
        }
      }
    };
    audit(controls, "as-rendered");

    // The login form is hidden behind the user switcher when the switcher
    // renders. Reveal it — this is what "Use another user" does — and audit the
    // controls that were behind it.
    const hidden = document.querySelector("form.oe_login_form.d-none");
    let revealed = 0;
    if (hidden) {
        hidden.classList.remove("d-none");
        await sleep(100);
        const more = [...document.querySelectorAll(SELECTOR)].filter(visible)
            .filter(e => !controls.includes(e));
        revealed = more.length;
        audit(more, "form-revealed");
    }

    // COUNTED INSIDE THE SWITCHER'S OWN HOST, and this is not fussiness.
    // The first version counted `.list-group-item-action` anywhere on the page
    // and was satisfied by `a.passkey_login_link.list-group-item-action` — a
    // passkey link that happens to carry the same Bootstrap class. The user
    // switcher had not rendered at all, and the assertion written to catch
    // exactly that reported success. Scope it to the component's host element.
    const switcherHost = document.querySelector("owl-component[name='web.user_switch']");
    const switcherIn = () => switcherHost
        ? switcherHost.querySelectorAll(".list-group-item-action, .o_user_switch_btn").length
        : 0;
    // "Choose a user" collapses to a single button when only one user is
    // remembered. Click it — that is `toggleFormDisplay` — so the list rows
    // render and get audited too, rather than depending on the localStorage
    // seed winning its race with user.js clearing it.
    const collapsed = switcherHost && switcherHost.querySelector(".o_user_switch_btn");
    if (collapsed) {
        collapsed.click();
        await sleep(250);
        const expanded = [...document.querySelectorAll(SELECTOR)].filter(visible)
            .filter(e => !controls.includes(e));
        if (expanded.length) audit(expanded, "switcher-expanded");
    }
    const switcherControls = switcherIn();
    console.log("SAPIAN-CONTROL-SUMMARY path=" + location.pathname
        + " controls=" + controls.length + " revealed=" + revealed
        + " states=" + stateCount + " foreign=" + foreign.length
        + " switcher_controls=" + switcherControls);
    if (!controls.length) {
        console.error("SAPIAN-CONTROL no interactive controls were enumerated at all");
        return;
    }
    // THE COVERAGE ASSERTION. The operator's build shows "Choose a user", so
    // that control exists and must be covered. If the seed did not take, this
    // guard would quietly audit a page missing the very controls it was
    // widened for — a smaller version of the defect it exists to catch.
    if (location.pathname === "/web/login" && switcherControls === 0) {
        console.error("SAPIAN-CONTROL the stored-user switcher rendered no controls of its "
            + "own, so 'Choose a user' was not audited. This run proves nothing about it.");
        return;
    }
    if (foreign.length) {
        console.error("SAPIAN-CONTROL " + foreign.length
            + " control state(s) wear a colour outside the palette: " + foreign.join(" || "));
        return;
    }
    console.log("test successful");
})();
"""


@tagged("post_install", "-at_install", "-standard", "sapian_palette")
class TestEveryControlIsInThePalette(AuthPageCase):
    """Reads what every control COMPUTES, in every state, and fails on a
    colour that is not ours.

    Tagged out of `standard` and selected by the bare `sapian_palette` tag
    because `browser_js` raises `SkipTest` when no Chrome is present, and a
    skip is a success signal produced by doing nothing. The
    `auth-controls-palette` CI job selects this tag AND greps for the
    `SAPIAN-CONTROL-SUMMARY` line, so a skipped run cannot pass — which is
    exactly what was missing before: the tag existed and nothing selected it.
    """

    def palette(self):
        """Every colour a control is allowed to wear, from the palette file."""
        primary = brand.brand_primary()
        return [
            primary.lower(),
            brand.brand_secondary().lower(),
            brand.tint(primary, 0.9).lower(),
        ]

    # SEEDING HAPPENS IN `ready`, WHICH IS NOT A TRICK BUT THE ONLY MOMENT.
    #
    # `browser_js` builds a fresh Chrome per call, so a previous call cannot
    # leave anything in localStorage, and `UserSwitch.setup()` reads the list
    # once at mount — after which writing it changes nothing. `ready` is polled
    # from before the page is interactive, so the write lands first and the
    # component mounts with two users. The expression still reports readiness;
    # the comma operator keeps both halves.
    SEED_AND_READY = (
        "(window.localStorage.setItem('web.lastConnectedUser', JSON.stringify(["
        "{login:'admin',name:'Mitchell Admin',partnerId:3,"
        "partnerWriteDate:'2026-01-01 00:00:00',userId:2},"
        "{login:'demo',name:'Marc Demo',partnerId:4,"
        "partnerWriteDate:'2026-01-01 00:00:00',userId:6}])), "
        "!!document.querySelector('form button[type=submit]'))"
    )

    def test_no_control_computes_a_colour_outside_the_palette(self):
        code = CONTROL_COLOURS_JS % {"brand": json.dumps(self.palette())}
        for route in self.auth_routes():
            self.browser_js(route, code, self.SEED_AND_READY)
