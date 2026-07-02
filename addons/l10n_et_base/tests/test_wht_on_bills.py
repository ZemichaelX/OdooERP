# -*- coding: utf-8 -*-
"""Integration tests for the automatic WHT engine on vendor bills.

Golden values mirror the reference-calculator tests in tests_fast/ so the Odoo
layer is proven to reproduce the approved reference math through real postings.
"""

from odoo import Command
from odoo.tests import tagged

from .common import L10nEtBaseCommon


@tagged("post_install", "-at_install")
class TestWhtOnBills(L10nEtBaseCommon):
    def test_config_seeded_on_chart_load(self):
        """Loading the 'et' chart must seed the effective-dated WHT config with a
        source note (rates are data, never code)."""
        config = self.env["l10n.et.wht.config"]._get_config(self.company, "2026-07-01")
        self.assertTrue(config, "WHT config was not seeded on chart load")
        self.assertEqual(config.rate_standard, 0.03)
        self.assertEqual(config.threshold_goods, 20000.0)
        self.assertTrue(config.punitive_respects_thresholds)
        self.assertTrue(config.source_note)

    def test_core_account_types_fixed(self):
        """Our template overrides must fix the mistyped core accounts (VAT payable
        et al. were shipped as assets by core l10n_et)."""
        # code_digits '6' on template 'et' pads the CSV codes: 3006 → 300600.
        account = (
            self.env["account.account"]
            .with_company(self.company)
            .search(
                [
                    ("code", "=", "300600"),
                    ("company_ids", "in", self.company.id),
                ],
                limit=1,
            )
        )
        self.assertTrue(account)
        self.assertEqual(account.account_type, "liability_current")
        self.assertEqual(account.name, "Withholding Tax Payable")

    def test_new_accounts_created(self):
        """The module's own accounts (PAYE payable, customs duty clearing) exist
        with consistent 6-digit codes on a fresh chart load."""
        account_model = self.env["account.account"].with_company(self.company)
        for code, name, account_type in (
            ("300900", "PAYE (Employment Income Tax) Payable", "liability_current"),
            ("230200", "Customs Duty Clearing", "asset_current"),
        ):
            account = account_model.search(
                [
                    *account_model._check_company_domain(self.company),
                    ("code", "=", code),
                ],
                limit=1,
            )
            self.assertTrue(account, f"account {code} missing")
            self.assertEqual(account.name, name)
            self.assertEqual(account.account_type, account_type)

    def test_wht_goods_50000_compliant_supplier_is_1500(self):
        """Spec worked example: 50,000 goods, compliant supplier → 3% = 1,500;
        payable to the supplier drops to 48,500."""
        bill = self._create_bill(self.partner_compliant, [(self.product_goods, 50000)])
        wht_lines = self._wht_lines(bill)
        self.assertEqual(len(wht_lines), 1)
        self.assertEqual(wht_lines.tax_line_id.l10n_et_wht_kind, "goods")
        self.assertEqual(wht_lines.credit, 1500.0)
        self.assertEqual(wht_lines.account_id.code, "300600")
        self.assertEqual(bill.amount_total, 48500.0)

    def test_wht_goods_exactly_20000_exempt(self):
        """Threshold is exclusive: exactly 20,000 goods attracts no WHT."""
        bill = self._create_bill(self.partner_compliant, [(self.product_goods, 20000)])
        self.assertFalse(self._wht_lines(bill))
        self.assertEqual(bill.amount_total, 20000.0)

    def test_wht_service_15000_compliant_supplier_is_450(self):
        """Services threshold 10,000: 15,000 service → 3% = 450."""
        bill = self._create_bill(self.partner_compliant, [(self.product_service, 15000)])
        wht_lines = self._wht_lines(bill)
        self.assertEqual(wht_lines.tax_line_id.l10n_et_wht_kind, "service")
        self.assertEqual(wht_lines.credit, 450.0)
        self.assertEqual(bill.amount_total, 14550.0)

    def test_wht_no_tin_supplier_is_punitive_15000(self):
        """50,000 goods from a supplier without TIN/licence → 30% = 15,000."""
        bill = self._create_bill(self.partner_no_tin, [(self.product_goods, 50000)])
        wht_lines = self._wht_lines(bill)
        self.assertEqual(wht_lines.tax_line_id.l10n_et_wht_kind, "punitive")
        self.assertEqual(wht_lines.credit, 15000.0)
        self.assertEqual(bill.amount_total, 35000.0)

    def test_wht_no_tin_below_threshold_exempt_by_default(self):
        """Default config gates the punitive rate by the thresholds: 5,000 goods
        from a no-TIN supplier → no WHT."""
        bill = self._create_bill(self.partner_no_tin, [(self.product_goods, 5000)])
        self.assertFalse(self._wht_lines(bill))

    def test_wht_punitive_gating_flag_false_applies_below_threshold(self):
        """Flipping punitive_respects_thresholds (config, not code) applies 30%
        below the threshold: 5,000 goods, no TIN → 1,500."""
        config = self.env["l10n.et.wht.config"]._get_config(self.company, "2026-07-01")
        config.punitive_respects_thresholds = False
        bill = self._create_bill(self.partner_no_tin, [(self.product_goods, 5000)])
        wht_lines = self._wht_lines(bill)
        self.assertEqual(wht_lines.credit, 1500.0)

    def test_wht_foreign_digital_8000_is_1200(self):
        """Foreign digital services: 15% on any amount (below domestic threshold)."""
        bill = self._create_bill(self.partner_foreign_digital, [(self.product_service, 8000)])
        wht_lines = self._wht_lines(bill)
        self.assertEqual(wht_lines.tax_line_id.l10n_et_wht_kind, "foreign_digital")
        self.assertEqual(wht_lines.credit, 1200.0)
        self.assertEqual(bill.amount_total, 6800.0)

    def test_wht_mixed_bill_thresholds_per_kind(self):
        """Goods and services on one bill are evaluated per kind: 25,000 goods
        (over 20k → 750) + 8,000 services (under 10k → exempt)."""
        bill = self._create_bill(
            self.partner_compliant,
            [
                (self.product_goods, 25000),
                (self.product_service, 8000),
            ],
        )
        wht_lines = self._wht_lines(bill)
        self.assertEqual(len(wht_lines), 1)
        self.assertEqual(wht_lines.tax_line_id.l10n_et_wht_kind, "goods")
        self.assertEqual(wht_lines.credit, 750.0)

    def test_wht_reapplied_idempotently_on_repost(self):
        """Reset-to-draft + repost must not stack WHT taxes on the lines."""
        bill = self._create_bill(self.partner_compliant, [(self.product_goods, 50000)])
        bill.button_draft()
        bill.action_post()
        wht_lines = self._wht_lines(bill)
        self.assertEqual(len(wht_lines), 1)
        self.assertEqual(wht_lines.credit, 1500.0)

    def test_wht_effective_dating_new_config_does_not_rewrite_history(self):
        """A future threshold change applies only from its effective date; a bill
        dated under the old config keeps the old rules."""
        config = self.env["l10n.et.wht.config"]._get_config(self.company, "2026-07-01")
        config.effective_to = "2026-07-31"
        self.env["l10n.et.wht.config"].create(
            {
                "company_id": self.company.id,
                "effective_from": "2026-08-01",
                "threshold_goods": 100000.0,
                "source_note": "Test future threshold change",
            }
        )
        old_bill = self._create_bill(
            self.partner_compliant, [(self.product_goods, 50000)], invoice_date="2026-07-15"
        )
        new_bill = self._create_bill(
            self.partner_compliant, [(self.product_goods, 50000)], invoice_date="2026-08-15"
        )
        self.assertEqual(self._wht_lines(old_bill).credit, 1500.0)
        self.assertFalse(self._wht_lines(new_bill), "50,000 is under the new 100,000 threshold")

    def test_wht_with_vat_both_apply(self):
        """WHT coexists with VAT: 50,000 goods + 15% VAT − 3% WHT → 56,000 total."""
        bill = self._create_bill(
            self.partner_compliant, [(self.product_goods, 50000)], with_vat=True
        )
        self.assertEqual(self._wht_lines(bill).credit, 1500.0)
        self.assertEqual(bill.amount_total, 56000.0)

    def test_sale_invoice_vat_15(self):
        """Sale invoice picks up the core 15% VAT by default and posts it to the
        (re-typed) VAT Payable account."""
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
        self.assertEqual(invoice.amount_tax, 1500.0)
        self.assertEqual(invoice.amount_total, 11500.0)
        vat_line = invoice.line_ids.filtered("tax_line_id")
        self.assertEqual(vat_line.account_id.code, "300700")
        self.assertEqual(vat_line.account_id.account_type, "liability_current")

    def test_trial_balance_clean(self):
        """Every automated posting balances (debits == credits)."""
        bill = self._create_bill(
            self.partner_compliant, [(self.product_goods, 50000)], with_vat=True
        )
        self.assertEqual(
            sum(bill.line_ids.mapped("debit")), sum(bill.line_ids.mapped("credit"))
        )
