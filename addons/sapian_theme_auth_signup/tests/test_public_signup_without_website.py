# -*- coding: utf-8 -*-
"""Sign-up is closed on a tenant that has no `website`, and closed by the PRODUCT.

THE CASE THIS COVERS, AND WHY IT WAS UNCOVERED
-----------------------------------------------
`sapian_theme_website` closes sign-up once `website` is installed. That is not
the tenant most clients get: the default module list in `provision_client.sh`
has no `website` at all. On that tenant the decision falls back to
`auth_signup`'s own parameter, whose Odoo default is **b2c — free sign-up** —
and the only thing setting it to b2b was phase 4 of a shell script, once, at
provisioning time.

So these tests do what the website ones do, one layer down: they put the
database in the state Odoo leaves it in, and assert the served answer is still
invitation-only.

THE SCOPE IS READ THROUGH THE METHOD THE CONTROLLER CALLS
----------------------------------------------------------
`res.users._get_signup_invitation_scope()` — `auth_signup/controllers/main.py`
resolves `signup_enabled` from it. Never through the parameter, which is the
thing that stopped being the authority once before.

AND THEY PROVE THEY CAN GO RED
-------------------------------
`test_the_offer_returns_when_it_is_deliberately_allowed` puts the database in
exactly the state this module exists to prevent and asserts sign-up comes BACK.
Without it every assertion here would pass on a database where sign-up was
impossible for some unrelated reason, and the module would look effective while
doing nothing.
"""

from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.sapian_theme.models.res_users import ALLOW_PUBLIC_SIGNUP_PARAM

SIGNUP_PARAM = "auth_signup.invitation_scope"
SIGNUP_HREF = "/web/signup"


class WithoutWebsiteCase:
    """Shared helpers.

    Every test here skips itself if `website` IS installed, and says so. The
    module under test is about the tenant that does not have it, and a silent
    pass on a database that does would be a test that never ran in either
    direction.
    """

    def _require_no_website(self):
        if "website" in self.env:
            self.skipTest(
                "website is installed on this database, so the no-website path "
                "cannot be exercised here; sapian_theme_website covers that case"
            )

    def _set_param(self, value):
        self.env["ir.config_parameter"].sudo().set_param(SIGNUP_PARAM, value)
        self.env.flush_all()

    def _allow(self, value):
        self.env["ir.config_parameter"].sudo().set_param(ALLOW_PUBLIC_SIGNUP_PARAM, value)
        self.env.flush_all()


@tagged("post_install", "-at_install")
class TestSignupScopeWithoutWebsite(TransactionCase, WithoutWebsiteCase):
    def test_odoos_own_default_does_not_open_the_tenant(self):
        """b2c is what Odoo ships. It must not be what a client is served."""
        self._require_no_website()
        self._set_param("b2c")
        self.assertEqual(
            self.env["res.users"]._get_signup_invitation_scope(),
            "b2b",
            "the parameter says b2c and the served scope agreed — a tenant that "
            "never ran the provisioner's phase 4 is open to the internet",
        )

    def test_an_unset_parameter_does_not_open_the_tenant(self):
        """A database nobody configured at all — a restored backup, say."""
        self._require_no_website()
        self.env["ir.config_parameter"].sudo().search([("key", "=", SIGNUP_PARAM)]).unlink()
        self.env.flush_all()
        self.assertEqual(self.env["res.users"]._get_signup_invitation_scope(), "b2b")

    def test_the_offer_returns_when_it_is_deliberately_allowed(self):
        """It DISCRIMINATES, and the escape hatch works.

        Without this, every assertion above would pass on a database where
        sign-up was impossible for an unrelated reason.
        """
        self._require_no_website()
        self._set_param("b2c")
        self._allow("1")
        self.assertEqual(
            self.env["res.users"]._get_signup_invitation_scope(),
            "b2c",
            "the opt-in did nothing, so the tests above prove only that "
            "something else is blocking sign-up",
        )

    def test_only_an_explicit_opt_in_counts(self):
        """A default that a typo switches off is not a default."""
        self._require_no_website()
        self._set_param("b2c")
        for value in ("0", "", "false", "no", "off", "yes please", "b2c"):
            with self.subTest(value=value):
                self._allow(value)
                expected = "b2c" if value in ("yes",) else "b2b"
                self.assertEqual(self.env["res.users"]._get_signup_invitation_scope(), expected)

    def test_we_are_not_the_first_to_define_the_method(self):
        """If auth_signup stops defining it, this override is decoration.

        The same guard `sapian_theme_website` carries, for the same reason: an
        override of a method nobody calls any more is a security control that
        silently stopped controlling anything.
        """
        defined_in = [
            klass.__module__
            for klass in type(self.env["res.users"]).mro()
            if "_get_signup_invitation_scope" in klass.__dict__
        ]
        self.assertGreater(
            len(defined_in),
            1,
            "we are the only definition of _get_signup_invitation_scope — "
            "auth_signup no longer provides one, so this module is overriding "
            "nothing and the scope it narrows may not be the scope in use: %s" % defined_in,
        )


@tagged("post_install", "-at_install")
class TestLoginPageWithoutWebsite(HttpCase, WithoutWebsiteCase):
    """What a stranger is actually served."""

    def test_the_login_page_does_not_offer_an_account(self):
        self._require_no_website()
        self._set_param("b2c")
        self.env.cr.flush()
        page = self.url_open("/web/login").text
        self.assertNotIn(
            SIGNUP_HREF,
            page,
            "the login page offers account creation to anonymous visitors",
        )

    def test_the_signup_page_itself_is_not_served(self):
        """Not just the link. The route is what a stranger would type."""
        self._require_no_website()
        self._set_param("b2c")
        self.env.cr.flush()
        response = self.url_open("/web/signup")
        self.assertEqual(
            response.status_code,
            404,
            "/web/signup rendered for an anonymous visitor on a tenant where "
            "sign-up is supposed to be invitation-only",
        )
