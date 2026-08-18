# -*- coding: utf-8 -*-
"""The balance sheet, and the three checks that make it trustworthy.

Goldens for the July-2026 fixture in ``common.py``, hand-computed as at
2026-07-31 with the result measured from 2026-07-01:

* receivables    11,500.00 — the 10,000 sale plus its 1,500 VAT
* input VAT      10,950.00 — 7,500 + 2,250 + 1,200 on the three bills
* TOTAL ASSETS   22,450.00
* liabilities    85,450.00 — supplier payables net of withholding, plus 7,200
  WHT payable and 1,500 output VAT payable
* equity accounts     0.00 — this fixture posts no share capital
* result for period −63,000.00 — the profit & loss figure for the same dates
* TOTAL LIABILITIES AND EQUITY  85,450.00 − 63,000.00 = **22,450.00**

The identity is the point: 22,450.00 both sides. Half of these tests exist to
prove the checks GO RED, because a balance sheet that always says it balances
is worse than none — it invites trust it has not earned.
"""

import base64
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from .common import L10nEtReportsCommon

RECEIVABLES = 11500.0
INPUT_VAT = 10950.0
TOTAL_ASSETS = 22450.0
TOTAL_LIABILITIES = 85450.0
RESULT_FOR_PERIOD = -63000.0
# The ET chart ships 35 asset + 12 liability + 3 equity accounts. A floor, not
# an equality: the accounting test fixtures add a few of their own.
MIN_BALANCE_SHEET_ACCOUNTS = 50


@tagged("post_install", "-at_install")
class TestBalanceSheet(L10nEtReportsCommon):
    """Position, identity, agreement with the P&L — each proved both ways."""

    def setUp(self):
        super().setUp()
        self.statement = self._make_report("l10n.et.balance.sheet")

    def _render(self):
        """The rendered document, which is what the client actually reads."""
        return (
            self.env["ir.actions.report"]
            ._render_qweb_html("l10n_et_reports.report_balance_sheet", self.statement.ids)[0]
            .decode()
        )

    def _section(self, data, key):
        for section in data["sections"]:
            if section["key"] == key:
                return section
        self.fail("Section %r is absent from the statement." % key)

    def _manual_entry(self, date, debit_ref, credit_ref, amount):
        """A posted manual journal entry between two chart accounts."""
        chart = self.env["account.chart.template"].with_company(self.company)
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": date,
                "company_id": self.company.id,
                "line_ids": [
                    Command.create(
                        {"account_id": chart.ref(debit_ref).id, "debit": amount, "name": "m"}
                    ),
                    Command.create(
                        {"account_id": chart.ref(credit_ref).id, "credit": amount, "name": "m"}
                    ),
                ],
            }
        )
        move.action_post()
        return move

    # ---- the statement itself --------------------------------------------

    def test_total_assets_matches_the_hand_computed_golden(self):
        data = self.statement._get_report_data()
        self.assertAlmostEqual(self._section(data, "receivables")["total"], RECEIVABLES, 2)
        self.assertAlmostEqual(self._section(data, "current_assets")["total"], INPUT_VAT, 2)
        self.assertAlmostEqual(data["total_assets"], TOTAL_ASSETS, 2)

    def test_total_liabilities_matches_the_hand_computed_golden(self):
        data = self.statement._get_report_data()
        self.assertAlmostEqual(data["total_liabilities"], TOTAL_LIABILITIES, 2)

    def test_the_statement_balances(self):
        """Assets = liabilities + equity + result. The whole point of it."""
        data = self.statement._get_report_data()
        self.assertAlmostEqual(data["total_assets"], TOTAL_ASSETS, 2)
        self.assertAlmostEqual(data["total_liabilities_and_equity"], TOTAL_ASSETS, 2)
        tie = data["tie_out"][0]
        self.assertTrue(tie["ok"], "The balance sheet does not balance.")
        self.assertAlmostEqual(tie["difference"], 0.0, 2)

    def test_it_is_a_position_not_a_flow(self):
        """An asset raised BEFORE date_from must still be on the statement.

        This is the guard for ``_statement_line_domain``. Reading the period the
        way the profit & loss does would drop every opening balance — and would
        still reconcile, because both sides of the identity would lose the same
        lines. Nothing would go red; the statement would just be wrong.
        """
        before = self.statement._get_report_data()["total_assets"]
        self._manual_entry("2026-06-15", "l10n_et2211", "l10n_et4001", 5000.0)
        self.statement.invalidate_recordset()
        data = self.statement._get_report_data()
        self.assertAlmostEqual(
            data["total_assets"],
            before + 5000.0,
            2,
            msg="A 5,000.00 asset raised before the period start is missing from "
            "the statement, so this is reading a period and calling it a position.",
        )
        self.assertTrue(data["tie_out"][0]["ok"], "It stopped balancing.")

    def test_an_earlier_result_is_brought_forward_not_counted_in_the_period(self):
        """Prior-year profit belongs in equity, not in this period's result."""
        self._post_move(
            "out_invoice",
            self.partner_compliant,
            self.product_goods,
            2000,
            invoice_date="2026-06-15",
        )
        self.statement.invalidate_recordset()
        data = self.statement._get_report_data()
        self.assertAlmostEqual(
            data["result_for_period"],
            RESULT_FOR_PERIOD,
            2,
            msg="A June sale leaked into July's result.",
        )
        self.assertNotAlmostEqual(data["brought_forward"], 0.0, 2)
        self.assertTrue(data["tie_out"][0]["ok"], "It stopped balancing.")

    def test_another_company_does_not_leak_in(self):
        """Multi-company isolation (CLAUDE.md rule 3)."""
        other = self.env["res.company"].create({"name": "Other Co BS"})
        account = self.env["account.account"].create(
            {
                "name": "Other Co bank",
                "code": "100999",
                "account_type": "asset_cash",
                "company_ids": [Command.link(other.id)],
            }
        )
        journal = self.env["account.journal"].create(
            {"name": "Other Misc BS", "code": "OMSB", "type": "general", "company_id": other.id}
        )
        move = (
            self.env["account.move"]
            .with_company(other)
            .create(
                {
                    "move_type": "entry",
                    "date": "2026-07-15",
                    "journal_id": journal.id,
                    "line_ids": [
                        Command.create(
                            {"account_id": account.id, "debit": 999.0, "name": "leak"}
                        ),
                        Command.create(
                            {"account_id": account.id, "credit": 999.0, "name": "leak"}
                        ),
                    ],
                }
            )
        )
        move.action_post()
        self.statement.invalidate_recordset()
        self.assertAlmostEqual(
            self.statement._get_report_data()["total_assets"], TOTAL_ASSETS, 2
        )

    # ---- check 1: it balances --------------------------------------------

    def test_the_balance_check_goes_red_when_a_section_loses_its_type(self):
        """PROVE IT DISCRIMINATES. Drop receivables from the section table.

        11,500.00 of assets then belongs to no line and falls out of the total,
        so the two sides differ by exactly that — while the result for the
        period, and therefore the agreement with the profit & loss, is untouched.
        """
        broken = [
            spec
            for spec in self.env["l10n.et.balance.sheet"]._statement_sections()
            if spec["key"] != "receivables"
        ]
        with patch.object(type(self.statement), "_statement_sections", lambda self: broken):
            data = self.statement._get_report_data()
        self.assertFalse(data["tie_out"][0]["ok"], "Losing every receivable still balanced.")
        self.assertAlmostEqual(data["tie_out"][0]["difference"], RECEIVABLES, 2)
        self.assertTrue(
            data["tie_out"][1]["ok"],
            "A missing asset section changed the agreement with the profit & loss, "
            "so the two checks are not independent.",
        )

    # ---- check 2: it agrees with the profit and loss ----------------------

    def test_the_result_for_the_period_agrees_with_the_profit_and_loss(self):
        """One set of books, not two opinions."""
        data = self.statement._get_report_data()
        self.assertAlmostEqual(data["result_for_period"], RESULT_FOR_PERIOD, 2)
        tie = data["tie_out"][1]
        self.assertAlmostEqual(tie["report_total"], RESULT_FOR_PERIOD, 2)
        self.assertAlmostEqual(tie["gl_total"], RESULT_FOR_PERIOD, 2)
        self.assertTrue(tie["ok"], "The two statements disagree about the period's result.")

    def test_the_cross_statement_check_goes_red_when_the_two_disagree(self):
        """PROVE IT DISCRIMINATES. Break the P&L, not the balance sheet.

        Dropping revenue from the profit & loss makes it report −73,000.00 while
        this statement, summing the ledger directly, still reports −63,000.00.
        The cross-statement check must catch the 10,000.00 gap — and the balance
        sheet must still balance, because its own arithmetic never used the P&L's
        figure. That asymmetry is what makes this a second check rather than a
        restatement of the first.
        """
        broken = [
            spec
            for spec in self.env["l10n.et.profit.loss"]._statement_sections()
            if spec["key"] != "revenue"
        ]
        with patch.object(
            self.env.registry["l10n.et.profit.loss"], "_statement_sections", lambda self: broken
        ):
            data = self.statement._get_report_data()
        tie = data["tie_out"][1]
        self.assertFalse(tie["ok"], "The two statements disagreed and nothing said so.")
        self.assertAlmostEqual(tie["difference"], -10000.0, 2)
        self.assertTrue(
            data["tie_out"][0]["ok"],
            "A broken profit & loss unbalanced the balance sheet, so the first "
            "check is not independent of the second.",
        )

    # ---- check 3: every account accounted for ----------------------------

    def test_every_balance_sheet_account_is_classified(self):
        """No held-back accounts on this side of the books today.

        `592100 Other` is an expense, so it belongs to the profit & loss's
        coverage line and not to this one — which is worth asserting, because a
        shared mixin that leaked the other statement's exception here would go
        unnoticed.
        """
        classification = self.statement._get_report_data()["classification"]
        self.assertTrue(classification["ok"], classification["message"])
        self.assertEqual(classification["unclassified"], [])
        self.assertGreaterEqual(classification["total"], MIN_BALANCE_SHEET_ACCOUNTS)
        self.assertIn("unclassified: none", classification["message"])

    def test_the_coverage_check_names_an_account_no_section_claims(self):
        """PROVE IT DISCRIMINATES, and that the amount check goes red with it."""
        broken = [
            spec
            for spec in self.env["l10n.et.balance.sheet"]._statement_sections()
            if spec["key"] != "receivables"
        ]
        with patch.object(type(self.statement), "_statement_sections", lambda self: broken):
            data = self.statement._get_report_data()
        classification = data["classification"]
        self.assertFalse(classification["ok"])
        self.assertIn("asset_receivable", classification["message"])
        self.assertFalse(
            data["tie_out_ok"],
            "An account fell off the statement and the overall verdict was still OK.",
        )

    def test_a_chart_with_no_balance_sheet_accounts_is_not_reported_ok(self):
        """An empty statement balances perfectly, and means nothing (rule 2)."""
        bare = self.env["res.company"].create({"name": "Chartless BS PLC"})
        statement = self.env["l10n.et.balance.sheet"].create(
            {"company_id": bare.id, "date_from": "2026-07-01", "date_to": "2026-07-31"}
        )
        data = statement._get_report_data()
        self.assertEqual(data["classification"]["total"], 0)
        self.assertAlmostEqual(data["total_assets"], 0.0, 2)
        self.assertFalse(
            data["tie_out_ok"],
            "A statement over a chart with no accounts reported that it balances.",
        )

    def test_off_balance_accounts_are_excluded_by_definition_and_said_so(self):
        """Excluded, but never invisible — the count is on the statement."""
        self.env["account.account"].create(
            {
                "name": "Guarantees given",
                "code": "900001",
                "account_type": "off_balance",
                "company_ids": [Command.link(self.company.id)],
            }
        )
        before = self.statement._get_report_data()
        self.statement.invalidate_recordset()
        data = self.statement._get_report_data()
        self.assertEqual(data["off_balance_accounts"], 1)
        self.assertEqual(
            data["classification"]["total"],
            before["classification"]["total"],
            "An off-balance-sheet account entered the balance sheet's coverage "
            "count, which would make the denominator meaningless.",
        )
        self.assertTrue(
            any("off-balance-sheet" in warning for warning in data["warnings"]),
            "Off-balance accounts exist and the statement said nothing about them.",
        )

    # ---- outputs ---------------------------------------------------------

    def test_pdf_shows_the_groups_the_totals_and_the_checks(self):
        """Read the rendered document, not the model that fed it."""
        self.company.partner_id.l10n_et_tin = "0099887766"
        html = self._render()
        self.assertIn("0099887766", html, "company TIN missing from the statement")
        for caption in ("Assets", "Liabilities", "Equity", "Receivables"):
            self.assertIn(caption, html, "%s caption missing" % caption)
        self.assertIn("TOTAL ASSETS", html)
        self.assertIn("TOTAL LIABILITIES AND EQUITY", html)
        self.assertIn("22450.00", html, "total assets missing")
        self.assertIn("-63000.00", html, "result for the period missing")
        self.assertIn("Result for the period", html)
        self.assertNotIn("MISMATCH", html)
        self.assertNotIn("does not balance", html)

    def test_the_pdf_says_so_when_it_does_not_balance(self):
        """The banner must mean what it says, in both directions.

        The clean render above asserts it does NOT say "does not balance"; this
        one asserts it does when the statement genuinely does not. A banner that
        only ever fires one way is decoration.
        """
        broken = [
            spec
            for spec in self.env["l10n.et.balance.sheet"]._statement_sections()
            if spec["key"] != "receivables"
        ]
        with patch.object(type(self.statement), "_statement_sections", lambda self: broken):
            html = self._render()
        self.assertIn("does not balance", html)
        self.assertIn("MISMATCH", html)

    def test_csv_export_carries_the_totals_and_the_checks(self):
        self.statement.action_export_csv()
        content = base64.b64decode(self.statement.csv_export_file).decode()
        self.assertIn("Group,Section,Code,Account,Amount", content)
        self.assertIn("TOTAL ASSETS,,,,22450.00", content)
        self.assertIn("TOTAL LIABILITIES AND EQUITY,,,,22450.00", content)
        self.assertIn("Result for the period,,,-63000.00", content)
        self.assertIn("Accounts classified", content)
        self.assertIn("OK", content)
        self.assertNotIn("MISMATCH", content)
        self.assertEqual(self.statement.csv_export_filename, "balance_sheet_2026_07.csv")
