# -*- coding: utf-8 -*-
"""Golden tests for the WHT summary engine (values in common.py)."""

from odoo.tests import tagged

from .common import L10nEtReportsCommon


@tagged("post_install", "-at_install")
class TestWhtSummary(L10nEtReportsCommon):
    def test_rows_golden(self):
        """One row per bill/rate: 3% 1,500 on 50,000; 30% 4,500 on 15,000;
        15% 1,200 on 8,000 — with supplier TINs."""
        summary = self._make_report("l10n.et.wht.summary")
        data = summary._get_report_data()
        self.assertEqual(len(data["rows"]), 3)
        by_kind = {row["kind"]: row for row in data["rows"]}
        self.assertEqual(by_kind["goods"]["base"], 50000.0)
        self.assertEqual(by_kind["goods"]["amount"], 1500.0)
        self.assertEqual(by_kind["goods"]["rate"], 3.0)
        self.assertEqual(by_kind["goods"]["tin"], "0011223344")
        self.assertEqual(by_kind["punitive"]["base"], 15000.0)
        self.assertEqual(by_kind["punitive"]["amount"], 4500.0)
        self.assertEqual(by_kind["punitive"]["rate"], 30.0)
        self.assertEqual(by_kind["punitive"]["tin"], "")
        self.assertEqual(by_kind["foreign_digital"]["amount"], 1200.0)
        self.assertEqual(by_kind["foreign_digital"]["rate"], 15.0)

    def test_totals_by_rate_and_grand_total(self):
        summary = self._make_report("l10n.et.wht.summary")
        data = summary._get_report_data()
        self.assertEqual(data["totals_by_rate"], {3.0: 1500.0, 15.0: 1200.0, 30.0: 4500.0})
        self.assertEqual(data["grand_total"], 7200.0)
        self.assertEqual(summary.total_wht, 7200.0)

    def test_tie_out_to_wht_payable_gl(self):
        """Grand total ties to the full movement of the WHT payable account."""
        summary = self._make_report("l10n.et.wht.summary")
        data = summary._get_report_data()
        self.assertTrue(data["tie_out_ok"], data["tie_out"])
        tie = data["tie_out"][0]
        self.assertEqual(tie["report_total"], 7200.0)
        self.assertEqual(tie["gl_total"], 7200.0)
        self.assertIn("300600", tie["accounts"])

    def test_missing_tin_warning(self):
        """The no-TIN supplier is named in the fix-before-filing warning."""
        summary = self._make_report("l10n.et.wht.summary")
        data = summary._get_report_data()
        self.assertEqual(data["missing_tin"], ["No-TIN Supplier"])
        self.assertEqual(len(data["warnings"]), 1)
        self.assertIn("No-TIN Supplier", data["warnings"][0])

    def test_refund_nets_out(self):
        """A vendor refund with WHT reduces the summary and still ties out."""
        refund = self._post_move("in_refund", self.partner_compliant, self.product_goods, 30000)
        # The l10n_et_base engine only automates in_invoice; put the WHT tax on
        # the refund line explicitly, as a user reversing a bill would keep it.
        goods_tax = (
            self.env["account.chart.template"]
            .with_company(self.company)
            .ref("l10n_et_base_tax_wht_purchase_goods_3")
        )
        refund.button_draft()
        refund.invoice_line_ids.tax_ids = [(4, goods_tax.id)]
        refund.action_post()
        summary = self._make_report("l10n.et.wht.summary")
        data = summary._get_report_data()
        self.assertEqual(data["totals_by_rate"][3.0], 600.0)  # 1,500 − 900
        self.assertEqual(data["grand_total"], 6300.0)
        self.assertTrue(data["tie_out_ok"], data["tie_out"])

    def test_period_with_no_wht_is_empty_and_ties(self):
        june = self.env["l10n.et.wht.summary"].create(
            {
                "company_id": self.company.id,
                "date_from": "2026-06-01",
                "date_to": "2026-06-30",
            }
        )
        data = june._get_report_data()
        self.assertEqual(data["rows"], [])
        self.assertEqual(data["grand_total"], 0.0)
        self.assertTrue(data["tie_out_ok"])
