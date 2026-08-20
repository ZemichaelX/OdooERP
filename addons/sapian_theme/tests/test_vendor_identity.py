# -*- coding: utf-8 -*-
"""The chrome signs itself SAPIAN, and a tenant cannot change that.

WHAT WAS WRONG
--------------
The backend footer read `res.company.name` and the tenant's
`sapian_theme.support_contact`. Measured on the demo tenant:

    © 2026 Selam General Trading PLC. All Rights Reserved.
    For Support: +251 11 123 4567 / support@selamtrading.example

Install it for Golbon Trading and it says Golbon. That is the login page's
"Powered by Odoo" defect pointed the other way — the product on screen is not
the product being sold — and the competitor gets this right: their footer
carries the CONSULTANCY's name and numbers.

WHY THE VALUES ARE CONSTANTS
----------------------------
`ir.config_parameter` was the obvious home and is the wrong one: Technical >
System Parameters is open to `base.group_system`, which on a client's own
database is the client. So is `res.company`. The brief is explicit that a
client editing their own company must not be able to change our footer, so the
values live in `sapian_theme/vendor.py` where only a release can move them.
The full reasoning is in that file.

The tests below are the proof, and they are written the way that matters: they
do not check that a constant equals itself. They put the tenant in the state
that used to change the footer — rename the company, set the support parameter
— and assert the served payload does not move.
"""

from odoo.tests import HttpCase, TransactionCase, tagged

from .. import vendor


@tagged("post_install", "-at_install")
class TestVendorFooterIsNotTheTenants(HttpCase):
    """A tenant cannot move our attribution by editing their own records.

    Fetched over HTTP rather than by calling `session_info()` directly:
    `web_tour` overrides it and reads `request`, which does not exist in a
    TransactionCase, so a direct call raises instead of returning a payload.
    Going through the endpoint is also what the browser does.
    """

    def setUp(self):
        super().setUp()
        self.authenticate("admin", "admin")

    def _session_info(self):
        response = self.url_open(
            "/web/session/get_session_info",
            data="{}",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["result"]

    def test_the_payload_carries_sapian_not_the_company(self):
        info = self._session_info()
        self.assertEqual(info["sapian_vendor_company"], vendor.SAPIAN_COMPANY)
        self.assertEqual(info["sapian_vendor_support"], vendor.SAPIAN_SUPPORT)
        # And it is genuinely NOT the tenant's, on a database where the two
        # differ — otherwise this would pass on a tenant that happened to be
        # called Sapian Technologies PLC.
        self.env.company.name = "Golbon Trading PLC"
        self.env.flush_all()
        self.assertNotEqual(
            self._session_info()["sapian_vendor_company"],
            self.env.company.name,
            "the footer still signs itself with the tenant's company name",
        )

    def test_the_payload_carries_the_product_name(self):
        """The fourth vendor key, added for `sapian_theme_mail`.

        Odoo's messaging menu offers "Install Odoo"; the bridge renames it, and
        it reads the product name from here rather than from a JS literal so a
        re-brand stays one edit in vendor.py. Asserted in THIS module because
        this is where the key is produced — a test living only in the bridge
        would leave the producer untested on a database without it.

        The tenant half matters as much as the value: this is the vendor's
        product name, and a client renaming their company must not touch it.
        """
        self.assertEqual(self._session_info()["sapian_vendor_product"], vendor.SAPIAN_PRODUCT)
        self.env.company.name = "Golbon Trading PLC"
        self.env.flush_all()
        self.assertEqual(
            self._session_info()["sapian_vendor_product"],
            vendor.SAPIAN_PRODUCT,
            "renaming the tenant's company moved the product name",
        )

    def test_renaming_the_company_does_not_move_the_footer(self):
        """THE DISCRIMINATION PROOF for the company half.

        This is the exact edit that used to change it: a client renaming their
        own company in Settings.
        """
        before = self._session_info()["sapian_vendor_company"]
        self.env.company.name = "Golbon Trading PLC"
        self.env.flush_all()
        self.assertEqual(
            self._session_info()["sapian_vendor_company"],
            before,
            "renaming the tenant's company changed our attribution",
        )
        self.assertEqual(before, vendor.SAPIAN_COMPANY)

    def test_the_tenant_support_parameter_does_not_move_the_footer(self):
        """THE DISCRIMINATION PROOF for the support half.

        `sapian_theme.support_contact` is the tenant's own number and still
        drives the LOGIN page. It must no longer reach the backend footer.
        """
        before = self._session_info()["sapian_vendor_support"]
        self.env["ir.config_parameter"].sudo().set_param(
            "sapian_theme.support_contact", "+1 555 NOT OURS"
        )
        self.env.flush_all()
        self.assertEqual(
            self._session_info()["sapian_vendor_support"],
            before,
            "the tenant's support parameter still reaches the backend footer",
        )
        self.assertEqual(before, vendor.SAPIAN_SUPPORT)

    def test_the_old_tenant_keys_are_gone(self):
        """The keys that carried the tenant's values must not linger.

        A component still reading `sapian_footer_company` would keep working
        and keep being wrong, which is how a half-finished rename survives.
        """
        info = self._session_info()
        for stale in ("sapian_footer_company", "sapian_support_contact"):
            self.assertNotIn(
                stale,
                info,
                "%s is still in session_info — something may still read it" % stale,
            )


@tagged("post_install", "-at_install")
class TestTheMarkIsTheCommittedLogo(TransactionCase):
    """Both renderings of the mark are the logo in brand/, path for path.

    There are two: `views/sapian_mark.xml` (server QWeb, used by the login page
    and the portal attribution) and the inline SVG in the sidebar header
    (`static/src/xml/app_rail.xml`), because an OWL template cannot `t-call` a
    server-side one. Two RENDERINGS, one source — and this asserts both against
    the committed file so neither can drift into a redrawing.

    brand/README.md: "Never recreate or trace them — a redrawn logo that looks
    close is worse than a missing one."
    """

    def _paths(self, text):
        import re

        return re.findall(r'<path[^>]*\bd="([^"]+)"', text)

    def test_both_renderings_match_the_committed_svg(self):
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[3]
        logo = (root / "brand" / "sapian-logo.svg").read_text(encoding="utf-8")
        expected = self._paths(logo)
        self.assertEqual(len(expected), 4, "brand/sapian-logo.svg no longer has four paths")

        module = pathlib.Path(__file__).resolve().parents[1]
        for name in (
            module / "views" / "sapian_mark.xml",
            module / "static" / "src" / "xml" / "app_rail.xml",
        ):
            found = self._paths(name.read_text(encoding="utf-8"))
            self.assertEqual(
                found,
                expected,
                "%s does not carry the committed logo's paths — a redrawn logo "
                "that looks close is worse than a missing one" % name.name,
            )


@tagged("post_install", "-at_install")
class TestVendorFooterOnTheWire(HttpCase):
    """And it reaches the page a user is actually served."""

    def test_the_session_a_browser_fetches_carries_sapian(self):
        self.authenticate("admin", "admin")
        self.env.company.name = "Golbon Trading PLC"
        self.env["ir.config_parameter"].sudo().set_param(
            "sapian_theme.support_contact", "+1 555 NOT OURS"
        )
        self.env.flush_all()

        html = self.url_open("/odoo").text
        self.assertGreater(len(html), 500, "the backend page came back empty")
        self.assertIn(vendor.SAPIAN_COMPANY, html)
        self.assertIn(vendor.SAPIAN_SUPPORT, html)
        # The tenant's values must not be what the footer is handed. Checked on
        # the session payload's own keys rather than on the whole page, because
        # the company name legitimately appears elsewhere in session_info.
        self.assertNotIn('"sapian_footer_company"', html)
        self.assertNotIn("+1 555 NOT OURS", html)
