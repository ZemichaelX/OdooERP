# -*- coding: utf-8 -*-
"""Import dossier linkage + recall report goldens.

Recall golden (hand-computed): batch B-123 is delivered to TWO customers on
different dates with different quantities (Hiwot 40 then Kadisco 25 = 65 of
the 100 received); Bethel Clinic receives batch B-124 only — the recall of
B-123 must list exactly Hiwot and Kadisco (with phone + city, that is what a
recall is for) and must NOT list Bethel: precision by exclusion.
"""

from datetime import datetime, time, timedelta

from odoo import Command, fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPharmaDossierRecall(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Pharma Recall Test Co"})
        cls.env.user.write({"company_ids": [(4, cls.company.id)], "company_id": cls.company.id})
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.supplier = cls.env["res.partner"].create({"name": "Global Pharma GmbH"})
        cls.hiwot = cls.env["res.partner"].create(
            {"name": "Hiwot Pharmacy", "phone": "+251 11 123 4567", "city": "Addis Ababa"}
        )
        cls.kadisco = cls.env["res.partner"].create(
            {"name": "Kadisco Pharmacy", "phone": "+251 22 555 8899", "city": "Adama"}
        )
        cls.bethel = cls.env["res.partner"].create(
            {"name": "Bethel Clinic", "phone": "+251 46 220 7711", "city": "Hawassa"}
        )
        cls.medicine = cls.env["product.product"].create(
            {
                "name": "Amoxicillin 500mg — አሞክሲሲሊን",
                "type": "consu",
                "is_storable": True,
                "is_pharma": True,
            }
        )
        cls.today = fields.Date.context_today(cls.env["stock.lot"])
        cls.b123 = cls._receive("B-123", 200, qty=100)
        cls.b124 = cls._receive("B-124", 300, qty=50)

    @classmethod
    def _expiry(cls, days_from_today):
        return datetime.combine(cls.today + timedelta(days=days_from_today), time(12, 0))

    @classmethod
    def _receive(cls, lot_name, days_to_expiry, qty):
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
        cls.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "picking_id": picking.id,
                "product_id": cls.medicine.id,
                "quantity": qty,
                "lot_name": lot_name,
                "expiration_date": cls._expiry(days_to_expiry),
                "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": cls.warehouse.lot_stock_id.id,
            }
        )
        move.picked = True
        picking.button_validate()
        return cls.env["stock.lot"].search(
            [("name", "=", lot_name), ("product_id", "=", cls.medicine.id)]
        )

    @classmethod
    def _deliver(cls, partner, qty, days_ago, force_lot=None):
        """A done delivery to ``partner``; FEFO reserves unless a lot is forced.
        The line date is back-dated so recall rows carry distinct dates."""
        picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.warehouse.out_type_id.id,
                "partner_id": partner.id,
                "location_id": cls.warehouse.lot_stock_id.id,
                "location_dest_id": cls.env.ref("stock.stock_location_customers").id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": cls.medicine.id,
                            "product_uom_qty": qty,
                            "location_id": cls.warehouse.lot_stock_id.id,
                            "location_dest_id": cls.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        if force_lot:
            picking.move_line_ids.lot_id = force_lot
        picking.move_ids.picked = True
        picking.button_validate()
        picking.move_line_ids.date = cls._expiry(-days_ago)
        return picking

    def test_recall_two_customers_and_exclusion(self):
        """B-123 recall lists exactly Hiwot (40) and Kadisco (25), date-ordered;
        Bethel (who only got B-124) is excluded. B-124 recall shows Bethel."""
        self._deliver(self.hiwot, 40, days_ago=20)
        self._deliver(self.kadisco, 25, days_ago=12)
        self._deliver(self.bethel, 30, days_ago=8, force_lot=self.b124)

        lines = self.b123._pharma_recall_lines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].picking_id.partner_id, self.hiwot, "oldest delivery first")
        self.assertEqual(lines[0].quantity, 40)
        self.assertEqual(lines[1].picking_id.partner_id, self.kadisco)
        self.assertEqual(lines[1].quantity, 25)
        self.assertNotIn(self.bethel, lines.picking_id.partner_id)
        self.assertEqual(sum(lines.mapped("quantity")), 65)

        b124_lines = self.b124._pharma_recall_lines()
        self.assertEqual(b124_lines.picking_id.partner_id, self.bethel)
        self.assertEqual(b124_lines.quantity, 30)

    def test_recall_report_prints_contacts(self):
        """The rendered report carries the customer phone and city columns —
        recall means calling people — and excludes the clean customer."""
        self._deliver(self.hiwot, 40, days_ago=20)
        self._deliver(self.kadisco, 25, days_ago=12)
        self._deliver(self.bethel, 30, days_ago=8, force_lot=self.b124)
        html = (
            self.env["ir.actions.report"]
            ._render_qweb_html("vertical_pharma.report_pharma_recall", self.b123.ids)[0]
            .decode()
        )
        for expected in (
            "Hiwot Pharmacy",
            "+251 11 123 4567",
            "Addis Ababa",
            "Kadisco Pharmacy",
            "Adama",
            "B-123",
        ):
            self.assertIn(expected, html)
        self.assertNotIn("Bethel", html, "precision by exclusion")

    def test_dossier_links_receipts_and_lots(self):
        """A dossier aggregates its receipts' batches, sequences itself and
        totals the landed cost; the batch traces back to its dossier."""
        dossier = self.env["pharma.import.dossier"].create(
            {
                "supplier_id": self.supplier.id,
                "eta_date": self.today,
                "amount_goods": 800000,
                "amount_freight": 120000,
                "amount_customs": 260000,
                "amount_clearance": 40000,
            }
        )
        self.assertTrue(dossier.name.startswith("IMP/"), "IMP/ sequence assigned")
        self.assertEqual(dossier.amount_total, 1220000)
        receipt = self.env["stock.picking"].search(
            [
                ("picking_type_id", "=", self.warehouse.in_type_id.id),
                ("move_line_ids.lot_id", "=", self.b123.id),
            ],
            limit=1,
        )
        receipt.pharma_dossier_id = dossier
        self.assertIn(self.b123, dossier.lot_ids)
        self.assertNotIn(self.b124, dossier.lot_ids)
        self.assertEqual(self.b123._pharma_dossiers(), dossier)
        self.assertFalse(self.b124._pharma_dossiers())
