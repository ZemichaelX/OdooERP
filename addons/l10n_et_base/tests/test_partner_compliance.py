# -*- coding: utf-8 -*-
"""Integration tests for the Ethiopian partner compliance fields."""

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import L10nEtBaseCommon


@tagged("post_install", "-at_install")
class TestPartnerCompliance(L10nEtBaseCommon):
    def test_tin_normalized_on_create(self):
        """A TIN typed with separators is stored as the bare 10 digits."""
        partner = self.env["res.partner"].create(
            {
                "name": "Hyphenated TIN Supplier",
                "l10n_et_tin": "0012-3456-78",
            }
        )
        self.assertEqual(partner.l10n_et_tin, "0012345678")

    def test_tin_normalized_on_write(self):
        self.partner_no_tin.write({"l10n_et_tin": " 00 9876 5432 "})
        self.assertEqual(self.partner_no_tin.l10n_et_tin, "0098765432")

    def test_invalid_tin_rejected(self):
        """Wrong length, letters and Unicode digits all fail the constraint."""
        for bad_tin in ("123456789", "00123A5678", "١٢٣٤٥٦٧٨٩٠"):
            with self.assertRaises(ValidationError, msg=bad_tin):
                self.env["res.partner"].create(
                    {
                        "name": "Bad TIN",
                        "l10n_et_tin": bad_tin,
                    }
                )

    def test_licence_validity_depends_on_expiry(self):
        """An expired licence counts as missing (drives the punitive WHT rate)."""
        self.assertTrue(self.partner_compliant.l10n_et_has_valid_licence)
        self.partner_compliant.l10n_et_business_licence_expiry = "2020-01-01"
        self.assertFalse(self.partner_compliant.l10n_et_has_valid_licence)
        self.assertFalse(self.partner_compliant.l10n_et_wht_compliant)

    def test_wht_compliant_needs_tin_and_licence(self):
        self.assertTrue(self.partner_compliant.l10n_et_wht_compliant)
        self.assertFalse(self.partner_no_tin.l10n_et_wht_compliant)

    def test_compliance_fields_propagate_to_contacts(self):
        """TIN/licence are commercial fields: a delivery contact of the company
        carries the company's identifiers (like core `vat`)."""
        contact = self.env["res.partner"].create(
            {
                "name": "Warehouse Contact",
                "parent_id": self.partner_compliant.id,
                "type": "delivery",
            }
        )
        self.assertEqual(contact.l10n_et_tin, "0011223344")
        self.assertEqual(contact.l10n_et_business_licence_no, "AA/1234/2016")

    def test_expired_licence_triggers_punitive_wht_on_bill(self):
        """End-to-end: expiring the licence flips the supplier to the punitive
        rate on the next bill."""
        self.partner_compliant.l10n_et_business_licence_expiry = "2020-01-01"
        bill = self._create_bill(self.partner_compliant, [(self.product_goods, 50000)])
        wht_lines = self._wht_lines(bill)
        self.assertEqual(wht_lines.tax_line_id.l10n_et_wht_kind, "punitive")
        self.assertEqual(wht_lines.credit, 15000.0)
