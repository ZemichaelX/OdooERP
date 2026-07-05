# -*- coding: utf-8 -*-
"""Golden tests for the pharma demo tenant: the provisioning is exercised with
a throwaway company name inside the test transaction, and every number the
pitch relies on is asserted hand-computed."""

from odoo.tests import TransactionCase, tagged

TEST_COMPANY_NAME = "Tena Pharma Test Co"


@tagged("post_install", "-at_install")
class TestDemoPharma(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["sapian.demo.pharma"]._provision_demo_pharma(
            company_name=TEST_COMPANY_NAME
        )
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))

    def _lot(self, name):
        lot = self.env["stock.lot"].search(
            [("name", "=", name), ("company_id", "=", self.company.id)]
        )
        self.assertEqual(len(lot), 1, f"exactly one demo lot {name}")
        return lot

    def test_provisioning_idempotent(self):
        """A second run returns the same company and creates nothing new."""
        products_before = self.env["product.product"].search_count(
            [("company_id", "=", self.company.id)]
        )
        again = self.env["sapian.demo.pharma"]._provision_demo_pharma(
            company_name=TEST_COMPANY_NAME
        )
        self.assertEqual(again, self.company)
        self.assertEqual(
            self.env["product.product"].search_count([("company_id", "=", self.company.id)]),
            products_before,
        )

    def test_medicines_disciplined_and_long_lived(self):
        """Six pharma medicines, lot-tracked, with the 730-day shelf life that
        keeps a live pitch receive from creating an instantly-expired lot."""
        medicines = self.env["product.product"].search(
            [("company_id", "=", self.company.id), ("is_pharma", "=", True)]
        )
        self.assertEqual(len(medicines), 6)
        for medicine in medicines:
            self.assertEqual(medicine.tracking, "lot")
            self.assertTrue(medicine.use_expiration_date)
            self.assertEqual(medicine.expiration_time, 730)

    def test_batches_cover_all_three_stages(self):
        """Fresh import stock, CO-88 nearing (+45 in a 90-day horizon), OR-15
        expired (−10)."""
        self.assertEqual(self._lot("B-124").pharma_state, "fresh")
        self.assertEqual(self._lot("CO-88").pharma_state, "nearing_expiry")
        self.assertEqual(self._lot("OR-15").pharma_state, "expired")

    def test_digest_activity_fired(self):
        """The pitch shows the alert itself: one activity anchored on the most
        urgent batch (OR-15), listing the nearing and expired batches only."""
        ors = self._lot("OR-15")
        activity = self.env["mail.activity"].search(
            [("res_model", "=", "stock.lot"), ("res_id", "=", ors.id)]
        )
        self.assertEqual(len(activity), 1)
        note = str(activity.note)
        self.assertIn("CO-88", note)
        self.assertIn("OR-15", note)
        self.assertNotIn("B-123", note)
        self.assertTrue(self._lot("CO-88").pharma_alerted)

    def test_dossier_landed_cost_and_traceability(self):
        """IMP/... dossier golden: 1,850,000 + 210,000 + 396,500 + 55,000 =
        2,511,500 ETB; every fresh batch traces to it, ageing stock does not."""
        dossier = self.env["pharma.import.dossier"].search(
            [("company_id", "=", self.company.id)]
        )
        self.assertEqual(len(dossier), 1)
        self.assertTrue(dossier.name.startswith("IMP/"))
        self.assertEqual(dossier.amount_total, 2511500)
        self.assertEqual(dossier.status, "received")
        for batch in ("B-123", "B-124", "PC-501", "MF-77", "AM-12"):
            self.assertIn(self._lot(batch), dossier.lot_ids)
        for batch in ("CO-88", "OR-15"):
            self.assertNotIn(self._lot(batch), dossier.lot_ids)
        self.assertEqual(self._lot("B-123")._pharma_dossiers(), dossier)

    def test_recall_golden_b123(self):
        """B-123 recall: exactly Hiwot (120, oldest) and Kadisco (80), with
        phone + city; Bethel only ever received B-124 — precision by exclusion.
        FEFO golden built in: Bethel's 60 came from B-124 because B-123 was
        exhausted."""
        lines = self._lot("B-123")._pharma_recall_lines()
        self.assertEqual(len(lines), 2)
        customers = lines.picking_id.partner_id
        self.assertEqual(lines[0].picking_id.partner_id.city, "Addis Ababa")
        self.assertEqual(lines[0].quantity, 120)
        self.assertEqual(lines[1].picking_id.partner_id.city, "Adama")
        self.assertEqual(lines[1].quantity, 80)
        self.assertTrue(all(p.phone for p in customers), "recall means calling people")
        self.assertNotIn("Bethel", "".join(customers.mapped("name")))
        self.assertLess(lines[0].date, lines[1].date, "different dates, oldest first")

        b124_lines = self._lot("B-124")._pharma_recall_lines()
        self.assertEqual(len(b124_lines), 1)
        self.assertIn("Bethel", b124_lines.picking_id.partner_id.name)
        self.assertEqual(b124_lines.quantity, 60)

    def test_company_ready_for_pitch(self):
        """ETB company, admin can switch into it, warehouse in place."""
        self.assertEqual(self.company.currency_id, self.env.ref("base.ETB"))
        self.assertIn(
            self.company,
            self.env.ref("base.user_admin").company_ids,
        )
        self.assertTrue(
            self.env["stock.warehouse"].search_count([("company_id", "=", self.company.id)])
        )
        self.assertEqual(self.company.pharma_expiry_alert_days, 90)
