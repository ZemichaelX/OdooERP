# -*- coding: utf-8 -*-
"""The favicon and the default logo reach `res.company` RECORDS.

WHY THIS IS SEPARATE FROM THE FAST TEST
---------------------------------------
`tests_fast/test_every_brand_display_point.py` proves the FILES exist and are
ours. That is necessary and not sufficient: both of these live on records, and
a file nobody writes to a record is a file nobody sees.

INSTALL AND UPGRADE ARE PROVED SEPARATELY, and that is the whole point of this
file. It is the same split `sapian_theme_mail` documents for the bot's name: a
`post_init_hook` runs on install and never on `-u`, so a tenant that already has
this module would keep Odoo's purple favicon in every browser tab forever while
a freshly installed one looked correct. Asserting one path and assuming the
other is how that defect ships.

  * install  — `post_init_hook`, exercised by this module being installed at
               all, and asserted here against the database it produced.
  * upgrade  — `migrations/19.0.2.2.0/end-brand_assets.py`, exercised by the
               `brand-assets-survive-upgrade` CI job which runs `-u
               sapian_theme` against a database where the assets have been
               deliberately reset to Odoo's, and asserted by
               `test_the_upgrade_path_rewrites_a_reset_company`.
  * later    — a company created AFTER install, covered by the `create`
               override and asserted here. Multi-company is a requirement of
               this product, and a second company is exactly the case a data
               file cannot reach.
"""

import base64

from odoo.tests import TransactionCase, tagged
from odoo.tools import file_open

from ..models.res_company import FAVICON, LOGO


def _asset(path):
    with file_open(path, "rb") as handle:
        return base64.b64encode(handle.read())


@tagged("post_install", "-at_install")
class TestBrandAssets(TransactionCase):
    def test_every_company_carries_our_favicon(self):
        """Not "the field is set" — the field equals OUR bytes.

        Odoo ships its own favicon as the column default, so a non-empty
        favicon is a success signal that a completely unbranded database also
        produces.
        """
        ours = _asset(FAVICON)
        wrong = (
            self.env["res.company"]
            .sudo()
            .search([])
            .filtered(lambda company: company.favicon != ours)
        )
        self.assertFalse(
            wrong,
            "companies still serving a favicon that is not ours: %s"
            % wrong.mapped("display_name"),
        )

    def test_a_company_created_after_install_gets_them_too(self):
        """The case a data file cannot reach."""
        company = self.env["res.company"].create({"name": "Brand Asset Latecomer"})
        self.assertEqual(
            company.favicon,
            _asset(FAVICON),
            "a company created after install kept Odoo's favicon",
        )
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
        company.sudo().write({"favicon": False})
        self.assertNotEqual(company.favicon, _asset(FAVICON))
        written = self.env["res.company"]._sapian_apply_brand_assets(company)
        self.assertEqual(written, 1, "the reset company was not rewritten")
        self.assertEqual(company.favicon, _asset(FAVICON))

    def test_a_client_logo_is_never_overwritten(self):
        """The logo is THEIRS. Only the favicon is ours unconditionally.

        A client who uploads their own logo through onboarding must keep it
        through every upgrade, or this module is vandalising their invoices.
        """
        company = self.env["res.company"].create({"name": "Brand Asset Client"})
        theirs = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"not our mark, but theirs" * 40)
        company.sudo().write({"logo": theirs})
        self.env["res.company"]._sapian_apply_brand_assets(company)
        self.assertEqual(company.logo, theirs, "the client's own logo was overwritten by ours")
