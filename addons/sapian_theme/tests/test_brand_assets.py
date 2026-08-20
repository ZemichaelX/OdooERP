# -*- coding: utf-8 -*-
"""The favicon reaches the browser tab, and our logo reaches `res.company`.

WHY THIS IS SEPARATE FROM THE FAST TEST
---------------------------------------
`tests_fast/test_every_brand_display_point.py` proves the FILES exist and are
ours. That is necessary and not sufficient: a file nobody serves is a file
nobody sees.

TWO DELIVERY MECHANISMS, AND THEY ARE NOT INTERCHANGEABLE
---------------------------------------------------------
The first version of this module wrote BOTH assets to `res.company`, and could
not: **`res.company` has no `favicon` field in Odoo 19.** `logo`,
`uses_default_logo` and `primary_color` are on `base`'s res.company; the favicon
belongs to the `website` model. The write raised `AttributeError` inside
`post_init_hook`, the registry failed to load, and every CI job that installs
this module died in setup.

  * the favicon — a VIEW, `views/favicon.xml`, inheriting `web.layout` so the
    `x_icon` fallback in its <head> is ours instead of Odoo's. Reaching install
    and upgrade alike, because that is what loading a data file does. Asserted
    here by fetching a real page and reading the <link> the browser reads.
  * the logo — a RECORD, so it has the install-versus-upgrade split
    `sapian_theme_mail` documents for the bot's name: a `post_init_hook` runs on
    install and never on `-u`, so a tenant that already has this module would
    keep Odoo's stock logo forever while a freshly installed one looked correct.
    Asserting one path and assuming the other is how that defect ships.
      - install — `post_init_hook`, asserted here against the database it built.
      - upgrade — `migrations/19.0.2.2.0/end-brand_assets.py`, exercised by the
        `brand-assets` CI job's real `-u` against a database whose logo has been
        deliberately reset, and asserted here at the method level.
      - later   — a company created AFTER install, covered by the `create`
        override. Multi-company is a requirement of this product, and a second
        company is exactly the case a data file cannot reach.
"""

import base64
import re

from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import file_open

from ..models.res_company import LOGO

# A real 1x1 PNG. It has to decode: `logo` is related to `partner_id.image_1920`,
# an `fields.Image`, and Odoo runs every write through `ImageProcess`, which
# raises on bytes it cannot open. A plausible-looking blob with a PNG magic
# number is not an image.
A_CLIENTS_OWN_LOGO = (
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
    b"hQGAhKmMIQAAAABJRU5ErkJggg=="
)

OUR_FAVICON = "/sapian_theme/static/src/img/favicon.png"
ODOO_FAVICON = "/web/static/img/favicon.ico"


def _asset(path):
    with file_open(path, "rb") as handle:
        return base64.b64encode(handle.read())


@tagged("post_install", "-at_install")
class TestFaviconReachesTheTab(HttpCase):
    """Read the page the browser reads, not the view record behind it.

    Asserting that the `sapian_theme.favicon` view EXISTS would pass on a
    database where an xpath silently matched nothing — `web.layout` is upstream
    markup and can move. The served <head> cannot lie about it.
    """

    def _favicon_href(self, route):
        """The href of the <link> the browser actually follows.

        Extracted from the tag rather than substring-searched in the page: a
        bare `assertNotIn("/web/static/img/favicon.ico")` over 400 kB of
        webclient HTML answers a question about the whole document, not about
        the one element that decides what the tab shows.
        """
        page = self.url_open(route).text
        tag = re.search(r'<link[^>]*rel="shortcut icon"[^>]*>', page)
        self.assertTrue(tag, "%s served no favicon <link> at all" % route)
        href = re.search(r'href="([^"]+)"', tag.group(0))
        self.assertTrue(href, "the favicon <link> on %s has no href" % route)
        return href.group(1)

    def test_the_backend_serves_our_favicon(self):
        """The tab a client's staff have open all day.

        Unconditional, unlike the login page below: `website` brands the
        FRONTEND head and never the backend one, so nothing else can be setting
        `x_icon` here.
        """
        self.authenticate("admin", "admin")
        self.assertEqual(
            self._favicon_href("/odoo"),
            OUR_FAVICON,
            "the backend tab is not wearing our favicon",
        )

    def test_the_login_page_favicon_is_never_odoos(self):
        """Two correct answers here, and Odoo's icon is neither of them.

        With `website` installed, /web/login renders inside the website layout,
        which sets `x_icon` from `website.favicon` — the client's own, and ours
        to leave alone. Without it, the fallback is reached and must be ours.
        Branching rather than skipping: a skip is a test that proves nothing on
        exactly the database it was written for.
        """
        href = self._favicon_href("/web/login")
        self.assertNotEqual(href, ODOO_FAVICON, "the login page still serves Odoo's icon")
        website = (
            self.env["ir.module.module"]
            .sudo()
            .search_count([("name", "=", "website"), ("state", "=", "installed")])
        )
        if website:
            self.assertTrue(
                href.startswith("/web/image/website"),
                "with `website` installed the login favicon should be the "
                "client's own website favicon, got %r" % href,
            )
        else:
            self.assertEqual(href, OUR_FAVICON)

    def test_the_favicon_file_is_actually_served(self):
        """A correct href to a 404 is still Odoo's icon in the tab."""
        response = self.url_open(OUR_FAVICON)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.content.startswith(b"\x89PNG\r\n\x1a\n"),
            "the favicon route did not return a PNG",
        )


@tagged("post_install", "-at_install")
class TestBrandAssets(TransactionCase):
    def test_no_company_is_left_on_odoos_stock_logo(self):
        """`uses_default_logo` IS the question, and it is Odoo's own answer.

        Not "the logo equals ours": a client who uploaded their own is correct
        and must not be flagged. What must not survive install is a company
        still wearing the stock image nobody chose.
        """
        companies = self.env["res.company"].sudo().search([])
        self.assertTrue(companies, "no company to check — this proves nothing")
        stock = companies.filtered(lambda company: company.uses_default_logo)
        self.assertFalse(
            stock,
            "companies still carrying Odoo's stock logo: %s" % stock.mapped("display_name"),
        )

    def test_a_company_created_after_install_gets_it_too(self):
        """The case a data file cannot reach."""
        company = self.env["res.company"].create({"name": "Brand Asset Latecomer"})
        self.assertEqual(
            company.logo,
            _asset(LOGO),
            "a company created after install kept Odoo's stock logo",
        )

    def test_the_upgrade_path_rewrites_a_reset_company(self):
        """The migration's own logic, driven directly.

        The CI job runs the real `-u`; this proves the method it calls does the
        work, so a failure there is a failure of the migration wiring rather
        than of the code it wires up.
        """
        company = self.env["res.company"].create({"name": "Brand Asset Reset"})
        company.sudo().write({"logo": False})
        self.assertNotEqual(company.logo, _asset(LOGO))
        written = self.env["res.company"]._sapian_apply_default_logo(company)
        self.assertEqual(written, 1, "the reset company was not rewritten")
        self.assertEqual(company.logo, _asset(LOGO))

    def test_a_client_logo_is_never_overwritten(self):
        """The logo is THEIRS.

        A client who uploads their own logo through onboarding must keep it
        through every upgrade, or this module is vandalising their invoices.
        """
        company = self.env["res.company"].create({"name": "Brand Asset Client"})
        company.sudo().write({"logo": A_CLIENTS_OWN_LOGO})
        self.assertFalse(
            company.uses_default_logo,
            "the fixture did not take, so this test cannot discriminate",
        )
        written = self.env["res.company"]._sapian_apply_default_logo(company)
        self.assertEqual(written, 0, "we wrote to a company that had chosen its own logo")
        self.assertNotEqual(
            company.logo, _asset(LOGO), "the client's own logo was overwritten by ours"
        )
