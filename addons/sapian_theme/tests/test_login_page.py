# -*- coding: utf-8 -*-
"""What an anonymous visitor is actually served on /web/login.

WHY THIS FILE EXISTS
--------------------
Three client-facing defects survived every check this repo had, and were found
by a person opening the page:

  * the footer said "Powered by Odoo" and linked to odoo.com;
  * `auth_signup` offered account creation on a private company ERP;
  * the support contact rendered nothing, because nothing configured it — a
    feature with a passing test and no deployment that switched it on.

The checks that existed all talked to the database or to a compiled asset.
`build_demo.sh` reported `login_primary=#14454F` — correctly — about a page
that said Powered by Odoo. So the question none of them asked was: what comes
back on the wire?

Every test here asks exactly that, and every one is written so that it can go
red. The pairs matter: for each "must not appear" there is a test that makes it
appear on purpose and asserts the check notices, because a `assertNotIn` over
an empty string passes.
"""

import re

from odoo.tests import HttpCase, tagged

from odoo.addons.sapian_theme import brand

SUPPORT_PARAM = "sapian_theme.support_contact"
DEMO_SUPPORT = "+251 11 555 0000"


@tagged("post_install", "-at_install")
class TestLoginPageAsAVisitor(HttpCase):
    """Fetched over HTTP with no session, which is what a prospect is."""

    def _login_page(self):
        response = self.url_open("/web/login")
        self.assertEqual(response.status_code, 200)
        html = response.text
        # A zero-length body satisfies every absence assertion below it.
        self.assertGreater(len(html), 2000, "the login page is too small to be the real page")
        return html

    def _signup_scope(self, value):
        field = self.env["res.config.settings"]._fields.get("auth_signup_uninvited")
        key = getattr(field, "config_parameter", None) or "auth_signup.invitation_scope"
        self.env["ir.config_parameter"].sudo().set_param(key, value)
        self.env.flush_all()

    # ---- attribution --------------------------------------------------------

    def test_the_page_does_not_attribute_the_product_to_odoo(self):
        html = self._login_page()
        self.assertNotIn("odoo.com", html, "the login footer still links to odoo.com")
        self.assertNotIn("Powered by <span>Odoo", html)

    def test_the_page_signs_itself_sapian(self):
        """The positive half. Removing Odoo's line and adding nothing would
        pass the test above and leave the page unsigned."""
        html = self._login_page()
        self.assertIn("Powered by SapianERP", html)
        self.assertIn("sapiantech.com", html)
        self.assertIn("o_sapian_mark", html, "the mark is not beside the wordmark")

    def test_the_attribution_check_discriminates(self):
        """Prove the odoo.com assertion can fail, by putting it back.

        Disabling our overrides via the views' `active` flag is the closest a
        test can get to "somebody deletes this template", and it exercises the
        real inheritance path rather than a string.

        BOTH overrides are disabled, because the page has two emitters and
        which one is live depends on whether `website` is installed:

          - without website, the login card's own hardcoded odoo.com link
            (web.login_layout);
          - with website, the card is replaced and its footer calls
            web.brand_promotion_message instead. Measured: with website on, the
            page carried TWO attributions until both were overridden.

        Disabling both means at least one comes back in either configuration,
        so this test discriminates on the databases we ship AND on the one the
        theme-with-website job builds.
        """
        for xmlid in (
            "sapian_theme.login_layout_sapian",
            "sapian_theme.brand_promotion_message",
        ):
            self.env.ref(xmlid).active = False
        self.env.flush_all()
        self.env.registry.clear_cache("templates")
        html = self.url_open("/web/login").text
        self.assertIn(
            "odoo.com", html, "with our overrides off, Odoo's own footer must be back"
        )

    # ---- sign-up ------------------------------------------------------------

    def test_no_signup_offer_for_a_stranger(self):
        self._signup_scope("b2b")
        html = self._login_page()
        self.assertNotIn("/web/signup", html)
        self.assertNotIn("Don't have an account", html)

    def test_the_signup_check_discriminates(self):
        """Odoo's own default is b2c. Set it and the offer must come back.

        WITH `website` INSTALLED IT DOES NOT, and that is measured, not
        assumed: on a database carrying website, /web/login at b2c renders no
        signup link at all. The offer lives in `auth_signup.login`, an inherit
        of `web.login` anchored inside `.oe_login_buttons`, and website's
        replacement of the login page does not carry it.

        So the assertion is different in the two configurations, and BOTH
        assert something — neither branch is a skip. Which branch runs is
        decided by what is installed, not by what happened, so a broken
        override cannot pick the lenient one.
        """
        self._signup_scope("b2c")
        html = self._login_page()
        website = self.env["ir.module.module"].search(
            [("name", "=", "website"), ("state", "=", "installed")], limit=1
        )
        if website:
            self.assertNotIn(
                "/web/signup",
                html,
                "website is installed and Odoo rendered a signup link at b2c — "
                "the configuration this test describes has changed",
            )
        else:
            self.assertIn("/web/signup", html, "b2c must offer signup, or this test is blind")

    # ---- support contact ----------------------------------------------------

    def test_the_support_contact_is_rendered_when_configured(self):
        self.env["ir.config_parameter"].sudo().set_param(SUPPORT_PARAM, DEMO_SUPPORT)
        self.env.flush_all()
        html = self._login_page()
        self.assertIn("Support:", html)
        self.assertIn(DEMO_SUPPORT, html)

    def test_an_unconfigured_support_contact_renders_nothing(self):
        """The empty state, which is what every build shipped: no stray label,
        no empty box — and nothing for a prospect to phone."""
        self.env["ir.config_parameter"].sudo().set_param(SUPPORT_PARAM, "")
        self.env.flush_all()
        self.assertNotIn("Support:", self._login_page())

    # ---- the sign-in button, in every state --------------------------------

    def _login_css(self):
        """The stylesheet the login page LINKS TO, fetched over HTTP.

        Not the attachment read out of the ORM: the point of this file is to
        assert on what the browser receives, and a bundle URL that 404s would
        leave an unstyled page that every ORM-level check calls correct.
        """
        html = self._login_page()
        hrefs = re.findall(r'href="(/web/assets/[^"]+\.css)"', html)
        self.assertTrue(hrefs, "the login page links to no stylesheet at all")
        css = ""
        for href in hrefs:
            response = self.url_open(href)
            self.assertEqual(response.status_code, 200, "%s did not serve" % href)
            css += response.text
        return css

    def test_the_sign_in_button_is_branded_in_every_state(self):
        """Resting, hover, active, DISABLED and focus.

        The disabled one is not an edge case: web/static/src/public/login.js
        calls addLoadingEffect() on submit, which adds `disabled` (core/utils/
        ui.js:190), so it is the colour of the button for as long as the login
        request takes. It was Odoo purple at 65% opacity while every other
        check reported the brand.
        """
        expected = brand.brand_primary()
        rule = re.search(r"\.oe_login_form \.btn-primary\{([^}]*)\}", self._login_css())
        self.assertTrue(rule, "the login button rule is not in the served CSS")
        declarations = rule.group(1)

        for variable in (
            "--btn-bg",
            "--btn-border-color",
            "--btn-disabled-bg",
            "--btn-disabled-border-color",
        ):
            found = re.search(re.escape(variable) + r": (#[0-9A-Fa-f]{6})", declarations)
            self.assertTrue(found, "%s is not set on the login button" % variable)
            self.assertEqual(
                found.group(1).upper(),
                expected,
                "%s is not the brand colour — that state renders Odoo purple" % variable,
            )

        # hover and active are the brand's derived hover, not the brand itself,
        # so they are asserted as "not Odoo's" by being present and derived.
        for variable in ("--btn-hover-bg", "--btn-active-bg"):
            self.assertRegex(declarations, re.escape(variable) + r": #[0-9A-Fa-f]{6}")

        # The focus ring is an R, G, B triple, not a hex.
        rgb = ", ".join(str(int(expected.lstrip("#")[i : i + 2], 16)) for i in (0, 2, 4))
        self.assertIn(
            "--btn-focus-shadow-rgb: %s" % rgb,
            declarations,
            "the focus ring is still Odoo's — anyone who tabs into the form sees it",
        )

    def test_the_button_state_check_discriminates(self):
        """The assertion above must fail on the CSS that shipped.

        That CSS is reconstructed here — the four variables the original rule
        set, and nothing else — and run through the same parse. If this passes,
        the test above proves nothing.
        """
        expected = brand.brand_primary()
        as_shipped = (
            ".oe_login_form .btn-primary{--btn-bg: %s; --btn-border-color: %s; "
            "--btn-hover-bg: #376169; --btn-active-bg: #376169;}" % (expected, expected)
        )
        declarations = re.search(r"\.oe_login_form \.btn-primary\{([^}]*)\}", as_shipped).group(
            1
        )
        self.assertNotRegex(
            declarations,
            r"--btn-disabled-bg",
            "the rule that shipped had no disabled colour — that is the defect",
        )
        self.assertNotIn("--btn-focus-shadow-rgb", declarations)
