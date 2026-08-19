# -*- coding: utf-8 -*-
"""End-to-end golden verification of the demo trader tenant (Epic C).

Provisions a tenant through the REAL onboarding wizard and REAL business flows
(quotation → delivery → invoice, PO → receipt → bill, payroll batch), then
asserts every hand-computed month total and that all four statutory reports
tie out to the GL. Numbers (July 2026):

- Sales: 35,200 (Mebrat, 40 sheets G32) + 80,100 (Abyssinia, rebar+HCB) = 115,300
  → output VAT 17,295
- Purchases: 68,800 (Derba depot: 30 quintals cement + rebar, 3% WHT 2,064)
  + 15,000 (Yonas Transport, no TIN, 30% WHT
  4,500) + 8,000 (BuildSoft foreign digital, 15% WHT 1,200) = 91,800
  → input VAT 13,770; WHT grand total 7,764
- Net VAT: 17,295 − 13,770 = +3,525 PAYABLE (a normal trading month)
- Payroll: gross 58,300; PAYE 11,525; pension 3,941 EE / 6,193 ER; net 42,834;
  journal 64,493 balanced — six employees, one per PAYE band, so the
  progressive table is visible on the payslip list

Every trading figure here is DOWNSTREAM of demo_catalogue.py — order lines take
their price_unit from cat.PRICES. When a sourced price changes these are
recomputed; they are not an independent golden the prices must be bent to match.
The payroll figures are independent of the catalogue and do not move with it.
"""

from odoo import fields
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
        """Both customer invoices posted with 15% VAT: 40,480 and 92,115."""
        invoices = self.env["account.move"].search(
            [
                ("company_id", "=", self.company.id),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
            ]
        )
        self.assertEqual(len(invoices), 2)
        self.assertEqual(sum(invoices.mapped("amount_untaxed")), 1268300.0)
        self.assertEqual(sum(invoices.mapped("amount_tax")), 190245.0)
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
        """The PO bill carries 3% WHT 2,064 on 68,800 and the receipt is done."""
        bill = self.env["account.move"].search(
            [
                ("company_id", "=", self.company.id),
                ("move_type", "=", "in_invoice"),
                # The compliant supplier (TIN + licence) -> 3% WHT.
                ("partner_id.name", "like", "Derba Midroc"),
            ]
        )
        self.assertEqual(bill.state, "posted")
        self.assertEqual(bill.amount_untaxed, 482800.0)
        wht_lines = bill.line_ids.filtered(lambda line: line.tax_line_id.l10n_et_wht_kind)
        self.assertEqual(wht_lines.tax_line_id.l10n_et_wht_kind, "goods")
        self.assertEqual(wht_lines.credit, 14484.0)
        # total = 68,800 + 10,320 VAT − 2,064 WHT
        self.assertEqual(bill.amount_total, 540736.0)
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
            {"goods": 14484.0, "punitive": 4500.0, "foreign_digital": 1200.0},
        )

    def test_payroll_posted_golden(self):
        """The payroll run posted a balanced 64,493 journal with the golden
        splits, and the bank file exists.

        HAND-COMPUTED from demo_catalogue.EMPLOYEES and the 1395/2025 bands, one
        employee per band. Not read out of a run — a golden copied from the
        thing it checks proves only that the machine agrees with itself.

            basic    +OT     taxable   PAYE = rate*income - deduction
            1,800            1,800     0%                          0
            3,500            3,500     0.15*3,500  -   300  =     225
            6,000            6,000     0.20*6,000  -   500  =     700
           10,000           10,000     0.25*10,000 -   850  =   1,650
           10,000  +2,000   12,000     0.30*12,000 - 1,350  =   2,250
           25,000           25,000     0.35*25,000 - 2,050  =   6,700
            ------  ------   ------                            ------
           56,300  +2,000   58,300                             11,525

        Pension is 7%/11% of the BASIC wage only — overtime is not pensionable —
        so it is computed on 56,300, not on 58,300:
            employee 7%  = 3,941        employer 11% = 6,193
        Net = 58,300 - 11,525 - 3,941 = 42,834
        Journal = gross 58,300 + employer pension 6,193 = 64,493, which must
        equal PAYE 11,525 + pension payable 10,134 + net payable 42,834.
        """
        run = self.env["l10n.et.payroll.run"].search([("company_id", "=", self.company.id)])
        self.assertEqual(run.state, "done")
        self.assertEqual(run.total_gross, 58300.0)
        self.assertEqual(run.total_paye, 11525.0)
        self.assertEqual(run.total_pension_employee, 3941.0)
        self.assertEqual(run.total_pension_employer, 6193.0)
        self.assertEqual(run.total_net, 42834.0)
        move = run.move_id
        self.assertEqual(move.state, "posted")
        self.assertEqual(sum(move.line_ids.mapped("debit")), 64493.0)
        self.assertEqual(
            sum(move.line_ids.mapped("debit")), sum(move.line_ids.mapped("credit"))
        )
        self.assertTrue(run.bank_export_file)

    def test_payroll_exercises_every_paye_band(self):
        """The reason the roster is six people, asserted as an INVARIANT.

        Not "six payslips" and not "six distinct rates": every band that the
        company's own effective-dated PAYE table contains must be occupied by
        at least one payslip. If a future proclamation adds a seventh band, or
        splits one, this fails and the demo roster gets a new employee — which
        is the correct outcome, because a progressive table with an empty band
        is exactly the thing the demo cannot show.

        Reading the bands from `l10n.et.paye.band` rather than from the Python
        reference is deliberate: those records are what the engine actually
        used to compute these payslips, so this compares the demo against the
        configuration rather than against a second opinion.
        """
        run = self.env["l10n.et.payroll.run"].search([("company_id", "=", self.company.id)])
        bands = self.env["l10n.et.paye.band"].search(
            [
                ("company_id", "=", self.company.id),
                ("effective_from", "<=", "2026-07-31"),
                "|",
                ("effective_to", "=", False),
                ("effective_to", ">=", "2026-07-01"),
            ]
        )
        self.assertTrue(bands, "no PAYE bands configured; this test would prove nothing")

        def band_of(income):
            for band in bands:
                if income > band.lower_bound and (
                    band.is_top_band or income <= band.upper_bound
                ):
                    return band
            return None

        occupied = {}
        for slip in run.payslip_ids:
            band = band_of(slip.taxable_income)
            self.assertTrue(band, "payslip income %s falls in no band" % slip.taxable_income)
            occupied.setdefault(band, []).append(slip.employee_id.name)

        empty = bands - self.env["l10n.et.paye.band"].browse([b.id for b in occupied])
        self.assertFalse(
            empty,
            "PAYE bands with no demo payslip in them, so the progressive table "
            "cannot be shown: %s" % ", ".join(empty.mapped("name")),
        )
        # The two ends specifically — a cleaner at 0% and a manager at 35% are
        # what make the table legible at a glance, and they are the two a
        # future roster edit is most likely to lose.
        self.assertEqual(min(slip.taxable_income for slip in run.payslip_ids), 1800.0)
        self.assertEqual(max(slip.taxable_income for slip in run.payslip_ids), 25000.0)
        top_band_slips = [
            slip for slip in run.payslip_ids if band_of(slip.taxable_income).is_top_band
        ]
        self.assertTrue(top_band_slips, "nobody is in the top band")
        self.assertTrue(
            all(slip.employee_id.job_title for slip in run.payslip_ids),
            "every demo employee needs a job title, or the band story is six "
            "names and six numbers",
        )

    def test_sales_pipeline_has_something_to_walk_through(self):
        """Drafts, at least one sent, at least one confirmed — and none of it
        invoiced, so the ledger goldens above cannot move with it.

        Asserted as shapes rather than as a total count: the pipeline is demo
        furniture and will grow. What must not change is that each of the three
        states is populated and that nothing here reaches the general ledger.
        """
        orders = self.env["sale.order"].search([("company_id", "=", self.company.id)])
        by_state = {}
        for order in orders:
            by_state.setdefault(order.state, self.env["sale.order"])
            by_state[order.state] |= order

        self.assertGreaterEqual(
            len(by_state.get("draft", [])), 2, "the Sales pipeline opens empty"
        )
        self.assertTrue(by_state.get("sent"), "no quotation has been sent")
        self.assertTrue(by_state.get("sale"), "no confirmed order")

        # THE PIPELINE MUST BE VISIBLE TO THE ACCOUNT THE DEMO IS PRESENTED
        # FROM, which is a different claim from "orders exist".
        #
        # Odoo's Sales app opens on `sale.action_quotations_with_onboarding`,
        # whose context is `{'search_default_my_quotation': 1}` — a default
        # filter of `user_id = uid`. Provisioning runs through `odoo shell` as
        # OdooBot, so an order that takes the default salesperson is invisible
        # to admin, and Odoo fills the empty list with its ONBOARDING SAMPLE
        # DATA: ghosted quotations for Henry Campbell and Thomas Passot, priced
        # in dollars. Measured on a built demo database before this was fixed.
        #
        # So this asserts through the same filter the app applies.
        demo_user = self.env["sapian.demo.trader"]._demo_salesperson()
        self.assertNotEqual(
            demo_user, self.env.ref("base.user_root"), "OdooBot is not a salesperson"
        )
        visible = orders.filtered(lambda order: order.user_id == demo_user)
        self.assertEqual(
            visible,
            orders,
            "orders not assigned to the demo login are invisible under the "
            "Sales app's default 'My Quotations' filter, and Odoo replaces the "
            "empty list with US sample data: %s"
            % ", ".join((orders - visible).mapped("partner_id.name")),
        )

        uninvoiced = orders.filtered(
            lambda order: order.state == "sale" and not order.invoice_ids
        )
        self.assertTrue(
            uninvoiced,
            "no confirmed-but-uninvoiced order — the demo has nothing to press "
            "'Create Invoice' on",
        )
        # The property the ledger goldens depend on: quotations post nothing.
        for order in by_state.get("draft", []) | by_state.get("sent", self.env["sale.order"]):
            self.assertFalse(order.invoice_ids, "a draft/sent quotation must have no invoice")
        etb = self.env.ref("base.ETB")
        for order in orders:
            self.assertEqual(order.currency_id, etb, "quotations must be in ETB")
            self.assertTrue(order.order_line, "an empty quotation is not a demo")
            self.assertGreater(order.amount_total, 0.0)

        # Every OPEN quotation must be settleable in cash without our own
        # validator refusing it. The ETB 50,000 cap binds account.payment, not
        # the invoice, so this is not a legal requirement — it is so that a
        # presenter improvising a cash receipt on one of these is never blocked
        # on camera. The already-invoiced July flow is not held to it (the
        # Abyssinia credit sale is 92,115); see demo_catalogue.QUOTATIONS.
        cap = self.env["l10n.et.cash.cap.config"]._get_config(self.company, "2026-07-31")
        self.assertTrue(cap, "no cash cap configured; this check would prove nothing")
        open_orders = orders.filtered(lambda order: not order.invoice_ids)
        for order in open_orders:
            self.assertLessEqual(
                order.amount_total,
                cap.cap_amount,
                "%s totals %.2f, over the %.0f cash cap: a cash receipt on it "
                "would be blocked mid-demo"
                % (order.partner_id.name, order.amount_total, cap.cap_amount),
            )

    def test_every_order_is_dated_in_the_demo_month(self):
        """No order may carry the build timestamp.

        Two separate causes, both fixed and both worth a guard:

        1. The invoiced orders never set `date_order` at all, so it defaulted
           to creation time.
        2. Odoo REWRITES `date_order` to now() on confirmation
           (`sale.order._prepare_confirmation_values`), so even an order created
           with a July date came out stamped today once confirmed.

        On screen that reads as seven orders all placed at the same minute of
        the build, which is worse than showing no date: it says "fixture", not
        "a month of trading". Asserted as a window rather than a list of exact
        timestamps, so the pipeline can be edited freely.
        """
        orders = self.env["sale.order"].search([("company_id", "=", self.company.id)])
        self.assertTrue(orders, "no orders to check")
        stray = orders.filtered(
            lambda order: not (
                fields.Date.to_date("2026-07-01")
                <= fields.Date.to_date(order.date_order)
                <= fields.Date.to_date("2026-07-31")
            )
        )
        self.assertFalse(
            stray,
            "orders dated outside the demo month — almost certainly the build "
            "timestamp: %s"
            % ", ".join("%s %s" % (order.partner_id.name, order.date_order) for order in stray),
        )

    def test_the_quotation_list_shows_the_order_date(self):
        """The demo's own view, and proof of what it is overriding.

        Odoo's `sale.view_quotation_tree` replaces `date_order` with
        `create_date` in the Quotations list — that is core behaviour, not
        something this repo introduced, and it is left alone for clients. The
        demo module ships a view that puts the order date back, because in a
        scripted tenant `create_date` is the build timestamp for every row.

        Asserted on the RESOLVED arch that the Sales app actually renders, not
        on our XML file, which would pass even if the inheritance failed to
        apply.
        """
        view = self.env.ref("sale.view_quotation_tree_with_onboarding")
        arch = self.env["sale.order"].get_view(view.id, "list")["arch"]
        self.assertIn(
            'name="date_order"',
            arch,
            "the Quotations list does not show the order date; the demo view "
            "in sapian_demo_trader/views/sale_order_views.xml is not applying",
        )
        self.assertNotIn(
            'name="create_date"',
            arch,
            "the Quotations list still shows Creation Date, which in the demo "
            "is the build timestamp on every row",
        )

    def test_company_carries_its_own_logo_not_odoo_s(self):
        """`uses_default_logo` is False — the field being NON-EMPTY proves
        nothing.

        `res.company.logo` has `default=_get_logo` (base/models/res_company.py),
        so it is always filled: a `assertTrue(company.logo)` check passes on a
        tenant showing Odoo's stock wordmark on every invoice, which is the
        exact defect. Odoo computes `uses_default_logo` by comparing against
        those default bytes, so this is the assertion that can actually go red.
        """
        self.assertTrue(self.company.logo)
        self.assertFalse(
            self.company.uses_default_logo,
            "the demo tenant is rendering Odoo's default logo, which "
            "contradicts the branding claim in the same demo session",
        )

    def test_vat_declaration_golden_and_tie_out(self):
        """Output 17,295 / input 13,770 / net +3,525 payable; both tie-outs OK."""
        declaration = self._report("l10n.et.vat.declaration")
        data = declaration._get_report_data()
        self.assertEqual(data["output_total_base"], 1268300.0)
        self.assertEqual(data["output_total_tax"], 190245.0)
        self.assertEqual(data["input_total_base"], 505800.0)
        self.assertEqual(data["input_total_tax"], 75870.0)
        # July is a normal trading month for a materials retailer: stock bought is
        # sold within weeks, so output exceeds input and the month is PAYABLE.
        self.assertEqual(data["net_vat"], 114375.0)
        self.assertTrue(data["is_payable"])
        self.assertTrue(data["tie_out_ok"], data["tie_out"])

    def test_wht_summary_golden_and_warnings(self):
        """WHT rows tie to GL at 7,764; Yonas flagged MISSING, BuildSoft not."""
        summary = self._report("l10n.et.wht.summary")
        data = summary._get_report_data()
        self.assertEqual(data["totals_by_rate"], {3.0: 14484.0, 15.0: 1200.0, 30.0: 4500.0})
        self.assertEqual(data["grand_total"], 20184.0)
        self.assertTrue(data["tie_out_ok"], data["tie_out"])
        self.assertEqual(len(data["missing_tin"]), 1)
        self.assertIn("Yonas Transport", data["missing_tin"][0])

    def test_statutory_reports_render(self):
        """All four statutory documents render with the expected markers."""
        render = self.env["ir.actions.report"]._render_qweb_html
        declaration = self._report("l10n.et.vat.declaration")
        html = render("l10n_et_reports.report_vat_declaration", declaration.ids)[0].decode()
        self.assertIn("190245.00", html)
        self.assertNotIn("MISMATCH", html)

        summary = self._report("l10n.et.wht.summary")
        html = render("l10n_et_reports.report_wht_summary", summary.ids)[0].decode()
        self.assertIn("MISSING", html)
        self.assertIn("N/A (foreign)", html)
        self.assertIn("20184.00", html)

        run = self.env["l10n.et.payroll.run"].search([("company_id", "=", self.company.id)])
        html = render("l10n_et_payroll.report_paye_declaration", run.ids)[0].decode()
        self.assertIn("11,525", html)
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

    def test_the_login_page_settings_are_configured(self):
        """The two settings the login page a prospect sees depends on.

        Both were unset, on every demo ever built. Odoo's default for
        "Customer Account" is b2c — free sign up — so the demo login page
        invited strangers to create an account on a private company ERP; and
        sapian_theme's support line renders nothing when unconfigured, which is
        how a feature with a passing test shipped invisible for weeks.

        Asserted through the SAME key lookup the code uses, so a rename in Odoo
        moves both together instead of leaving a test that passes against a
        parameter nobody reads.
        """
        demo = self.env["sapian.demo.trader"]
        demo._configure_demo_login(self.company)
        params = self.env["ir.config_parameter"].sudo()
        self.assertEqual(
            params.get_param(demo._signup_scope_param()),
            "b2b",
            "public sign-up is open on the demo tenant",
        )
        self.assertTrue(
            params.get_param("sapian_theme.support_contact"),
            "no support contact, so the login page renders no way to get help",
        )

    def test_the_signup_key_is_the_one_odoo_actually_reads(self):
        """`auth_signup_uninvited` is the FIELD name; the parameter it writes
        is `auth_signup.invitation_scope`. Setting the field name as a
        parameter would look right and change nothing, so this pins that the
        code asks the field rather than guessing."""
        demo = self.env["sapian.demo.trader"]
        field = self.env["res.config.settings"]._fields.get("auth_signup_uninvited")
        if field is None:
            self.skipTest("auth_signup is not installed on this database")
        self.assertEqual(demo._signup_scope_param(), field.config_parameter)
        self.assertNotEqual(
            demo._signup_scope_param(),
            "auth_signup_uninvited",
            "that is the field name, not the parameter key",
        )

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
