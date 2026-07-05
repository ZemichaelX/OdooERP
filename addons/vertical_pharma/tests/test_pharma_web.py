# -*- coding: utf-8 -*-
"""Browser-path test: the expired-lot block must surface through web dispatch
(the path a warehouse user actually hits when clicking Validate)."""

import json
from datetime import datetime, time, timedelta

from odoo import Command, fields
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestPharmaWebPath(HttpCase):
    def _call_kw(self, model, method, args=None, kwargs=None):
        response = self.url_open(
            f"/web/dataset/call_kw/{model}/{method}",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "model": model,
                        "method": method,
                        "args": args or [],
                        "kwargs": kwargs or {},
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        return response.json()

    def test_expired_lot_block_surfaces_in_web_dispatch(self):
        """Validating a delivery with an expired lot over the web RPC path
        returns the blocking UserError (the dialog the warehouse user sees)."""
        env = self.env
        # Dedicated company (warehouse auto-created in test mode); the admin
        # session must be allowed into it for the web call to reach the picking.
        company = env["res.company"].create({"name": "Pharma Web Test Co"})
        env.ref("base.user_admin").write({"company_ids": [(4, company.id)]})
        env = env(context=dict(env.context, allowed_company_ids=[company.id]))
        warehouse = env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
        medicine = env["product.product"].create(
            {
                "name": "Web Test Medicine",
                "type": "consu",
                "is_storable": True,
                "is_pharma": True,
            }
        )
        today = fields.Date.context_today(env["stock.lot"])
        lot = env["stock.lot"].create(
            {
                "name": "LOT-WEB-EXP",
                "product_id": medicine.id,
                "company_id": company.id,
                "expiration_date": datetime.combine(today - timedelta(days=1), time(12, 0)),
            }
        )
        env["stock.quant"]._update_available_quantity(
            medicine, warehouse.lot_stock_id, 5, lot_id=lot
        )
        picking = env["stock.picking"].create(
            {
                "picking_type_id": warehouse.out_type_id.id,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": env.ref("stock.stock_location_customers").id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": medicine.id,
                            "product_uom_qty": 1,
                            "location_id": warehouse.lot_stock_id.id,
                            "location_dest_id": env.ref("stock.stock_location_customers").id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        # Odoo refuses to reserve expired stock, so put the lot on a manual
        # move line — the same way a warehouse user would force it.
        env["stock.move.line"].create(
            {
                "move_id": picking.move_ids.id,
                "picking_id": picking.id,
                "product_id": medicine.id,
                "quantity": 1,
                "lot_id": lot.id,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": env.ref("stock.stock_location_customers").id,
            }
        )
        picking.move_ids.picked = True
        env.cr.flush()

        self.authenticate("admin", "admin")
        payload = self._call_kw(
            "stock.picking",
            "button_validate",
            [[picking.id]],
            {"context": {"allowed_company_ids": [company.id]}},
        )
        self.assertIn("error", payload, "expired-lot delivery must be blocked")
        self.assertIn(
            "expired batches",
            payload["error"]["data"]["message"],
        )
