# -*- coding: utf-8 -*-
"""Integration tests for the pharma compliance core (batch discipline, FEFO,
expiry alerts, expired-delivery policy, GS1 scan capture).

Expiry dates are created RELATIVE to today so the escalation states are
deterministic against the default 90-day horizon regardless of wall clock:
today+200 = fresh, today+30 = nearing expiry, today−1 = expired.
"""

from datetime import datetime, time, timedelta

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPharmaCompliance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Dedicated company: independent from whatever demo/cleanup state the
        # database carries (stock auto-creates its warehouse in test mode).
        cls.company = cls.env["res.company"].create({"name": "Pharma Test Co"})
        cls.env.user.write({"company_ids": [(4, cls.company.id)], "company_id": cls.company.id})
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.customer = cls.env["res.partner"].create({"name": "Hiwot Pharmacy"})
        cls.supplier = cls.env["res.partner"].create({"name": "Global Pharma GmbH"})
        cls.medicine = cls.env["product.product"].create(
            {
                "name": "Amoxicillin 500mg — አሞክሲሲሊን",
                "type": "consu",
                "is_storable": True,
                "is_pharma": True,
            }
        )
        cls.today = fields.Date.context_today(cls.env["stock.lot"])

    @classmethod
    def _expiry(cls, days_from_today):
        return datetime.combine(cls.today + timedelta(days=days_from_today), time(12, 0))

    @classmethod
    def _receive(cls, lot_name, days_to_expiry, qty=10, set_expiry=True):
        """Receive ``qty`` of the medicine as ``lot_name`` via a real receipt."""
        picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.warehouse.in_type_id.id,
                "partner_id": cls.supplier.id,
                "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": cls.warehouse.lot_stock_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": cls.medicine.id,
                            "product_uom_qty": qty,
                            "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                            "location_dest_id": cls.warehouse.lot_stock_id.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        move = picking.move_ids
        move.move_line_ids.unlink()
        line = cls.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "picking_id": picking.id,
                "product_id": cls.medicine.id,
                "quantity": qty,
                "lot_name": lot_name,
                "expiration_date": cls._expiry(days_to_expiry) if set_expiry else False,
                "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": cls.warehouse.lot_stock_id.id,
            }
        )
        move.picked = True
        if not set_expiry:
            # product_expiry auto-fills the line's expiration date from the
            # product's expiration_time; force the field empty to reproduce a
            # user clearing it — the exact hole the receipt gate covers.
            line.expiration_date = False
        # skip_expired = the user confirming product_expiry's own popup when
        # receiving an already-expired batch.
        picking.with_context(skip_expired=True).button_validate()
        return cls.env["stock.lot"].search(
            [("name", "=", lot_name), ("product_id", "=", cls.medicine.id)]
        )

    def _delivery(self, qty=1, force_lot=None):
        """A confirmed outgoing picking for the medicine. Without ``force_lot``
        the reservation runs normally (FEFO). With it, the lot is put on a
        manual move line — Odoo refuses to reserve expired stock, so this is
        how an expired batch can end up on a delivery at all."""
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "partner_id": self.customer.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.medicine.id,
                            "product_uom_qty": qty,
                            "location_id": self.warehouse.lot_stock_id.id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        if force_lot:
            self.env["stock.move.line"].create(
                {
                    "move_id": picking.move_ids.id,
                    "picking_id": picking.id,
                    "product_id": self.medicine.id,
                    "quantity": qty,
                    "lot_id": force_lot.id,
                    "location_id": self.warehouse.lot_stock_id.id,
                    "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                }
            )
        else:
            picking.action_assign()
        return picking

    def test_pharma_flag_enforces_discipline(self):
        """is_pharma forces lot tracking, expiry dates and the FEFO category."""
        self.assertEqual(self.medicine.tracking, "lot")
        self.assertTrue(self.medicine.use_expiration_date)
        self.assertEqual(
            self.medicine.categ_id,
            self.env.ref("vertical_pharma.product_category_pharma"),
        )
        self.assertEqual(
            self.medicine.categ_id.removal_strategy_id,
            self.env.ref("product_expiry.removal_fefo"),
        )
        with self.assertRaises(ValidationError):
            self.medicine.product_tmpl_id.write(
                {"tracking": "none", "use_expiration_date": False}
            )

    def test_receipt_without_expiry_blocked(self):
        """Incoming pharma stock without an expiration date must not validate."""
        with self.assertRaisesRegex(UserError, "expiration date"):
            self._receive("LOT-NOEXP", 100, set_expiry=False)

    def test_lot_states_golden(self):
        """today+200 fresh · today+30 nearing (90-day horizon) · today−1 expired."""
        fresh = self._receive("LOT-FRESH", 200)
        nearing = self._receive("LOT-NEAR", 30)
        expired = self._receive("LOT-EXP", -1)
        self.assertEqual(fresh.pharma_state, "fresh")
        self.assertEqual(nearing.pharma_state, "nearing_expiry")
        self.assertEqual(expired.pharma_state, "expired")

    def test_state_horizon_boundary(self):
        """Exactly horizon days out is nearing; one day beyond is fresh."""
        at_horizon = self._receive("LOT-H90", 90)
        beyond = self._receive("LOT-H91", 91)
        self.assertEqual(at_horizon.pharma_state, "nearing_expiry")
        self.assertEqual(beyond.pharma_state, "fresh")

    def test_fefo_picks_earliest_expiry(self):
        """FEFO golden: with lots at +200 and +50 days, the delivery reserves
        the +50 lot."""
        self._receive("LOT-LATE", 200)
        early = self._receive("LOT-EARLY", 50)
        picking = self._delivery(qty=1)
        reserved = picking.move_line_ids.lot_id
        self.assertEqual(reserved, early, "FEFO must reserve the earliest expiry")

    def test_expired_delivery_blocked_by_default(self):
        """An expired lot forced onto a delivery blocks validation (default
        policy) — with OUR message, not a side effect of core stock."""
        lot = self._receive("LOT-BLOCK", 5)
        lot.expiration_date = self._expiry(-1)
        picking = self._delivery(qty=1, force_lot=lot)
        picking.move_ids.picked = True
        with self.assertRaisesRegex(UserError, "expired batches"):
            picking.button_validate()

    def test_expired_delivery_warn_policy(self):
        """With policy 'warn' the delivery validates but carries an audit note."""
        self.company.pharma_expired_delivery_policy = "warn"
        self.addCleanup(self.company.write, {"pharma_expired_delivery_policy": "block"})
        lot = self._receive("LOT-WARN", 5)
        lot.expiration_date = self._expiry(-1)
        picking = self._delivery(qty=1, force_lot=lot)
        picking.move_ids.picked = True
        # skip_expired = the user confirming product_expiry's own popup.
        picking.with_context(skip_expired=True).button_validate()
        self.assertEqual(picking.state, "done")
        self.assertTrue(any("EXPIRED" in str(message.body) for message in picking.message_ids))

    def test_expiry_digest_one_activity_and_dedup(self):
        """The digest creates ONE activity listing nearing/expired lots with
        stock, marks them alerted, and never reports them twice."""
        self._receive("LOT-DIG-FRESH", 200)
        nearing = self._receive("LOT-DIG-NEAR", 30)
        expired = self._receive("LOT-DIG-EXP", -1)
        domain = [("res_model", "=", "stock.lot")]
        before = self.env["mail.activity"].search_count(domain)
        self.env["stock.lot"]._pharma_run_expiry_digest()
        activities = self.env["mail.activity"].search(domain, order="id desc")
        self.assertEqual(len(activities) - before, 1, "exactly one digest activity")
        self.assertEqual(activities[0].res_id, expired.id, "anchored on the most urgent batch")
        note = str(activities[0].note)
        self.assertIn("LOT-DIG-NEAR", note)
        self.assertIn("LOT-DIG-EXP", note)
        self.assertNotIn("LOT-DIG-FRESH", note)
        self.assertTrue(nearing.pharma_alerted)
        self.assertTrue(expired.pharma_alerted)
        after_first = self.env["mail.activity"].search_count(domain)
        self.env["stock.lot"]._pharma_run_expiry_digest()
        self.assertEqual(
            self.env["mail.activity"].search_count(domain),
            after_first,
            "digest must not repeat already-alerted lots",
        )

    def test_gs1_scan_fills_lot_and_expiry(self):
        """Scanning 01+17+10 fills the lot name and expiration date and clears
        the scan buffer; a mis-scan warns and fills nothing."""
        line = self.env["stock.move.line"].new(
            {"product_id": self.medicine.id, "company_id": self.company.id}
        )
        line.pharma_gs1_scan = "010950110153000317260925" + "10B-123"
        result = line._onchange_pharma_gs1_scan()
        self.assertIsNone(result)
        self.assertEqual(line.lot_name, "B-123")
        self.assertEqual(str(line.expiration_date.date()), "2026-09-25")
        self.assertFalse(line.pharma_gs1_scan)

        bad = self.env["stock.move.line"].new({"product_id": self.medicine.id})
        bad.pharma_gs1_scan = "99garbage"
        result = bad._onchange_pharma_gs1_scan()
        self.assertIn("warning", result)
        self.assertFalse(bad.lot_name)
