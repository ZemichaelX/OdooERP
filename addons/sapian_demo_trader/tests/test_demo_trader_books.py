# -*- coding: utf-8 -*-
"""The demo's books add up, and the numbers are printed so they can be read.

Someone will add these up — that is the whole reason this file exists. Every
figure the demo claims is asserted here AND logged at INFO with a SAPIAN-BOOKS
marker, so a GREEN run reports the numbers rather than merely staying quiet
about them. A test that only speaks when it fails leaves the figures to be
taken on trust between failures.
"""

import logging

from odoo.tests import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestDemoTraderBooks(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["sapian.demo.trader"]._provision_demo_tenant(
            company_name="Books Trading PLC"
        )
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company.ids))

    def _statement(self, model_name, date_from="2026-07-01", date_to="2026-07-31"):
        return (
            self.env[model_name]
            .with_company(self.company)
            .create(
                {
                    "company_id": self.company.id,
                    "date_from": date_from,
                    "date_to": date_to,
                }
            )
        )

    def _section_total(self, data, key):
        """One section's total, by key.

        `_build_sections` returns a flat list of dicts carrying `key`, `label`,
        `accounts` and `total` — revenue and cost of sales are SECTIONS, not
        top-level keys on the report data, which is worth stating because
        reading them off the top level raises KeyError rather than returning a
        wrong number.
        """
        for section in data["sections"]:
            if section.get("key") == key:
                return section["total"]
        self.fail("the statement has no %s section" % key)
        return None

    # ---- 1. cost of sales is the cost of the goods that were sold ----------

    def test_cost_of_sales_is_not_zero_and_gross_profit_is_not_revenue(self):
        """THE DEFECT, stated as an assertion.

        A trading company sold 115,300 birr of construction materials and it
        cost nothing. The report was faithful; the books were wrong, because
        every product sat in the default category whose valuation is periodic.
        """
        data = self._statement("l10n.et.profit.loss")._get_report_data()
        revenue = self._section_total(data, "revenue")
        cogs = self._section_total(data, "cost_of_sales")
        gross = data["gross_profit"]
        net = data["net_profit"]
        _logger.info(
            "SAPIAN-BOOKS P&L 2026-07 revenue=%.2f cost_of_sales=%.2f "
            "gross_profit=%.2f net_profit=%.2f operating=%.2f",
            revenue,
            cogs,
            gross,
            net,
            gross - net,
        )
        self.assertGreater(
            cogs,
            0.0,
            "Cost of sales is zero: the company sold goods that cost nothing, "
            "which is the defect this module was fixed for.",
        )
        self.assertNotAlmostEqual(
            gross,
            revenue,
            2,
            msg="Gross profit equals revenue, so nothing was charged against "
            "the goods that left the warehouse.",
        )
        self.assertAlmostEqual(
            gross,
            revenue - cogs,
            2,
            msg="Gross profit is not revenue minus cost of sales.",
        )

    def test_the_month_is_profitable_at_a_traders_margin(self):
        """Believable, not spectacular.

        The sourced costs and prices are untouched, so the gross margin is
        whatever the market gives — roughly 9% on building materials. What was
        changed is VOLUME. A net margin in double figures would be the same
        kind of lie as a cost of sales of zero, in the other direction.
        """
        data = self._statement("l10n.et.profit.loss")._get_report_data()
        revenue = self._section_total(data, "revenue")
        gross, net = data["gross_profit"], data["net_profit"]
        gross_margin = gross / revenue if revenue else 0.0
        net_margin = net / revenue if revenue else 0.0
        _logger.info(
            "SAPIAN-BOOKS MARGINS gross=%.3f%% net=%.3f%%",
            gross_margin * 100,
            net_margin * 100,
        )
        self.assertGreater(net, 0.0, "The demo month makes a loss.")
        self.assertLess(
            net_margin,
            0.10,
            "A net margin of 10%+ is not what a materials trader earns; the "
            "demo has drifted into flattery.",
        )
        self.assertGreater(
            gross,
            0.0,
            "Gross profit must cover the operating cost for the month to stand up.",
        )

    # ---- 2 & 3. the balance sheet ------------------------------------------

    def test_the_balance_sheet_balances_and_agrees_with_the_profit_and_loss(self):
        data = self._statement("l10n.et.balance.sheet")._get_report_data()
        assets = data["total_assets"]
        equity_and_liabilities = data["total_liabilities_and_equity"]
        identity = data["tie_out"][0]
        cross = data["tie_out"][1]
        _logger.info(
            "SAPIAN-BOOKS BS 2026-07-31 assets=%.2f liabilities_and_equity=%.2f "
            "difference=%.2f result=%.2f pl_says=%.2f",
            assets,
            equity_and_liabilities,
            identity["difference"],
            cross["report_total"],
            cross["gl_total"],
        )
        self.assertAlmostEqual(identity["difference"], 0.0, 2, msg="It does not balance.")
        self.assertAlmostEqual(
            cross["difference"],
            0.0,
            2,
            msg="The balance sheet's result for the period disagrees with the "
            "profit and loss.",
        )

    def test_there_is_money_in_the_bank(self):
        """Bank and Cash read 0.00 while six invoices showed as paid."""
        data = self._statement("l10n.et.balance.sheet")._get_report_data()
        total = self._section_total(data, "cash")
        _logger.info("SAPIAN-BOOKS BANK cash_and_bank=%.2f", total)
        self.assertGreater(
            total,
            0.0,
            "Bank and Cash is not positive: the company has no money anywhere, "
            "yet its invoices are settled.",
        )

    def test_goods_in_transit_does_not_carry_the_months_purchases(self):
        """230100 is a current asset, not a bucket for every vendor bill line."""
        account = self.env["account.account"].search(
            [
                *self.env["account.account"]._check_company_domain(self.company),
                ("code", "=", "230100"),
            ],
            limit=1,
        )
        self.assertTrue(account, "230100 Goods in Transit is missing from the chart")
        lines = self.env["account.move.line"].search(
            [
                ("account_id", "=", account.id),
                ("company_id", "=", self.company.id),
                ("parent_state", "=", "posted"),
            ]
        )
        balance = sum(lines.mapped("debit")) - sum(lines.mapped("credit"))
        _logger.info("SAPIAN-BOOKS GOODS_IN_TRANSIT balance=%.2f lines=%d", balance, len(lines))
        self.assertAlmostEqual(
            balance,
            0.0,
            2,
            msg="230100 Goods in Transit still carries the month's purchases "
            "instead of them clearing into stock or expense.",
        )

    def test_the_staff_were_actually_paid(self):
        account = self.company.sudo().l10n_et_net_wages_account_id
        self.assertTrue(account, "no net wages account configured")
        lines = self.env["account.move.line"].search(
            [
                ("account_id", "=", account.id),
                ("company_id", "=", self.company.id),
                ("parent_state", "=", "posted"),
            ]
        )
        owing = sum(lines.mapped("credit")) - sum(lines.mapped("debit"))
        _logger.info("SAPIAN-BOOKS SALARY_PAYABLE outstanding=%.2f", owing)
        self.assertAlmostEqual(
            owing,
            0.0,
            2,
            msg="Payroll was run and posted but never paid; the net wages "
            "account still owes the staff.",
        )

    # ---- 4. one product, all the way through -------------------------------

    def test_one_product_traced_through_purchase_and_sale(self):
        """hcb_20: opening + bought - sold = on hand, and none of them equal.

        Deliberately short of what July sells, so the closing figure is not the
        opening figure by coincidence and not the purchase by coincidence
        either.
        """
        product = self.env["product.product"].search(
            [
                ("name", "ilike", "HCB 20"),
                ("company_id", "in", (False, self.company.id)),
            ],
            limit=1,
        )
        self.assertTrue(product, "HCB 20 is not in the catalogue")
        product = product.with_company(self.company)

        moves = self.env["stock.move"].search(
            [
                ("product_id", "=", product.id),
                ("company_id", "=", self.company.id),
                ("state", "=", "done"),
            ]
        )
        received = sum(
            m.product_uom._compute_quantity(m.quantity, product.uom_id)
            for m in moves
            if m.location_dest_id.usage == "internal" and m.location_id.usage != "internal"
        )
        delivered = sum(
            m.product_uom._compute_quantity(m.quantity, product.uom_id)
            for m in moves
            if m.location_id.usage == "internal" and m.location_dest_id.usage != "internal"
        )
        on_hand = product.qty_available
        _logger.info(
            "SAPIAN-BOOKS TRACE %s in=%.2f out=%.2f on_hand=%.2f unit_cost=%.2f",
            product.name,
            received,
            delivered,
            on_hand,
            product.standard_price,
        )
        self.assertGreater(received, 0.0, "nothing was ever received into stock")
        self.assertGreater(delivered, 0.0, "nothing was ever delivered out of stock")
        self.assertAlmostEqual(
            on_hand,
            received - delivered,
            2,
            msg="Quantity on hand is not what went in minus what went out.",
        )
        self.assertGreater(
            on_hand, 0.0, "The month ends with no blocks on hand, which is not the story."
        )

    def test_stock_on_the_balance_sheet_is_not_zero(self):
        """Quantities without value would pass every quantity check and still
        leave the balance sheet wrong."""
        data = self._statement("l10n.et.balance.sheet")._get_report_data()
        # NAME THE ACCOUNTS, do not just report the total. The first green run
        # measured current_assets = -102,377.00, and a negative current-assets
        # line is the kind of thing an accountant spots in five seconds. A total
        # on its own cannot say which account made it negative, and guessing
        # from the chart would be a story rather than a measurement.
        for section in data["sections"]:
            if section.get("key") == "current_assets":
                _logger.info("SAPIAN-BOOKS STOCK current_assets=%.2f", section["total"])
                for row in section["accounts"]:
                    _logger.info(
                        "SAPIAN-BOOKS CURRENT_ASSET %s %s = %.2f",
                        row["code"],
                        row["name"],
                        row["amount"],
                    )
        account = self.env["account.account"].search(
            [
                *self.env["account.account"]._check_company_domain(self.company),
                ("code", "=", "235100"),
            ],
            limit=1,
        )
        self.assertTrue(account, "235100 Stock is missing from the chart")
        lines = self.env["account.move.line"].search(
            [
                ("account_id", "=", account.id),
                ("company_id", "=", self.company.id),
                ("parent_state", "=", "posted"),
            ]
        )
        balance = sum(lines.mapped("debit")) - sum(lines.mapped("credit"))
        _logger.info("SAPIAN-BOOKS STOCK_VALUATION 235100=%.2f", balance)
        self.assertGreater(
            balance,
            0.0,
            "Stock has quantities but no value: the opening inventory posted "
            "no accounting entry, so the balance sheet cannot agree with the "
            "warehouse.",
        )

    # ---- 5. products are configured ----------------------------------------

    def test_every_product_has_a_category_that_is_not_the_default(self):
        products = self.env["product.product"].search(
            [("company_id", "in", (False, self.company.id))]
        )
        default = self.env.ref("product.product_category_all", raise_if_not_found=False)
        ours = (
            products.filtered(lambda p: p.categ_id == default) if default else products.browse()
        )
        _logger.info(
            "SAPIAN-BOOKS CATEGORIES products=%d in_default=%d",
            len(products),
            len(ours),
        )
        self.assertFalse(
            ours.mapped("name"),
            "These products sit in the default 'All' category, which values "
            "stock periodically and posts no cost of sales: %s"
            % ", ".join(ours.mapped("name")[:10]),
        )
