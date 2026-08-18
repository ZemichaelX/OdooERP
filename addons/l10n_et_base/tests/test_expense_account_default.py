# -*- coding: utf-8 -*-
"""The default expense account must be an expense account, not a transit asset.

Core `l10n_et` maps the company's default expense account to `230100 Goods in
Transit`, an ``asset_current`` account (`l10n_et/models/template_et.py`, the
``expense_account_id`` key of ``_get_et_res_company``). Odoo's generic chart
loader then propagates that into ``ir.default`` for
``product.category.property_account_expense_categ_id``, so a product carrying no
account of its own — which is every product a client imports — books its
purchases into a current asset.

The consequence is not cosmetic and it is not detectable from inside the ledger:
the books still balance, because a balanced ledger cannot tell a misclassified
debit from a correct one. What breaks is the profit & loss account, which shows
revenue with no cost of sales, and the balance sheet, which carries a transit
balance that only grows. Measured on a demo tenant before this fix:
`230100` at 453,800.00, `STJ` empty, and reported profit overstated by 54,000.00
for a single 54,000.00 purchase.

These tests are the guard for defect register entry 26. Each asserts the
POSITIVE — that the resolved account is an expense account and that the profit &
loss figure moves — rather than the absence of an error, so none of them can pass
by the work not happening.
"""

from odoo.tests import tagged

from .common import L10nEtBaseCommon

# Account types that belong in the profit & loss statement's cost side.
EXPENSE_TYPES = ("expense", "expense_direct_cost", "expense_depreciation")


@tagged("post_install", "-at_install")
class TestEtExpenseAccountDefault(L10nEtBaseCommon):
    """Guard: an Ethiopian company's purchases must reach cost of sales."""

    def _profit_and_loss(self):
        """Net profit derived from posted lines, the way flow (m) derived it.

        The product ships no P&L report (defect register entry 27), so the
        statement is computed here from account types. That is deliberate: this
        test asserts the figure a P&L WOULD show, which is the thing entry 26
        actually breaks.
        """
        lines = self.env["account.move.line"].search(
            [
                ("parent_state", "=", "posted"),
                ("company_id", "=", self.company.id),
            ]
        )
        income = sum(
            line.balance
            for line in lines
            if line.account_id.account_type in ("income", "income_other")
        )
        expense = sum(
            line.balance for line in lines if line.account_id.account_type in EXPENSE_TYPES
        )
        return -income - expense

    def test_company_default_expense_account_is_an_expense_account(self):
        """The company's default expense account must be typed as an expense."""
        account = self.company.expense_account_id
        self.assertTrue(
            account,
            "The Ethiopian chart must set a default expense account on the company.",
        )
        self.assertIn(
            account.account_type,
            EXPENSE_TYPES,
            "The company's default expense account is %s (%s), typed %r. A purchase "
            "booked there never reaches the profit & loss account, so the P&L shows "
            "revenue with no cost of sales."
            % (account.code, account.name, account.account_type),
        )

    def test_product_without_its_own_account_resolves_to_an_expense_account(self):
        """A product with no account of its own is the client's real case.

        Asserted through ``_get_product_accounts`` — the same API the invoice line
        uses — rather than by reading ``ir.default`` directly. The resolution
        chain is product account → category property → ``company.expense_account_id``,
        and which link supplies the answer is an implementation detail; what
        matters is the account a real bill line would land in.
        """
        product = self.product_goods.with_company(self.company)
        self.assertFalse(
            product.property_account_expense_id,
            "Fixture guard: this product must carry no expense account of its own, "
            "or the test would prove nothing about the chart's default.",
        )
        account = product._get_product_accounts()["expense"]
        self.assertTrue(
            account,
            "A product with no account of its own resolves to no expense account "
            "at all, so a vendor bill has nowhere to post.",
        )
        self.assertIn(
            account.account_type,
            EXPENSE_TYPES,
            "Products with no account of their own resolve to %s (%s), typed %r."
            % (account.code, account.name, account.account_type),
        )

    def test_posted_vendor_bill_lands_in_cost_of_sales(self):
        """The guard itself: post a bill and read the account it landed in."""
        bill = self._create_bill(self.partner_compliant, [(self.product_goods, 54000.0)])
        product_lines = bill.line_ids.filtered(lambda line: line.display_type == "product")
        self.assertEqual(len(product_lines), 1, "Expected exactly one product line.")
        account = product_lines.account_id
        self.assertIn(
            account.account_type,
            EXPENSE_TYPES,
            "A posted vendor bill for 54,000.00 of goods landed in %s (%s), typed %r, "
            "instead of cost of sales." % (account.code, account.name, account.account_type),
        )

    # ---- the existing-company path -------------------------------------
    #
    # A template change applies at INSTALL and is skipped at UPGRADE, so the
    # tests above would stay green on a database that still had the defect.
    # These three exercise the repair path the migration calls.

    def _transit_account(self):
        return (
            self.env["account.chart.template"]
            .with_company(self.company)
            .ref("l10n_et2301", raise_if_not_found=False)
        )

    def _put_company_back_on_the_transit_default(self):
        """Recreate the pre-fix state, so the repair has something to repair."""
        transit = self._transit_account()
        self.assertTrue(transit, "The core transit account must exist to test against.")
        self.company.expense_account_id = transit
        self.env["ir.default"].sudo().set(
            "product.category",
            "property_account_expense_categ_id",
            transit.id,
            company_id=self.company.id,
        )
        return transit

    def test_existing_company_on_the_core_default_is_moved(self):
        """The repair must move a company that loaded the chart before this fix."""
        transit = self._put_company_back_on_the_transit_default()
        self.assertEqual(
            self.company.expense_account_id,
            transit,
            "Guard: the company must actually be on the transit account first, or "
            "this test proves nothing.",
        )
        moved = self.env["account.chart.template"]._l10n_et_base_fix_default_expense_account(
            self.company
        )
        self.assertIn(
            self.company,
            moved,
            "The repair reported no company moved, so an upgraded tenant would "
            "keep the defect while the upgrade reported success.",
        )
        self.assertIn(self.company.expense_account_id.account_type, EXPENSE_TYPES)
        category_default = (
            self.env["ir.default"]
            .sudo()
            ._get(
                "product.category",
                "property_account_expense_categ_id",
                company_id=self.company.id,
            )
        )
        self.assertEqual(
            category_default,
            self.company.expense_account_id.id,
            "The product-category default still points at the old account.",
        )

    def test_the_repair_is_idempotent(self):
        """Running it twice must not report a second move."""
        self._put_company_back_on_the_transit_default()
        chart_template = self.env["account.chart.template"]
        chart_template._l10n_et_base_fix_default_expense_account(self.company)
        again = chart_template._l10n_et_base_fix_default_expense_account(self.company)
        self.assertFalse(
            again,
            "A second run reported work done, so the repair is not idempotent and "
            "every upgrade would rewrite the client's setting.",
        )

    def test_a_company_that_chose_its_own_account_is_left_alone(self):
        """This is a defaulting fix, not an opinion about the client's chart."""
        chosen = self.env["account.account"].create(
            {
                "name": "Client's own purchases account",
                "code": "511900",
                "account_type": "expense",
            }
        )
        self.company.expense_account_id = chosen
        moved = self.env["account.chart.template"]._l10n_et_base_fix_default_expense_account(
            self.company
        )
        self.assertEqual(
            self.company.expense_account_id,
            chosen,
            "The repair overwrote an expense account the client had chosen.",
        )
        self.assertNotIn(self.company, moved)

    def test_posted_vendor_bill_moves_the_profit_and_loss(self):
        """The blast radius: the P&L must move by the amount of the purchase."""
        before = self._profit_and_loss()
        amount = 54000.0
        self._create_bill(self.partner_compliant, [(self.product_goods, amount)])
        after = self._profit_and_loss()
        self.assertAlmostEqual(
            before - after,
            amount,
            2,
            msg="Posting a %.2f purchase moved the derived profit & loss by %.2f. A "
            "purchase that does not reach the P&L overstates profit by its own "
            "amount." % (amount, before - after),
        )
