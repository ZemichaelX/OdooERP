# -*- coding: utf-8 -*-
"""End-to-end golden verification of the demo trader tenant (Epic C).

Provisions a tenant through the REAL onboarding wizard and REAL business flows
(quotation → delivery → invoice, PO → receipt → bill, payroll batch), then
asserts every hand-computed month total and that all four statutory reports
tie out to the GL. Numbers (July 2026):

- Sales: 32,000 (Mebrat, 40 sheets G32) + 24,000 (Abyssinia, rebar+HCB) = 56,000
  → output VAT 8,400
- Purchases: 52,000 (Derba depot: 30 quintals cement + rebar, 3% WHT 1,560)
  + 15,000 (Yonas Transport, no TIN, 30% WHT
  4,500) + 8,000 (BuildSoft foreign digital, 15% WHT 1,200) = 75,000
  → input VAT 11,250; WHT grand total 7,260
- Net VAT: 8,400 − 11,250 = −2,850 (credit carried forward)
- Payroll: gross 23,800; PAYE 3,900; pension 1,526 EE / 2,398 ER; net 18,374;
  journal 26,198 balanced
"""

from odoo.tests import TransactionCase, tagged

from odoo.addons.sapian_core.models.sapian_module_catalog import SapianModuleCatalog


@tagged("post_install", "-at_install")
class TestDemoTraderE2E(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Distinct name: independent from the demo-flag data, same code path.
        # No module installation can occur (deps already installed), so the
        # whole provision runs inside the test transaction.
        cls.company = cls.env["sapian.demo.trader"]._provision_demo_tenant(
            company_name="E2E Trading PLC"
        )
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company.ids))

    def _report(self, model_name):
        return (
            self.env[model_name]
            .with_company(self.company)
            .create(
                {
                    "company_id": self.company.id,
                    "date_from": "2026-07-01",
                    "date_to": "2026-07-31",
                }
            )
        )

    def test_company_onboarded_via_wizard(self):
        """The tenant went through the real wizard: chart, currency, TIN,
        Ethiopian fiscal year, branding."""
        company = self.company
        self.assertEqual(company.chart_template, "et")
        self.assertEqual(company.currency_id, self.env.ref("base.ETB"))
        self.assertEqual(company.partner_id.l10n_et_tin, "0088776655")
        self.assertEqual(company.fiscalyear_last_month, "7")
        self.assertEqual(company.fiscalyear_last_day, 7)
        self.assertEqual(company.primary_color, "#1a7f5a")
        # The wizard must have ENABLED every pick whose module is genuinely
        # installed. Comparing against the installed set (not against the
        # catalog itself, which would be true by construction) keeps this able
        # to catch "the wizard failed to enable a pick"; the catalog/dependency
        # invariant that makes the two coincide is pinned separately in
        # test_catalog_dependencies.
        catalog = self.env["sapian.module.catalog"].search([("company_id", "=", company.id)])
        installed_names = set(
            self.env["ir.module.module"]
            .search(
                [("name", "in", catalog.mapped("technical_name")), ("state", "=", "installed")]
            )
            .mapped("name")
        )
        expected_enabled = catalog.filtered(
            lambda entry: entry.technical_name in installed_names
        )
        self.assertEqual(len(catalog), len(SapianModuleCatalog.STANDARD_CATALOG))
        self.assertTrue(expected_enabled)
        self.assertEqual(catalog.filtered("enabled"), expected_enabled)

    def test_sales_invoices_vat(self):
        """Both customer invoices posted with 15% VAT: 36,800 and 27,600."""
        invoices = self.env["account.move"].search(
            [
                ("company_id", "=", self.company.id),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
            ]
        )
        self.assertEqual(len(invoices), 2)
        self.assertEqual(sum(invoices.mapped("amount_untaxed")), 56000.0)
        self.assertEqual(sum(invoices.mapped("amount_tax")), 8400.0)
        # Demo-data review regressions: invoices are in ETB (not the default
        # USD pricelist), and the due date is never before the issue date.
        etb = self.env.ref("base.ETB")
        for invoice in invoices:
            self.assertEqual(invoice.currency_id, etb, "sales invoice must be ETB")
            self.assertGreaterEqual(
                invoice.invoice_date_due,
                invoice.invoice_date,
                "due date must not precede the invoice date",
            )
        # Deliveries actually happened (quotation → delivery → invoice).
        deliveries = self.env["stock.picking"].search(
            [
                ("company_id", "=", self.company.id),
                ("picking_type_code", "=", "outgoing"),
            ]
        )
        self.assertTrue(deliveries)
        self.assertTrue(all(p.state == "done" for p in deliveries))

    def test_purchase_bill_wht_and_receipt(self):
        """The PO bill carries 3% WHT 1,560 on 52,000 and the receipt is done."""
        bill = self.env["account.move"].search(
            [
                ("company_id", "=", self.company.id),
                ("move_type", "=", "in_invoice"),
                # The compliant supplier (TIN + licence) -> 3% WHT.
                ("partner_id.name", "like", "Derba Midroc"),
            ]
        )
        self.assertEqual(bill.state, "posted")
        self.assertEqual(bill.amount_untaxed, 52000.0)
        wht_lines = bill.line_ids.filtered(lambda line: line.tax_line_id.l10n_et_wht_kind)
        self.assertEqual(wht_lines.tax_line_id.l10n_et_wht_kind, "goods")
        self.assertEqual(wht_lines.credit, 1560.0)
        # total = 52,000 + 7,800 VAT − 1,560 WHT
        self.assertEqual(bill.amount_total, 58240.0)
        receipts = self.env["stock.picking"].search(
            [
                ("company_id", "=", self.company.id),
                ("picking_type_code", "=", "incoming"),
            ]
        )
        self.assertTrue(all(p.state == "done" for p in receipts))

    def test_punitive_and_foreign_digital_bills(self):
        """Yonas Transport (no TIN) → 30% = 4,500; BuildSoft → 15% = 1,200."""
        bills = self.env["account.move"].search(
            [
                ("company_id", "=", self.company.id),
                ("move_type", "=", "in_invoice"),
                ("state", "=", "posted"),
            ]
        )
        wht_by_kind = {}
        for line in bills.line_ids.filtered(lambda line: line.tax_line_id.l10n_et_wht_kind):
            wht_by_kind[line.tax_line_id.l10n_et_wht_kind] = line.credit
        self.assertEqual(
            wht_by_kind,
            {"goods": 1560.0, "punitive": 4500.0, "foreign_digital": 1200.0},
        )

    def test_payroll_posted_golden(self):
        """The payroll run posted a balanced 26,198 journal with the golden
        splits, and the bank file exists."""
        run = self.env["l10n.et.payroll.run"].search([("company_id", "=", self.company.id)])
        self.assertEqual(run.state, "done")
        self.assertEqual(run.total_gross, 23800.0)
        self.assertEqual(run.total_paye, 3900.0)
        self.assertEqual(run.total_pension_employee, 1526.0)
        self.assertEqual(run.total_pension_employer, 2398.0)
        self.assertEqual(run.total_net, 18374.0)
        move = run.move_id
        self.assertEqual(move.state, "posted")
        self.assertEqual(sum(move.line_ids.mapped("debit")), 26198.0)
        self.assertEqual(
            sum(move.line_ids.mapped("debit")), sum(move.line_ids.mapped("credit"))
        )
        self.assertTrue(run.bank_export_file)

    def test_vat_declaration_golden_and_tie_out(self):
        """Output 8,400 / input 11,250 / net −2,850 credit; both tie-outs OK."""
        declaration = self._report("l10n.et.vat.declaration")
        data = declaration._get_report_data()
        self.assertEqual(data["output_total_base"], 56000.0)
        self.assertEqual(data["output_total_tax"], 8400.0)
        self.assertEqual(data["input_total_base"], 75000.0)
        self.assertEqual(data["input_total_tax"], 11250.0)
        self.assertEqual(data["net_vat"], -2850.0)
        self.assertFalse(data["is_payable"])
        self.assertTrue(data["tie_out_ok"], data["tie_out"])

    def test_wht_summary_golden_and_warnings(self):
        """WHT rows tie to GL at 7,260; Habesha flagged MISSING, CloudServe not."""
        summary = self._report("l10n.et.wht.summary")
        data = summary._get_report_data()
        self.assertEqual(data["totals_by_rate"], {3.0: 1560.0, 15.0: 1200.0, 30.0: 4500.0})
        self.assertEqual(data["grand_total"], 7260.0)
        self.assertTrue(data["tie_out_ok"], data["tie_out"])
        self.assertEqual(len(data["missing_tin"]), 1)
        self.assertIn("Yonas Transport", data["missing_tin"][0])

    def test_statutory_reports_render(self):
        """All four statutory documents render with the expected markers."""
        render = self.env["ir.actions.report"]._render_qweb_html
        declaration = self._report("l10n.et.vat.declaration")
        html = render("l10n_et_reports.report_vat_declaration", declaration.ids)[0].decode()
        self.assertIn("8400.00", html)
        self.assertNotIn("MISMATCH", html)

        summary = self._report("l10n.et.wht.summary")
        html = render("l10n_et_reports.report_wht_summary", summary.ids)[0].decode()
        self.assertIn("MISSING", html)
        self.assertIn("N/A (foreign)", html)
        self.assertIn("7260.00", html)

        run = self.env["l10n.et.payroll.run"].search([("company_id", "=", self.company.id)])
        html = render("l10n_et_payroll.report_paye_declaration", run.ids)[0].decode()
        self.assertIn("3,900", html)
        html = render("l10n_et_payroll.report_pension_schedule", run.ids)[0].decode()
        self.assertIn("MISSING", html, "missing POESSA marker absent")
        self.assertIn("Fix before filing", html)
        self.assertIn("Chaltu", html)

    def test_configure_demo_login(self):
        """Admin defaults to the real company; placeholder companies (incl. the
        original main company) leave the switcher; users are moved off them."""
        placeholders_before = self.env["res.company"].search(
            [
                (
                    "name",
                    "in",
                    [
                        "My US Company",
                        "My Company (Chicago)",
                        "My Company (San Francisco)",
                        "YourCompany",
                    ],
                ),
            ]
        )
        self.env["sapian.demo.trader"]._configure_demo_login(self.company)
        admin = self.env.ref("base.user_admin")
        self.assertEqual(admin.company_id, self.company)
        self.assertIn(self.company, admin.company_ids)
        for placeholder in placeholders_before:
            self.assertFalse(placeholder.active, placeholder.name)
            self.assertNotIn(placeholder, admin.company_ids)
        users = (
            self.env["res.users"]
            .with_context(active_test=False)
            .search([("company_id", "in", placeholders_before.ids)])
        )
        self.assertFalse(users, "users still default to a placeholder company")

    def test_demo_provision_idempotent(self):
        """Provisioning again with the same name is a no-op."""
        again = self.env["sapian.demo.trader"]._provision_demo_tenant(
            company_name="E2E Trading PLC"
        )
        self.assertEqual(again, self.company)
        self.assertEqual(
            self.env["l10n.et.payroll.run"].search_count(
                [("company_id", "=", self.company.id)]
            ),
            1,
        )

    def test_multi_uom_setting_is_enabled(self):
        """The units are VISIBLE, not just present.

        Odoo hides every UoM field unless "Units of Measure & Packagings" is
        on, so without this the quintal/bag pair below is data no prospect can
        see: no unit on the product form, no unit column on the purchase line.
        Asked the way the settings screen asks it — read back through
        res.config.settings — rather than by re-stating the write.
        """
        settings = self.env["res.config.settings"].default_get(["group_uom"])
        self.assertTrue(
            settings["group_uom"],
            "Settings > Inventory > 'Units of Measure & Packagings' is off, so "
            "the demo's quintal/bag conversion is invisible on screen",
        )
        # And the mechanism behind it, since that is what a view actually tests.
        self.assertIn(
            self.env.ref("uom.group_uom"),
            self.env.ref("base.group_user").all_implied_ids,
        )

    def test_cement_is_sold_in_bags_and_bought_in_quintals(self):
        """The unit moment: 30 quintals purchased -> 60 bags on hand.

        Odoo 19 has no UoM categories; the quintal is a related unit worth two
        bags (relative_uom_id/relative_factor) and the product offers both
        through uom_ids. Cement has no opening stock, so the on-hand quantity
        IS the conversion.
        """
        # Start from THIS company's purchase line: products are global, and
        # with the tenant now shipping in data/ the database also holds the
        # install-time Selam company's identically-named products.
        line = self.env["purchase.order.line"].search(
            [
                ("order_id.company_id", "=", self.company.id),
                ("product_id.name", "like", "Dangote"),
            ],
            limit=1,
        )
        self.assertTrue(line, "this company bought Dangote cement")
        cement = line.product_id
        self.assertEqual(cement.uom_id.name, "Bag (50 kg)")
        quintal = self.env["uom.uom"].search([("name", "=", "Quintal (100 kg)")], limit=1)
        self.assertTrue(quintal, "the quintal unit exists")
        self.assertEqual(quintal.relative_uom_id, cement.uom_id)
        self.assertEqual(quintal.relative_factor, 2.0)
        self.assertIn(quintal, cement.uom_ids, "the quintal is offered on lines")

        self.assertEqual(line.product_uom_id, quintal, "purchased in quintals")
        self.assertEqual(line.product_qty, 30.0)

        on_hand = self.env["stock.quant"]._get_available_quantity(
            cement,
            self.env["stock.warehouse"]
            .search([("company_id", "=", self.company.id)], limit=1)
            .lot_stock_id,
        )
        self.assertEqual(on_hand, 60.0, "30 quintals in = 60 bags on hand")
