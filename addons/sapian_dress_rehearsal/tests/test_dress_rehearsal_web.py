# -*- coding: utf-8 -*-
"""Three role walkthroughs over the web dispatch path — the buttons a warehouse
user, an accountant and an HR manager actually click. Each drives a real
document through /web/dataset/call_kw so the server-side logic (WHT auto-apply,
payroll posting, stock validation) is exercised the way the UI hits it."""

import json

from odoo import Command
from odoo.tests import HttpCase, tagged

COMPANY = "Rehearsal Web Co"


@tagged("post_install", "-at_install")
class TestDressRehearsalWeb(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["sapian.dress.rehearsal"]._provision_shell(COMPANY)
        cls.env.ref("base.user_admin").write({"company_ids": [Command.link(cls.company.id)]})
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )

    def _call_kw(self, model, method, args, kwargs=None):
        response = self.url_open(
            f"/web/dataset/call_kw/{model}/{method}",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "model": model,
                        "method": method,
                        "args": args,
                        "kwargs": kwargs or {},
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        return response.json()

    def _ctx(self):
        return {"context": {"allowed_company_ids": [self.company.id]}}

    def test_role_warehouse_receive(self):
        """Warehouse user validates a supplier receipt over the web path."""
        supplier = self.env["res.partner"].search([("name", "like", "Awash")], limit=1)
        product = self.env["product.product"].search([("name", "like", "Teff")], limit=1)
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "partner_id": supplier.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.warehouse.lot_stock_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": 10,
                            "location_id": self.env.ref("stock.stock_location_suppliers").id,
                            "location_dest_id": self.warehouse.lot_stock_id.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.move_ids.quantity = 10
        picking.move_ids.picked = True
        self.env.cr.flush()
        self.authenticate("admin", "admin")
        payload = self._call_kw("stock.picking", "button_validate", [[picking.id]], self._ctx())
        self.assertNotIn("error", payload, payload)
        picking.invalidate_recordset()
        self.assertEqual(picking.state, "done")

    def test_role_accountant_bill_with_wht(self):
        """Accountant posts a vendor bill; WHT auto-applies over the web path."""
        supplier = self.env["res.partner"].search([("name", "like", "Awash")], limit=1)
        product = self.env["product.product"].search([("name", "like", "Teff")], limit=1)
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": supplier.id,
                "invoice_date": "2026-08-15",
                "company_id": self.company.id,
                "invoice_line_ids": [
                    Command.create(
                        {"product_id": product.id, "quantity": 50, "price_unit": 2000}
                    )
                ],
            }
        )
        self.env.cr.flush()
        self.authenticate("admin", "admin")
        payload = self._call_kw("account.move", "action_post", [[bill.id]], self._ctx())
        self.assertNotIn("error", payload, payload)
        bill.invalidate_recordset()
        self.assertEqual(bill.state, "posted")
        # 100,000 base > 20,000 → 3% WHT applied automatically.
        wht_lines = bill._l10n_et_wht_move_lines()
        self.assertTrue(wht_lines, "WHT line should have been applied on posting")
        self.assertAlmostEqual(abs(sum(wht_lines.mapped("balance"))), 3000.0, places=2)

    def test_role_hr_confirm_payroll(self):
        """HR manager confirms a payroll run over the web path; it posts."""
        employees = self.env["hr.employee"].search([("company_id", "=", self.company.id)])
        run = self.env["l10n.et.payroll.run"].create(
            {
                "company_id": self.company.id,
                "date_from": "2026-08-01",
                "date_to": "2026-08-31",
                "employee_ids": [Command.set(employees.ids)],
            }
        )
        run.action_generate_payslips()
        self.env.cr.flush()
        self.authenticate("admin", "admin")
        payload = self._call_kw(
            "l10n.et.payroll.run", "action_confirm", [[run.id]], self._ctx()
        )
        self.assertNotIn("error", payload, payload)
        run.invalidate_recordset()
        self.assertEqual(run.state, "done")
        self.assertTrue(run.move_id, "payroll journal entry should be posted")
