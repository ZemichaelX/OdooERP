# -*- coding: utf-8 -*-
"""One test that produces an actual PDF file for a purchase order.

Same shape and same reasoning as the invoice bridge's `test_invoice_pdf.py`:
under `--test-enable` Odoo falls back to HTML, and forcing the real render from
a plain TransactionCase hangs because wkhtmltopdf has no server to fetch assets
from. An HttpCase gives it one.

Content assertions live in `test_purchase_dates.py`, against HTML. This file
asserts that the order actually prints.
"""

from datetime import datetime

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestL10nEtPurchasePdf(HttpCase):
    def test_the_order_prints_and_the_pdf_is_real(self):
        self.env["ir.config_parameter"].sudo().set_param("web.base.url", self.base_url())
        company = self.env.company
        company.l10n_et_report_calendar = "both"
        company.l10n_et_date_format = "latin"

        vendor = self.env["res.partner"].create({"name": "Addis Supplies PLC"})
        product = self.env["product.product"].create(
            {"name": "Printer paper", "purchase_ok": True}
        )
        order = self.env["purchase.order"].create(
            {
                "partner_id": vendor.id,
                "date_order": datetime(2025, 7, 8, 9, 0),
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": 10,
                            "price_unit": 100.0,
                            "date_planned": datetime(2025, 8, 7, 9, 0),
                        },
                    )
                ],
            }
        )
        order.date_planned = datetime(2025, 8, 7, 9, 0)
        self.assertEqual(order.l10n_et_date_order, "2017-11-01")

        pdf, report_type = (
            self.env["ir.actions.report"]
            .with_context(force_report_rendering=True)
            ._render_qweb_pdf("purchase.action_report_purchase_order", order.ids)
        )
        self.assertEqual(report_type, "pdf", "Odoo fell back to HTML")
        self.assertTrue(pdf.startswith(b"%PDF"), "not a PDF")
        self.assertGreater(len(pdf), 5000, "a PDF this small printed nothing")
