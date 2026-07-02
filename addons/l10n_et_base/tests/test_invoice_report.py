# -*- coding: utf-8 -*-
"""Render tests for the Ethiopian invoice layout and WHT certificate."""

from odoo import Command
from odoo.tests import tagged

from .common import L10nEtBaseCommon


@tagged("post_install", "-at_install")
class TestEtReports(L10nEtBaseCommon):
    def test_et_invoice_report_renders_tins_and_number(self):
        """The Ethiopian VAT invoice shows seller TIN, buyer TIN, the sequential
        invoice number and the VAT amount."""
        self.company.partner_id.l10n_et_tin = "0099887766"
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_compliant.id,
                "invoice_date": "2026-07-01",
                "company_id": self.company.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_goods.id,
                            "quantity": 1,
                            "price_unit": 10000,
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        html = (
            self.env["ir.actions.report"]
            ._render_qweb_html("l10n_et_base.report_et_invoice", invoice.ids)[0]
            .decode()
        )
        self.assertIn("VAT Invoice", html)
        self.assertIn(invoice.name, html, "sequential invoice number missing")
        self.assertIn("0099887766", html, "seller TIN missing")
        self.assertIn("0011223344", html, "buyer TIN missing")
        self.assertIn("1,500", html, "15% VAT amount missing from breakdown")

    def test_wht_certificate_renders_amounts(self):
        """The WHT certificate lists the withheld amount and both TINs."""
        self.company.partner_id.l10n_et_tin = "0099887766"
        bill = self._create_bill(self.partner_compliant, [(self.product_goods, 50000)])
        html = (
            self.env["ir.actions.report"]
            ._render_qweb_html("l10n_et_base.report_wht_certificate", bill.ids)[0]
            .decode()
        )
        self.assertIn("Withholding Tax Certificate", html)
        self.assertIn("0099887766", html)
        self.assertIn("0011223344", html)
        self.assertIn("1,500", html, "withheld amount missing")
