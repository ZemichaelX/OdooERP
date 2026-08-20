# -*- coding: utf-8 -*-
"""Public sign-up is closed, asserted from the page a stranger is served.

WHY NOT ASSERT THE SETTING
--------------------------
Because asserting the setting is the defect. `build_demo.sh` reported
`login_signup_scope=b2b` — correctly, the parameter did say b2b — about a
database whose `/web/login` offered "Don't have an account?" to anyone who
could reach it. The parameter had stopped being the authority the moment
`website` was installed, and the check kept reading it.

So every test here fetches `/web/login` and looks at what came back, and the
scope is only ever read through `_get_signup_invitation_scope()` — the method
the login controller itself calls (auth_signup/controllers/main.py:132) — never
through the parameter or the column that feed it.

AND THEY PROVE THEY CAN GO RED
------------------------------
`test_the_offer_returns_when_it_is_deliberately_allowed` puts the database in
exactly the state this module exists to prevent and asserts the offer comes
BACK. Without it, every assertion here would pass on a database where sign-up
was impossible for some unrelated reason — an Odoo version that dropped the
link, a template that stopped rendering — and the module would look effective
while doing nothing.
"""

from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.sapian_theme.models.res_users import ALLOW_PUBLIC_SIGNUP_PARAM

SIGNUP_HREF = "/web/signup"
SIGNUP_TEXT = "Don't have an account"


class PublicSignupCase:
    """Shared helpers. The website row is the thing website_sale rewrites."""

    def _set_websites(self, scope):
        websites = self.env["website"].sudo().search([])
        self.assertTrue(websites, "no website record, so this test measures nothing")
        websites.write({"auth_signup_uninvited": scope})
        self.env.flush_all()
        return websites

    def _allow(self, value):
        self.env["ir.config_parameter"].sudo().set_param(ALLOW_PUBLIC_SIGNUP_PARAM, value)
        self.env.flush_all()


@tagged("post_install", "-at_install")
class TestPublicSignupScope(TransactionCase, PublicSignupCase):
    """The resolution itself, through the method the controller calls."""

    def test_the_website_column_no_longer_decides(self):
        """This is the exact state website_sale's post-install hook leaves.

        `website_sale/__init__.py:15` writes 'b2c' to every website. Before
        this module that value was final, because
        `website/models/res_users.py:66` returns it without consulting
        anything else.
        """
        self._set_websites("b2c")
        self.assertEqual(
            self.env["res.users"]._get_signup_invitation_scope(),
            "b2b",
            "a website row at 'b2c' still opens public sign-up",
        )

    def test_we_are_above_website_in_the_mro(self):
        """The whole reason this module is a bridge rather than part of the theme.

        Neither `auth_signup` nor `website` calls super() in this method, so
        the highest class ends the chain. With the override placed in
        `sapian_theme` — which depends on base + web only — the MRO came out
        [website, auth_signup, sapian_theme] and our code was never reached.
        Asserting the ORDER rather than only the result means a future
        dependency change that silently demotes us fails here, with the reason,
        instead of quietly reopening sign-up.
        """
        defining = [
            klass.__module__
            for klass in type(self.env["res.users"]).mro()
            if "_get_signup_invitation_scope" in klass.__dict__
        ]
        self.assertTrue(defining, "nothing defines the method; the test is measuring nothing")
        self.assertEqual(
            defining[0],
            "odoo.addons.sapian_theme_website.models.res_users",
            "we are not the first to define _get_signup_invitation_scope "
            "(order was %s), so whoever is above us ends the chain and public "
            "sign-up is decided by somebody else" % defining,
        )

    def test_an_explicit_opt_in_gives_odoo_back(self):
        """A client who really does run a webshop must be able to say so."""
        self._set_websites("b2c")
        self._allow("1")
        self.assertEqual(self.env["res.users"]._get_signup_invitation_scope(), "b2c")

    def test_the_opt_in_is_off_by_default_and_strict(self):
        """Anything other than an explicit truthy value keeps sign-up closed.

        A parameter left at "", "0" or "false" — including one somebody set to
        turn the feature OFF — must not read as permission.
        """
        self._set_websites("b2c")
        for value in ("", "0", "false", "no", "off", "maybe"):
            self._allow(value)
            self.assertEqual(
                self.env["res.users"]._get_signup_invitation_scope(),
                "b2b",
                "%r was treated as permission to open public sign-up" % value,
            )

    def test_the_stored_row_is_left_alone_and_does_not_decide(self):
        """The stored value is NOT rewritten, and it is not the authority.

        An earlier version of this module normalised those rows in a
        post_init_hook, so Settings > Website would not read "Free sign up" on
        a tenant where sign-up is closed. It was removed because it cannot win:
        `website_sale`'s own post-install hook rewrites them, and in two of the
        three real install orders it runs after ours —

            fresh build, all in one run   website_sale's hook runs after ours
            tenant buys website_sale      our hook ran a year earlier
            bridge installed afterwards   ours runs after, and holds

        — which this test caught on `-i sapian_theme,website,website_sale`. A
        guarantee that holds only when modules happen to install in the right
        order is the class of thing this module exists to remove, so the write
        is gone and the override is the whole mechanism.

        The consequence is stated rather than hidden: the Website settings
        screen can read "Free sign up" while sign-up is invitation-only. That
        is a display inconsistency, not a hole — `check_login_page.py` prints
        both the stored rows (`login_signup_websites`) and the effective value
        (`login_signup_effective`) so the difference is visible to whoever
        looks.
        """
        self._allow("")
        websites = self._set_websites("b2c")
        self.assertEqual(
            set(websites.mapped("auth_signup_uninvited")),
            {"b2c"},
            "something rewrote the stored value; this module must not",
        )
        self.assertEqual(
            self.env["res.users"]._get_signup_invitation_scope(),
            "b2b",
            "the stored value decided the outcome, which is the defect",
        )


@tagged("post_install", "-at_install")
class TestPublicSignupOnTheWire(HttpCase, PublicSignupCase):
    """What a stranger is actually served."""

    def _login_page(self):
        response = self.url_open("/web/login")
        self.assertEqual(response.status_code, 200)
        html = response.text
        # A zero-length page satisfies every assertNotIn below it.
        self.assertGreater(len(html), 500, "the login page came back essentially empty")
        return html

    def test_no_signup_offer_with_a_website_at_b2c(self):
        self._set_websites("b2c")
        self._allow("")
        html = self._login_page()
        self.assertNotIn(SIGNUP_HREF, html)
        self.assertNotIn(SIGNUP_TEXT, html)

    def test_the_offer_returns_when_it_is_deliberately_allowed(self):
        """THE DISCRIMINATION PROOF.

        Puts the database in the state this module exists to prevent and
        asserts the offer comes back. Without this, the test above would pass
        on a database where the link could never render for reasons that have
        nothing to do with us.
        """
        self._set_websites("b2c")
        self._allow("1")
        html = self._login_page()
        self.assertIn(
            SIGNUP_HREF,
            html,
            "opting in did not bring the sign-up offer back, so the test above "
            "proves nothing about this module",
        )

    def test_exactly_one_attribution_on_the_login_page(self):
        """With `website` installed, /web/login used to carry TWO.

        `website.layout`'s footer calls `web.brand_promotion_message`, which
        sapian_theme overrides, and the login form carries its own attribution
        anchored in login_templates.xml. Measured before the fix: 2 on
        /web/login, 1 on /web/signup, 1 on /web/reset_password.

        The count is asserted at exactly one rather than "at least one",
        because both failure directions are real: two is the defect this
        replaced, and zero is an unsigned login page.
        """
        html = self._login_page()
        self.assertEqual(
            html.count("Powered by SapianERP"),
            1,
            "the login page carries %d attributions, not one"
            % html.count("Powered by SapianERP"),
        )

    def test_the_other_auth_pages_keep_theirs(self):
        """The suppression is scoped to /web/login and nothing else.

        `/web/signup` and `/web/reset_password` extend `web.login_layout` and
        not `web.login`. Scoping the suppression one character wider — a prefix
        on `/web/log` rather than an exact match — would leave both unsigned,
        which is why this test exists alongside the one above.

        WHERE THEIR ONE ATTRIBUTION COMES FROM CHANGED, and this test is what
        noticed. It used to be `brand_promotion_message`, rendered in the
        website footer that wrapped these pages. Removing that wrapper — the
        point of `views/login_layout.xml` — took their only signature with it
        and this assertion went red at 0. The attribution now lives in the
        login card's own footer (`sapian_theme/views/login_templates.xml`),
        which all three auth pages share, so the count is one again and is one
        with or without `website` installed.
        """
        self._allow("1")  # so /web/signup is reachable rather than redirected
        for path in ("/web/signup", "/web/reset_password"):
            html = self.url_open(path).text
            self.assertEqual(
                html.count("Powered by SapianERP"),
                1,
                "%s carries %d attributions, not one"
                % (path, html.count("Powered by SapianERP")),
            )
