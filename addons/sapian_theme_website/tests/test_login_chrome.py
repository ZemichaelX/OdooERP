# -*- coding: utf-8 -*-
"""The login page is an application login, not a page of the client's website.

THE DEFECT THESE EXIST FOR
--------------------------
On a 36-app database with `website` installed — the product's own shipped
configuration — `/web/login` served our branded card wrapped in Odoo's default
marketing chrome: a "Your Logo" navbar with Shop / Events / Courses / Jobs /
Contact us, and a footer with "Useful Links", "We are a team of passionate
people...", info@yourcompany.example.com and +1 555-555-5556. That is the first
screen a prospect sees.

WHY NOTHING CAUGHT IT
---------------------
Every login assertion we had measured the CARD, and the card was correct:

    login_powered_sapian=1  login_mark=1  login_signup=0  login_primary=#14454F

All four still pass on the broken page. They describe the part we built; none
of them described the page we serve. Same family as the proxy rule and as the
sibling file's "assert the setting" mistake.

So these tests assert on the WHOLE response body, and they assert absence
structurally — no `<header`, no `<footer` anywhere in the document — rather
than hunting for the particular strings Odoo's default theme happens to use
today. A re-themed website would change "Useful Links"; it would not stop
emitting a header element.

ABSENCE IS A WEAK ASSERTION, SO IT IS NEVER ASSERTED ALONE
----------------------------------------------------------
"No header and no footer" is exactly what an error page, an empty response or
a broken template also produce. Every test below therefore pairs it with two
positives:

  * the page still IS the page — the login form, our mark, our attribution;
  * `test_the_website_itself_still_has_its_chrome` proves the same markers ARE
    present on `/`, so a run where website's header simply stopped rendering
    fails loudly instead of passing everything.
"""

from odoo.tests import HttpCase, tagged

# The structural markers. `<header` and `<footer` are what web.frontend_layout
# emits under `t-if="not no_header"` / `t-if="not no_footer"`, and what
# website.layout keeps (it edits them with position="attributes", it does not
# replace them). If either appears on an auth page, the layout that suppresses
# them is not being used.
CHROME_TAGS = ("<header", "<footer")

# Odoo's stock website content. Not the primary assertion — a client who edits
# their footer would drop these while keeping the defect — but pinned because
# these exact strings are what a prospect actually reads.
CHROME_TEXT = (
    "Useful Links",
    "info@yourcompany",
    "555-555-5556",
    "oe_website_login_container",
)

AUTH_ROUTES = ("/web/login", "/web/reset_password")


@tagged("post_install", "-at_install")
class TestLoginPageIsNotAWebsitePage(HttpCase):
    """The auth pages carry no website chrome, with `website` installed."""

    def _page(self, route):
        response = self.url_open(route)
        self.assertEqual(response.status_code, 200, "%s did not return a page at all" % route)
        html = response.text
        # A page that came back nearly empty would satisfy every "not in"
        # assertion below. Floor it first.
        self.assertGreater(
            len(html), 2000, "%s came back too small to be a rendered page" % route
        )
        return html

    def test_the_website_is_installed_or_this_file_proves_nothing(self):
        """The precondition, asserted rather than assumed.

        Every test here is about what happens WITH `website`. Run them on a
        database without it and they pass by describing a configuration that
        was never at risk — a green that means nothing.
        """
        self.assertIn(
            "website",
            self.env.registry._init_modules | {self.env.cr.dbname},
            "the `website` module is not in this registry",
        )
        self.assertTrue(
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", "website"), ("state", "=", "installed")]),
            "`website` is not installed, so these tests measure nothing",
        )

    def test_no_website_chrome_on_the_auth_pages(self):
        for route in AUTH_ROUTES:
            html = self._page(route)
            for marker in CHROME_TAGS:
                self.assertNotIn(
                    marker,
                    html,
                    "%s renders %s — it is wrapped in the website layout" % (route, marker),
                )
            for marker in CHROME_TEXT:
                self.assertNotIn(
                    marker,
                    html,
                    "%s carries the website's default content (%s)" % (route, marker),
                )

    def test_the_login_page_is_still_our_login_page(self):
        """The positive half. Absence of chrome is not the deliverable."""
        html = self._page("/web/login")
        for marker in ("oe_login_form", "o_sapian_mark", "Powered by"):
            self.assertIn(marker, html, "the login page lost %s along with the chrome" % marker)

    def test_the_website_itself_still_has_its_chrome(self):
        """THE CONTROL, and the reason the assertions above mean anything.

        If website's header and footer stopped rendering everywhere — a broken
        theme, a failed asset build, an Odoo change — every "no chrome"
        assertion would pass and this module would look like it was working.
        The marketing site must keep exactly what the login page must not have.
        """
        response = self.url_open("/")
        self.assertEqual(response.status_code, 200, "the website home did not render")
        html = response.text
        for marker in CHROME_TAGS:
            self.assertIn(
                marker,
                html,
                "the website home has no %s, so 'no %s on /web/login' proves "
                "nothing" % (marker, marker),
            )


@tagged("post_install", "-at_install")
class TestLoginLayoutDiscriminates(HttpCase):
    """And the check goes red the moment website's inheritance comes back.

    This is the defect itself, reproduced on purpose: reactivating
    `website.login_layout` is precisely the state master is in. Without this,
    the tests above would keep passing if our record silently stopped being
    applied — the guard would be decoration.
    """

    def test_reactivating_websites_inheritance_puts_the_chrome_back(self):
        view = self.env.ref("website.login_layout")
        self.assertFalse(
            view.active,
            "website.login_layout is active — this module's record did not apply",
        )

        before = self.url_open("/web/login").text
        self.assertNotIn("<header", before)

        view.sudo().active = True
        # QWeb caches the combined arch per view; without this the next fetch
        # is served from the cache and the test passes by not re-rendering.
        self.env.registry.clear_cache()
        self.env.flush_all()

        after = self.url_open("/web/login").text
        view.sudo().active = False
        self.env.registry.clear_cache()
        self.env.flush_all()

        self.assertIn(
            "<header",
            after,
            "reactivating website.login_layout did NOT put the chrome back, so "
            "deactivating it is not what removes it and this guard is measuring "
            "something else",
        )
        self.assertGreater(
            len(after),
            len(before),
            "the wrapped page was not larger than the bare one",
        )


@tagged("post_install", "-at_install")
class TestProtectedPageStillRenders(HttpCase):
    """The one website feature that shares this layout must keep working.

    `website.protected_403` — the password prompt for a protected website page
    — is `t-call="website.login_layout"`. Deactivating an extension removes its
    contribution, not the record, so the xmlid still resolves to the root
    view's combined arch. That is the theory; this is the measurement, and it
    is made over HTTP because a bare `_render` of that template fails for want
    of a request in EITHER state and would have told us nothing.
    """

    def test_a_password_protected_page_still_asks_for_its_password(self):
        page = self.env["website.page"].search([("url", "!=", "/")], limit=1)
        if not page:
            self.skipTest("no website.page on this database to protect")
        page.sudo().write({"visibility": "password"})
        page.view_id.sudo().visibility_password_display = "letmein"
        self.env.flush_all()

        response = self.url_open(page.url)
        self.assertEqual(
            response.status_code,
            403,
            "a password-protected page did not return 403",
        )
        self.assertIn(
            "password is required",
            response.text.lower(),
            "the protected-page prompt no longer renders its form",
        )
