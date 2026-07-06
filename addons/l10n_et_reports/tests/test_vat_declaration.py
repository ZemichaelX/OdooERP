# -*- coding: utf-8 -*-
"""Golden tests for the monthly VAT declaration engine (values in common.py)."""

from odoo import Command
from odoo.tests import tagged

from .common import L10nEtReportsCommon


@tagged("post_install", "-at_install")
class TestVatDeclaration(L10nEtReportsCommon):
    def test_output_section_golden(self):
        """10,000 sale at 15% → output base 10,000, tax 1,500; zero-rated and
        exempt rows present with zero bases."""
        declaration = self._make_report("l10n.et.vat.declaration")
        data = declaration._get_report_data()
        self.assertEqual(len(data["output_rows"]), 3)
        standard = data["output_rows"][0]
        self.assertEqual(standard["base"], 10000.0)
        self.assertEqual(standard["amount"], 1500.0)
        self.assertEqual(data["output_rows"][1]["base"], 0.0)  # zero-rated
        self.assertEqual(data["output_rows"][2]["base"], 0.0)  # exempt
        self.assertEqual(data["output_total_base"], 10000.0)
        self.assertEqual(data["output_total_tax"], 1500.0)

    def test_input_section_golden(self):
        """Purchases 50,000 + 15,000 + 8,000 at 15% → input base 73,000,
        tax 10,950."""
        declaration = self._make_report("l10n.et.vat.declaration")
        data = declaration._get_report_data()
        standard = data["input_rows"][0]
        self.assertEqual(standard["base"], 73000.0)
        self.assertEqual(standard["amount"], 10950.0)
        self.assertEqual(data["input_total_tax"], 10950.0)

    def test_net_vat_credit_carry_forward(self):
        """Net VAT = 1,500 − 10,950 = −9,450: a credit, not payable."""
        declaration = self._make_report("l10n.et.vat.declaration")
        data = declaration._get_report_data()
        self.assertEqual(data["net_vat"], -9450.0)
        self.assertFalse(data["is_payable"])
        self.assertEqual(declaration.net_vat, -9450.0)

    def test_tie_out_matches_gl(self):
        """Report totals equal the full GL movement of the VAT accounts."""
        declaration = self._make_report("l10n.et.vat.declaration")
        data = declaration._get_report_data()
        self.assertTrue(data["tie_out_ok"], data["tie_out"])
        output_tie = data["tie_out"][0]
        self.assertEqual(output_tie["report_total"], 1500.0)
        self.assertEqual(output_tie["gl_total"], 1500.0)
        self.assertIn("300700", output_tie["accounts"])
        input_tie = data["tie_out"][1]
        self.assertEqual(input_tie["gl_total"], 10950.0)

    def test_tie_out_flags_manual_gl_posting(self):
        """A manual journal entry on the VAT payable account (bypassing the tax
        engine) must break the tie-out visibly."""
        declaration = self._make_report("l10n.et.vat.declaration")
        vat_payable = (
            self.env["account.chart.template"].with_company(self.company).ref("l10n_et3007")
        )
        expense = (
            self.env["account.chart.template"].with_company(self.company).ref("l10n_et6111")
        )
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2026-07-20",
                "company_id": self.company.id,
                "line_ids": [
                    Command.create(
                        {"account_id": expense.id, "debit": 100.0, "name": "manual"}
                    ),
                    Command.create(
                        {
                            "account_id": vat_payable.id,
                            "credit": 100.0,
                            "name": "manual",
                        }
                    ),
                ],
            }
        )
        move.action_post()
        data = declaration._get_report_data()
        self.assertFalse(data["tie_out_ok"])
        output_tie = data["tie_out"][0]
        self.assertFalse(output_tie["ok"])
        self.assertEqual(output_tie["difference"], 100.0)

    def test_period_filtering(self):
        """Documents outside the period are excluded."""
        self._post_move(
            "out_invoice",
            self.partner_compliant,
            self.product_goods,
            99999,
            invoice_date="2026-08-05",
        )
        declaration = self._make_report("l10n.et.vat.declaration")
        data = declaration._get_report_data()
        self.assertEqual(data["output_total_base"], 10000.0)
        august = self.env["l10n.et.vat.declaration"].create(
            {
                "company_id": self.company.id,
                "date_from": "2026-08-01",
                "date_to": "2026-08-31",
            }
        )
        self.assertEqual(august._get_report_data()["output_total_base"], 99999.0)

    def test_refund_nets_out(self):
        """A credit note reduces the output section."""
        self._post_move("out_refund", self.partner_compliant, self.product_goods, 4000)
        declaration = self._make_report("l10n.et.vat.declaration")
        data = declaration._get_report_data()
        self.assertEqual(data["output_total_base"], 6000.0)
        self.assertEqual(data["output_total_tax"], 900.0)
        self.assertTrue(data["tie_out_ok"])

    def test_off_chart_company_reads_zero_not_raise(self):
        """A4: a declaration for a company NOT on the Ethiopian chart reads as
        zeros with a visible warning state instead of raising on field access."""
        other = self.env["res.company"].create({"name": "Off Chart Co"})
        self.env.user.write({"company_ids": [Command.link(other.id)]})
        declaration = self.env["l10n.et.vat.declaration"].create(
            {
                "company_id": other.id,
                "date_from": "2026-07-01",
                "date_to": "2026-07-31",
            }
        )
        # Reading the computed totals must NOT raise (the audit bug).
        self.assertEqual(declaration.net_vat, 0.0)
        self.assertEqual(declaration.output_vat_total, 0.0)
        self.assertEqual(declaration.input_vat_total, 0.0)
        self.assertTrue(declaration.off_chart, "warning state is set")
        data = declaration._get_report_data()
        self.assertTrue(data["off_chart"])
        self.assertTrue(data["off_chart_warning"])
        # Export must not raise either.
        declaration.action_export_csv()
        self.assertTrue(declaration.csv_export_file)
