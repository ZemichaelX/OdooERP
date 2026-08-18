# -*- coding: utf-8 -*-
"""The profit & loss statement, and the two checks that make it trustworthy.

Odoo Community ships no P&L (defect register entry 27) and no OCA repository
supplies one, so until this model existed a client could not see whether the
business made money. A statement nobody can check is worse than no statement,
because it invites trust it has not earned — so half of these tests exist to
prove the checks GO RED, not that they go green.

Goldens for the July-2026 fixture in ``common.py``, hand-computed:

* revenue          10,000.00 — the single 10,000 sale invoice
* cost of sales    73,000.00 — the 50,000 + 15,000 + 8,000 vendor bills, which
  land in ``511100 Cost of Goods and Services`` because ``l10n_et_base`` moved
  the company's default expense account off ``230100 Goods in Transit`` (entry
  26) and typed 511100 ``expense_direct_cost`` (entry 27's chart half).
* gross profit    −63,000.00
* net profit      −63,000.00 — no operating-expense or depreciation movement

Neither figure was available before those two fixes: every bill posted to a
current asset, and every expense account carried the same type, so no statement
could show a cost-of-sales line at all.
"""

import base64
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from .common import L10nEtReportsCommon

REVENUE = 10000.0
COST_OF_SALES = 73000.0
GROSS_PROFIT = -63000.0
NET_PROFIT = -63000.0


@tagged("post_install", "-at_install")
class TestProfitLoss(L10nEtReportsCommon):
    """The statement, and both of its self-checks in both directions."""

    def setUp(self):
        super().setUp()
        self.statement = self._make_report("l10n.et.profit.loss")

    def _render(self):
        """The rendered document, which is what the client actually reads."""
        return (
            self.env["ir.actions.report"]
            ._render_qweb_html("l10n_et_reports.report_profit_loss", self.statement.ids)[0]
            .decode()
        )

    def _section(self, data, key):
        for section in data["sections"]:
            if section["key"] == key:
                return section
        self.fail("Section %r is absent from the statement." % key)

    # ---- the statement itself --------------------------------------------

    def test_revenue_and_cost_of_sales_are_separated(self):
        """A gross profit line — the thing the chart fix made possible.

        Before ``l10n_et_base`` typed 511100 ``expense_direct_cost``, all 58 of
        the chart's expense accounts shared one type and NO report could split
        cost of sales from operating expense.
        """
        data = self.statement._get_report_data()
        self.assertAlmostEqual(self._section(data, "revenue")["total"], REVENUE, 2)
        self.assertAlmostEqual(
            self._section(data, "cost_of_sales")["total"],
            COST_OF_SALES,
            2,
            msg="Cost of sales is empty: the vendor bills did not reach an "
            "account typed 'Cost of Revenue'.",
        )
        self.assertAlmostEqual(data["gross_profit"], GROSS_PROFIT, 2)
        self.assertAlmostEqual(self.statement.gross_profit, GROSS_PROFIT, 2)

    def test_net_profit_matches_the_hand_computed_golden(self):
        """The bottom line, from posted journal items."""
        self.assertAlmostEqual(self.statement.net_profit, NET_PROFIT, 2)

    def test_the_statement_is_a_live_window_not_a_snapshot(self):
        """A later posting inside the period moves the figures without a rerun."""
        before = self.statement.net_profit
        self._post_move("out_invoice", self.partner_compliant, self.product_goods, 4000)
        self.statement.invalidate_recordset()
        self.assertAlmostEqual(
            self.statement.net_profit,
            before + 4000.0,
            2,
            msg="A 4,000.00 sale posted into the period did not move net profit, "
            "so the statement is reading a stale figure.",
        )

    def test_a_posting_outside_the_period_is_excluded(self):
        """The period window is real, not decorative."""
        before = self.statement.net_profit
        self._post_move(
            "out_invoice",
            self.partner_compliant,
            self.product_goods,
            9000,
            invoice_date="2026-08-05",
        )
        self.statement.invalidate_recordset()
        self.assertAlmostEqual(self.statement.net_profit, before, 2)

    def test_another_company_does_not_leak_in(self):
        """Multi-company isolation (CLAUDE.md rule 3)."""
        other = self.env["res.company"].create({"name": "Other Co"})
        account = self.env["account.account"].create(
            {
                "name": "Other Co sales",
                "code": "400000",
                "account_type": "income",
                "company_ids": [Command.link(other.id)],
            }
        )
        journal = self.env["account.journal"].create(
            {"name": "Other Misc", "code": "OMSC", "type": "general", "company_id": other.id}
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
                            {"account_id": account.id, "credit": 777.0, "name": "leak"}
                        ),
                        Command.create(
                            {"account_id": account.id, "debit": 777.0, "name": "leak"}
                        ),
                    ],
                }
            )
        )
        move.action_post()
        self.statement.invalidate_recordset()
        self.assertAlmostEqual(self.statement.net_profit, NET_PROFIT, 2)
        self.assertNotIn(
            "400000",
            [
                row["code"]
                for row in self._section(self.statement._get_report_data(), "revenue")[
                    "accounts"
                ]
            ],
        )

    # ---- check 1: net profit vs the ledger -------------------------------

    def test_net_profit_ties_to_the_ledger(self):
        """The statement total against an independent search over the GL."""
        data = self.statement._get_report_data()
        tie = data["tie_out"][0]
        self.assertAlmostEqual(tie["report_total"], NET_PROFIT, 2)
        self.assertAlmostEqual(tie["gl_total"], NET_PROFIT, 2)
        self.assertTrue(tie["ok"], "Net profit does not tie to the general ledger.")

    def test_the_ledger_check_goes_red_when_a_section_loses_its_type(self):
        """PROVE IT DISCRIMINATES. Drop 'income' from the section table.

        The revenue accounts then belong to no line, so their 10,000.00 falls
        out of net profit — and the difference against the ledger is exactly
        that. This is the failure a P&L cannot be trusted without.
        """
        broken = [
            spec
            for spec in self.env["l10n.et.profit.loss"]._statement_sections()
            if spec["key"] != "revenue"
        ]
        with patch.object(type(self.statement), "_statement_sections", lambda self: broken):
            data = self.statement._get_report_data()
            tie = data["tie_out"][0]
        self.assertFalse(tie["ok"], "Losing every revenue account still tied out.")
        self.assertAlmostEqual(
            tie["difference"],
            REVENUE,
            2,
            msg="The ledger check reported a %.2f difference; dropping the "
            "revenue section should move it by exactly %.2f." % (tie["difference"], REVENUE),
        )

    def test_the_ledger_check_is_not_a_restatement_of_the_coverage_check(self):
        """An amount that goes missing with every account still classified.

        The two checks must fail on different things, or the second is
        decoration. Here the section partition is untouched — every account is
        still placed, so coverage stays exactly as clean as it was — while a row
        filter silently eats the 73,000.00 cost-of-sales account. That is a real
        shape of bug: the statement decides what to *display* and the total
        quietly follows.

        Note what does NOT work as a break, because it was tried: flipping a
        section's ``credit_positive`` negates twice — once when the row amount is
        made report-positive, once when the section is added to net profit — and
        cancels exactly. It misprints the face of the statement (revenue shown
        negative) without moving the total, so this check cannot see it and is
        not claimed to.
        """
        original = type(self.statement)._section_rows

        def eat_cost_of_sales(inner_self, accounts, balances, credit_positive):
            rows = original(inner_self, accounts, balances, credit_positive)
            return [row for row in rows if row["code"] != "511100"]

        clean = self.statement._get_report_data()["classification"]["classified"]
        with patch.object(type(self.statement), "_section_rows", eat_cost_of_sales):
            data = self.statement._get_report_data()
        self.assertFalse(
            data["tie_out"][0]["ok"],
            "73,000.00 of cost of sales vanished from the statement and it still "
            "reported that it ties to the ledger.",
        )
        self.assertAlmostEqual(data["tie_out"][0]["difference"], -COST_OF_SALES, 2)
        self.assertEqual(
            data["classification"]["classified"],
            clean,
            "The coverage count moved, so this break did not isolate the ledger "
            "check from it.",
        )

    # ---- check 2: every account accounted for ----------------------------

    def test_the_held_back_account_is_reported_by_name_every_printing(self):
        """592100 'Other' is unclassified until the accountants answer.

        Its name gives no corroboration for the 59x cost-of-sales range, so
        typing it by code range alone is exactly where a silent
        misclassification would live. Until somebody answers, every printing
        says so, by name.
        """
        data = self.statement._get_report_data()
        classification = data["classification"]
        self.assertFalse(classification["ok"])
        codes = [row["code"] for row in classification["unclassified"]]
        self.assertIn("592100", codes)
        self.assertIn("592100", classification["message"])
        self.assertIn("Other", classification["message"])
        self.assertEqual(
            classification["classified"] + len(classification["unclassified"]),
            classification["total"],
            "The counts do not add up, so the coverage line is decorative.",
        )

    def test_the_held_back_account_is_not_absorbed_into_operating_expenses(self):
        """Not swept into 'other expenses', where it would stop being a question."""
        data = self.statement._get_report_data()
        operating = self._section(data, "operating_expenses")
        self.assertNotIn("592100", [row["code"] for row in operating["accounts"]])
        awaiting = self._section(data, "awaiting_classification")
        self.assertIn("592100", [row["code"] for row in awaiting["accounts"]])

    def test_the_coverage_check_names_an_account_no_section_claims(self):
        """PROVE IT DISCRIMINATES. A type on no line is a CHART error.

        Dropping the depreciation section leaves four real accounts with a type
        the statement does not know. They must be named — not counted quietly
        into some nearby total.
        """
        broken = [
            spec
            for spec in self.env["l10n.et.profit.loss"]._statement_sections()
            if spec["key"] != "depreciation"
        ]
        with patch.object(type(self.statement), "_statement_sections", lambda self: broken):
            classification = self.statement._get_report_data()["classification"]
        self.assertFalse(classification["ok"])
        codes = [row["code"] for row in classification["unclassified"]]
        for code in ("631100", "631300", "631400", "631500"):
            self.assertIn(code, codes, "%s fell through the statement unreported." % code)
        self.assertIn("expense_depreciation", classification["message"])

    def test_a_chart_with_no_profit_and_loss_accounts_is_not_reported_ok(self):
        """An empty statement reconciles perfectly, and means nothing (rule 2).

        Zero against zero is the do-nothing path: if the chart had never been
        loaded, every total would tie. The coverage check refuses it.
        """
        bare = self.env["res.company"].create({"name": "Chartless PLC"})
        statement = self.env["l10n.et.profit.loss"].create(
            {"company_id": bare.id, "date_from": "2026-07-01", "date_to": "2026-07-31"}
        )
        data = statement._get_report_data()
        self.assertEqual(data["classification"]["total"], 0)
        self.assertFalse(
            data["tie_out_ok"],
            "A statement over a chart with no income or expense accounts "
            "reported that it ties.",
        )
        self.assertIn("no income or expense accounts", data["classification"]["message"])

    # ---- outputs ---------------------------------------------------------

    def test_pdf_shows_the_sections_the_totals_and_both_checks(self):
        """Read the rendered document, not the model that fed it."""
        self.company.partner_id.l10n_et_tin = "0099887766"
        html = self._render()
        self.assertIn("0099887766", html, "company TIN missing from the statement")
        self.assertIn("Cost of Sales", html)
        self.assertIn("Gross Profit", html)
        self.assertIn("NET PROFIT FOR THE PERIOD", html)
        self.assertIn("10000.00", html, "revenue missing")
        self.assertIn("73000.00", html, "cost of sales missing")
        self.assertIn("-63000.00", html, "net profit missing")
        self.assertIn("592100", html, "the unclassified account is not on the face")
        self.assertIn("UNCLASSIFIED", html)

    def test_the_banner_distinguishes_a_mismatch_from_an_unclassified_account(self):
        """ "Does not reconcile" must mean the amounts disagree, nothing else.

        The first rendered statement said "This statement does not reconcile"
        when it reconciled exactly and the only shortfall was `592100` waiting
        on the accountants. An accountant who reads that once and finds nothing
        wrong stops reading the banner, which is how the real mismatch gets
        missed later.
        """
        clean = self._render()
        self.assertIn("is not yet classified", clean)
        self.assertNotIn("does not reconcile to the general ledger", clean)

        original = type(self.statement)._section_rows

        def eat_cost_of_sales(inner_self, accounts, balances, credit_positive):
            rows = original(inner_self, accounts, balances, credit_positive)
            return [row for row in rows if row["code"] != "511100"]

        with patch.object(type(self.statement), "_section_rows", eat_cost_of_sales):
            broken = self._render()
        self.assertIn("does not reconcile to the general ledger", broken)
        self.assertIn("MISMATCH", broken)

    def test_csv_export_carries_the_totals_and_both_checks(self):
        self.statement.action_export_csv()
        content = base64.b64decode(self.statement.csv_export_file).decode()
        self.assertIn("Section,Code,Account,Amount", content)
        self.assertIn("Revenue,,TOTAL,10000.00", content)
        self.assertIn("Cost of Sales,,TOTAL,73000.00", content)
        self.assertIn("Gross Profit,,,-63000.00", content)
        self.assertIn("NET PROFIT,,,-63000.00", content)
        self.assertIn("Accounts classified", content)
        self.assertIn("592100", content)
        self.assertEqual(self.statement.csv_export_filename, "profit_loss_2026_07.csv")
