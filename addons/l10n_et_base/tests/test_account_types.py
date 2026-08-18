# -*- coding: utf-8 -*-
"""The Ethiopian chart must be typed so a profit & loss can show gross profit.

Core `l10n_et` types **every** expense account `expense` — measured on the live
chart: 58 of 58, and `expense_direct_cost` count zero. That is not a reporting
inconvenience, it is a defect in the chart: on this chart **no** profit & loss can
separate cost of sales from operating expenses. Not ours, not OCA's, not
`base_accounting_kit`'s, not Odoo Enterprise's.

So the grouping is fixed **in the chart, once**, rather than as prefix rules
buried inside one report. Every report that reads account types inherits it,
including reports nobody has written yet.

WHY THE RULES ARE THREE DIGITS AND NOT TWO
------------------------------------------
The first draft of this mapping used two-digit prefixes, and `63` swept up
`632100 Pre-construction activities`, `632200 Construction of buildings` and
`632400 Construction of infrastructure` — **capital work, not depreciation**.
Typed `expense_depreciation` they would have sat in the depreciation line of
every statement forever, invisibly. `test_construction_is_not_depreciation`
exists to keep that mistake from coming back.

WHY 592100 IS DELIBERATELY LEFT ALONE
-------------------------------------
`592100 "Other"` has a name that says nothing, and only its code range argues for
cost of sales. An account typed by code range alone, whose name gives no
corroboration, is exactly where a silent misclassification lives. It stays
unclassified and NAMED until Zemichael's accountants answer — see
`ACCOUNTS_AWAITING_CLASSIFICATION`.
"""

from odoo.tests import tagged

from odoo.addons.l10n_et_base.models.template_et import (
    ACCOUNTS_AWAITING_CLASSIFICATION,
    CORE_ACCOUNT_FIXES,
)

from .common import L10nEtBaseCommon

COST_OF_SALES = ("511100", "590100", "591100", "593100")
DEPRECIATION = ("631100", "631300", "631400", "631500")
CONSTRUCTION = ("632100", "632200", "632400")


@tagged("post_install", "-at_install")
class TestEtAccountTypes(L10nEtBaseCommon):
    """Typed so the statements can group without hand-mapping every account."""

    def _account(self, code):
        account = (
            self.env["account.account"]
            .with_company(self.company)
            .search(
                [
                    *self.env["account.account"]._check_company_domain(self.company),
                    ("code", "=", code),
                ],
                limit=1,
            )
        )
        self.assertTrue(account, "Account %s is not on this chart." % code)
        return account

    def test_cost_of_sales_accounts_are_typed_direct_cost(self):
        """Without this there is no gross profit line on any report."""
        for code in COST_OF_SALES:
            account = self._account(code)
            self.assertEqual(
                account.account_type,
                "expense_direct_cost",
                "%s (%s) is typed %r, so it lands in operating expenses and gross "
                "profit cannot be computed." % (code, account.name, account.account_type),
            )

    def test_depreciation_accounts_are_typed_depreciation(self):
        for code in DEPRECIATION:
            account = self._account(code)
            self.assertEqual(
                account.account_type,
                "expense_depreciation",
                "%s (%s) is typed %r." % (code, account.name, account.account_type),
            )

    def test_construction_is_not_depreciation(self):
        """The two-digit trap. Capital work must never be depreciation.

        This passes BEFORE the fix as well as after — it is a regression guard,
        not a red-proof test, and it is the one that would catch a careless
        widening of the rule back to `63`.
        """
        for code in CONSTRUCTION:
            account = self._account(code)
            self.assertNotEqual(
                account.account_type,
                "expense_depreciation",
                "%s (%s) is capital work, not depreciation. A two-digit `63` rule "
                "sweeps it up and it then sits in the depreciation line of every "
                "statement." % (code, account.name),
            )

    def test_592100_is_left_unclassified_and_named(self):
        """It must stay a question, not quietly become an answer."""
        self.assertIn(
            "592100",
            ACCOUNTS_AWAITING_CLASSIFICATION,
            "592100 must be registered as awaiting classification, so the profit & "
            "loss can name it as unclassified instead of absorbing it.",
        )
        self.assertNotIn(
            "592100",
            CORE_ACCOUNT_FIXES,
            "592100 must NOT be typed until the accountants answer.",
        )
        self.assertEqual(
            self._account("592100").account_type,
            "expense",
            "592100 has been classified without an answer from the accountants.",
        )

    def test_the_chart_can_now_express_a_gross_profit(self):
        """The whole point, asserted as a property of the chart rather than a list."""
        accounts = (
            self.env["account.account"]
            .with_company(self.company)
            .search(
                [
                    *self.env["account.account"]._check_company_domain(self.company),
                    ("account_type", "=", "expense_direct_cost"),
                ]
            )
        )
        self.assertTrue(
            accounts,
            "No account on this chart is typed expense_direct_cost, so every profit "
            "& loss built on it — ours or anyone's — must report revenue with no "
            "cost of sales.",
        )
