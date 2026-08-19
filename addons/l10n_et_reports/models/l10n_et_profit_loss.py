# -*- coding: utf-8 -*-
"""Profit and loss statement, grouped by ACCOUNT TYPE.

Odoo Community ships no profit & loss statement (entry 27 of the internal
defect register), and
neither does any OCA repository we surveyed — `account_financial_report` has a
general ledger and a trial balance but no P&L or balance sheet, and `mis_builder`
ships an engine with zero templates. A client cannot see whether the business
made money. That is the reporting blocker this model clears.

**The grouping is not in this file.** Which account belongs on which line is
decided by the account's `account_type`, set once in the chart by
`l10n_et_base` (`CORE_ACCOUNT_FIXES`). This module only says which TYPE goes on
which LINE. That is deliberate: a prefix table buried in one report would fix
one report and hide the chart defect from every other, and it would have typed
`632100 Construction of buildings` as depreciation forever with nothing failing.

**Two checks on the face of the statement, and neither can pass by the work not
happening (CLAUDE.md rule 2).**

1. *Net profit vs the general ledger.* The statement's net profit is built from
   the section totals; the ledger figure is an independent search over the full
   period movement of every account whose `internal_group` is income or expense
   — Odoo's own classification, not ours. If a section's type list is wrong the
   two disagree by the amount that fell out.
2. *Accounts classified.* Every P&L account in the chart, against the accounts
   the statement placed, reported as `61 of 62 accounts classified` and naming
   the shortfall. An account the statement cannot name is NOT swept into "other
   expenses": it is left out of the totals so check 1 goes red as well, and it is
   printed by name so somebody has to answer for it.

`592100 Other` is such an account today — see `ACCOUNTS_AWAITING_CLASSIFICATION`
in `l10n_et_base`. It is placed in its own visible section and counted as
unclassified on every printing until the accountants classify it.
"""

from odoo import api, fields, models


class L10nEtProfitLoss(models.Model):
    _name = "l10n.et.profit.loss"
    _description = "Ethiopian Profit and Loss Statement"
    _inherit = ["l10n.et.statement.mixin"]
    _order = "date_from desc, id desc"

    # Odoo's own classification of what belongs in a profit & loss. Read from
    # `internal_group` rather than from `_statement_sections` below, so a type no
    # section claims is reported instead of silently ignored.
    _statement_internal_groups = ("income", "expense")
    _statement_account_label = "income or expense accounts"

    name = fields.Char(compute="_compute_name", store=True)
    gross_profit = fields.Monetary(
        compute="_compute_totals",
        help="Revenue less cost of sales. Requires the chart to type its cost "
        "accounts 'Cost of Revenue' — l10n_et_base does that for the Ethiopian "
        "chart, which core l10n_et does not.",
    )
    net_profit = fields.Monetary(
        compute="_compute_totals",
        help="Profit for the period: all income less all expense, live from "
        "posted journal items.",
    )
    tie_out_ok = fields.Boolean(
        string="Ties to the ledger",
        compute="_compute_totals",
        help="False when the statement does not reconcile to the general ledger, "
        "or when an account in the chart could not be placed on it.",
    )

    @api.depends("date_from", "company_id")
    def _compute_name(self):
        """Label, e.g. 'Profit and Loss 2026-07'."""
        for report in self:
            period = report.date_from and report.date_from.strftime("%Y-%m") or "?"
            report.name = self.env._("Profit and Loss %(period)s", period=period)

    @api.depends("date_from", "date_to", "company_id")
    def _compute_totals(self):
        """Live figures from posted moves — a period window, never a snapshot."""
        for report in self:
            data = report._get_report_data()
            report.gross_profit = data["gross_profit"]
            report.net_profit = data["net_profit"]
            report.tie_out_ok = data["tie_out_ok"]

    # ---- the face of the statement --------------------------------------

    def _statement_sections(self):
        """Which ACCOUNT TYPE prints on which LINE, in statement order.

        One reviewable table, and the only mapping this module owns. Everything
        about which account carries which type lives in the chart.
        """
        return [
            {
                "key": "revenue",
                "label": self.env._("Revenue"),
                "types": ("income",),
                "credit_positive": True,
            },
            {
                "key": "cost_of_sales",
                "label": self.env._("Cost of Sales"),
                "types": ("expense_direct_cost",),
                "credit_positive": False,
                "subtotal": self.env._("Gross Profit"),
            },
            {
                "key": "other_income",
                "label": self.env._("Other Income"),
                "types": ("income_other",),
                "credit_positive": True,
            },
            {
                "key": "operating_expenses",
                "label": self.env._("Operating Expenses"),
                "types": ("expense",),
                "credit_positive": False,
            },
            {
                "key": "depreciation",
                "label": self.env._("Depreciation and Amortisation"),
                "types": ("expense_depreciation",),
                "credit_positive": False,
            },
            {
                "key": "other_expenses",
                "label": self.env._("Other Expenses"),
                "types": ("expense_other",),
                "credit_positive": False,
            },
        ]

    def _get_report_data(self):
        """Full statement dataset for rendering, export and tests."""
        self.ensure_one()
        rounding = self.currency_id.round
        accounts = self._statement_accounts()
        balances = self._account_balances(accounts)
        awaiting = self._awaiting_classification_accounts(accounts)
        sections, placed, held_back = self._build_sections(accounts, balances, awaiting)

        # Net profit is accumulated from the SECTION TOTALS, never from a raw sum
        # over the accounts: the tie-out below sums the ledger independently, and
        # if both sides came from the same figure it could not disagree.
        net_profit = 0.0
        gross_profit = 0.0
        for section in sections:
            if section["key"] == "awaiting_classification":
                # Each held-back account carries its own sign — an unclassified
                # income account is not an expense.
                for row in section["accounts"]:
                    net_profit += row["amount"] if row["credit_positive"] else -row["amount"]
                continue
            net_profit += section["total"] if section["credit_positive"] else -section["total"]
            if section.get("subtotal"):
                gross_profit = rounding(net_profit)
                section["subtotal_amount"] = gross_profit
        net_profit = rounding(net_profit)

        classification = self._classification_check(accounts, placed, held_back)
        tie_out = [
            self._tie_out_row(
                self.env._("Net profit vs income and expense accounts in the GL"),
                net_profit,
                accounts,
                credit_positive=True,
            )
        ]
        warnings = []
        if not classification["ok"]:
            warnings.append(classification["message"])
        return {
            "sections": sections,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "classification": classification,
            "tie_out": tie_out,
            "tie_out_ok": all(row["ok"] for row in tie_out) and classification["ok"],
            "warnings": warnings,
        }

    # ---- outputs ---------------------------------------------------------

    def action_print_pdf(self):
        """Print the branded profit & loss statement."""
        self.ensure_one()
        return self.env.ref("l10n_et_reports.action_report_profit_loss").report_action(self)

    def action_export_csv(self):
        """Regenerate the CSV export: sections, subtotals, both checks."""
        self.ensure_one()
        data = self._get_report_data()
        rows = [["Section", "Code", "Account", "Amount"]]
        for section in data["sections"]:
            for row in section["accounts"]:
                rows.append(
                    [section["label"], row["code"], row["name"], f"{row['amount']:.2f}"]
                )
            rows.append([section["label"], "", "TOTAL", f"{section['total']:.2f}"])
            if section.get("subtotal"):
                rows.append([])
                rows.append([section["subtotal"], "", "", f"{section['subtotal_amount']:.2f}"])
                rows.append([])
        rows.append([])
        rows.append(["NET PROFIT", "", "", f"{data['net_profit']:.2f}"])
        for warning in data["warnings"]:
            rows.append([])
            rows.append(["WARNING", warning])
        rows.extend(self._csv_tie_out_rows(data["tie_out"]))
        rows.append(self._csv_classification_row(data["classification"]))
        self._store_csv(rows, "profit_loss")
        return True
