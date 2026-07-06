# -*- coding: utf-8 -*-
"""Regression tests for the Jul 2026 adversarial-review findings (pharma)."""

from datetime import datetime, time, timedelta

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPharmaReviewRegressions(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Pharma Regress Co"})
        cls.env.user.write({"company_ids": [(4, cls.company.id)], "company_id": cls.company.id})
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.supplier = cls.env["res.partner"].create({"name": "Global Pharma GmbH"})
        cls.medicine = cls.env["product.product"].create(
            {
                "name": "Amoxicillin 500mg",
                "type": "consu",
                "is_storable": True,
                "is_pharma": True,
            }
        )
        cls.today = fields.Date.context_today(cls.env["stock.lot"])

    @classmethod
    def _receive(cls, lot_name, days_to_expiry, qty=10):
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
        cls.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "picking_id": picking.id,
                "product_id": cls.medicine.id,
                "quantity": qty,
                "lot_name": lot_name,
                "expiration_date": datetime.combine(
                    cls.today + timedelta(days=days_to_expiry), time(12, 0)
                ),
                "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": cls.warehouse.lot_stock_id.id,
            }
        )
        move.picked = True
        picking.with_context(skip_expired=True).button_validate()
        return cls.env["stock.lot"].search(
            [("name", "=", lot_name), ("product_id", "=", cls.medicine.id)]
        )

    def test_cannot_unflag_pharma_with_existing_lots(self):
        """R3#4: un-flagging is_pharma while batches exist would drop them out
        of every expiry gate."""
        self._receive("LOT-A", 100)
        with self.assertRaises(ValidationError):
            self.medicine.product_tmpl_id.write({"is_pharma": False})

    def test_cannot_clear_expiration_on_pharma_lot(self):
        """R3#5: clearing a pharma lot's expiry would slip it past the delivery
        gate and out of the digest."""
        lot = self._receive("LOT-B", 100)
        with self.assertRaises(ValidationError):
            lot.expiration_date = False

    def test_alerted_resets_when_expiry_changed(self):
        """R3#6: a relabelled expiry re-arms the digest (pharma_alerted clears)
        so the batch can be reported again against the new date."""
        lot = self._receive("LOT-C", 30)  # nearing
        self.env["stock.lot"]._pharma_run_expiry_digest()
        self.assertTrue(lot.pharma_alerted)
        lot.expiration_date = datetime.combine(self.today + timedelta(days=400), time(12, 0))
        self.assertFalse(lot.pharma_alerted, "re-armed after expiry change")

    def test_expiry_local_date_helper(self):
        """R1#7: the expiry is read as a LOCAL date (the last usable day),
        not the raw UTC date."""
        lot = self._receive("LOT-D", 80)
        self.assertEqual(
            lot._pharma_expiry_local_date(),
            fields.Datetime.context_timestamp(lot, lot.expiration_date).date(),
        )
