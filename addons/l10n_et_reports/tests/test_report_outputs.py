# -*- coding: utf-8 -*-
"""Render and CSV-export tests for the statutory report layouts."""

import base64

from odoo import Command
from odoo.tests import tagged

from .common import L10nEtReportsCommon


@tagged("post_install", "-at_install")
class TestReportOutputs(L10nEtReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.partner_id.l10n_et_tin = "0099887766"

    def _render(self, report_xmlid, records):
        return (
            self.env["ir.actions.report"]
            ._render_qweb_html(report_xmlid, records.ids)[0]
            .decode()
        )

    def test_vat_declaration_pdf(self):
        """Shows taxpayer TIN, section totals, credit carry-forward and OK
        tie-outs (no warning banner when everything ties)."""
        declaration = self._make_report("l10n.et.vat.declaration")
        html = self._render("l10n_et_reports.report_vat_declaration", declaration)
        self.assertIn("0099887766", html, "taxpayer TIN missing")
        self.assertIn("1500.00", html, "output VAT missing")
        self.assertIn("10950.00", html, "input VAT missing")
        self.assertIn("CREDIT carried forward", html)
        self.assertIn("9450.00", html, "net credit missing")
        self.assertNotIn("MISMATCH", html)
        self.assertNotIn("Fix before filing", html)
        self.assertIn("verify the row layout", html.lower())

    def test_vat_declaration_pdf_mismatch_banner(self):
        """A rogue manual posting on VAT payable renders the warning banner."""
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
                        {"account_id": vat_payable.id, "credit": 100.0, "name": "manual"}
                    ),
                ],
            }
        )
        move.action_post()
        declaration = self._make_report("l10n.et.vat.declaration")
        html = self._render("l10n_et_reports.report_vat_declaration", declaration)
        self.assertIn("Fix before filing", html)
        self.assertIn("MISMATCH", html)

    def test_wht_summary_pdf(self):
        """Shows per-row TIN handling (value / MISSING / N/A foreign), the
        30-day remittance note, the foreign-provider note and the warning."""
        summary = self._make_report("l10n.et.wht.summary")
        html = self._render("l10n_et_reports.report_wht_summary", summary)
        self.assertIn("0011223344", html, "supplier TIN missing")
        self.assertIn("MISSING", html, "missing-TIN marker absent")
        self.assertIn("N/A (foreign)", html, "foreign provider marker absent")
        self.assertIn("within 30 days of month end", html)
        self.assertIn("Foreign providers: no local TIN required", html)
        self.assertIn("Fix before filing", html)
        self.assertIn("No-TIN Supplier", html)
        self.assertIn("7200.00", html, "grand total missing")

    def test_vat_csv_export(self):
        declaration = self._make_report("l10n.et.vat.declaration")
        declaration.action_export_csv()
        content = base64.b64decode(declaration.csv_export_file).decode()
        self.assertIn("Section,Row,Base,Tax", content)
        self.assertIn("Output VAT,TOTAL,10000.00,1500.00", content)
        self.assertIn("Input VAT,TOTAL,73000.00,10950.00", content)
        self.assertIn("VAT credit carried forward,,-9450.00", content)
        self.assertIn("OK", content)
        self.assertNotIn("MISMATCH", content)
        self.assertEqual(declaration.csv_export_filename, "vat_declaration_2026_07.csv")

    def test_wht_csv_export(self):
        summary = self._make_report("l10n.et.wht.summary")
        summary.action_export_csv()
        content = base64.b64decode(summary.csv_export_file).decode()
        self.assertIn("Date,Reference,Supplier,TIN,Kind,Rate %,Base,WHT", content)
        self.assertIn("Compliant Supplier PLC,0011223344,goods,3,50000.00,1500.00", content)
        self.assertIn("No-TIN Supplier,MISSING,punitive,30,15000.00,4500.00", content)
        self.assertIn("N/A (foreign),foreign_digital,15,8000.00,1200.00", content)
        self.assertIn("GRAND TOTAL,,,7200.00", content)
        self.assertIn("WARNING", content)
