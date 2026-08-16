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
