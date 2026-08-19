# -*- coding: utf-8 -*-
"""Balance sheet: assets, liabilities and equity as at a closing date.

The other half of the reporting blocker (entry 27 of the internal defect
register). Odoo Community ships no balance
sheet and no OCA repository supplies one, so an Ethiopian PLC had nothing to
hand its bank or to attach to its annual business-profit return.

**A balance sheet is a POSITION, not a flow.** The profit & loss reads movement
inside its period; this reads every posted line up to and including
``date_to`` — that is the whole difference, and it is one overridden method
(``_statement_line_domain``). ``date_from`` still matters: it splits the
accumulated result into *brought forward* and *result for the period*, which is
what lets the two statements be tied to each other.

**Three checks print on the face of it**, and none can pass by the work not
happening (CLAUDE.md rule 2):

1. *Total assets vs total liabilities and equity.* The two sides are computed
   from different accounts by different queries — the left from the asset
   sections, the right from the liability and equity sections plus the result
   summed off the income and expense accounts. An account that falls out of
   either side moves one and not the other.
2. *Result for the period vs the profit & loss statement.* This statement sums
   it straight off the income and expense accounts; the P&L builds the same
   figure up from its section totals. Two paths, one number — and this is the
   check that makes the two statements one set of books rather than two
   opinions.
3. *Accounts classified.* `50 of 50 accounts classified`, naming any shortfall,
   with anything it cannot place left OUT of the totals so check 1 goes red as
   well.
"""

from datetime import timedelta

from odoo import api, fields, models

# The day before the period opens: everything on or before it is brought
# forward, everything after it is the result of the period.
ONE_DAY = timedelta(days=1)


class L10nEtBalanceSheet(models.Model):
    _name = "l10n.et.balance.sheet"
    _description = "Ethiopian Balance Sheet"
    _inherit = ["l10n.et.statement.mixin"]
    _order = "date_to desc, id desc"

    # Odoo's own classification of what sits on a balance sheet. `off_balance`
    # is excluded BY DEFINITION, not by oversight, and is counted separately so
    # it never becomes invisible.
    _statement_internal_groups = ("asset", "liability", "equity")
    _statement_account_label = "asset, liability or equity accounts"

    name = fields.Char(compute="_compute_name", store=True)
    total_assets = fields.Monetary(
        compute="_compute_totals",
        help="Everything the company owns, as at the closing date.",
    )
    total_liabilities_and_equity = fields.Monetary(
        compute="_compute_totals",
        help="Everything the company owes plus what the owners have in it, "
        "including the result of the period. Must equal total assets.",
    )
    result_for_period = fields.Monetary(
        compute="_compute_totals",
        help="Profit or loss between the two dates — the same figure the profit "
        "& loss statement reports, and checked against it on the face of this "
        "statement.",
    )
    tie_out_ok = fields.Boolean(
        string="Balances",
        compute="_compute_totals",
        help="False when the statement does not balance, when it disagrees with "
        "the profit & loss statement, or when an account in the chart could not "
        "be placed on it.",
    )

    @api.depends("date_to", "company_id")
    def _compute_name(self):
        """Label, e.g. 'Balance Sheet as at 2026-12-31'."""
        for report in self:
            as_at = report.date_to and report.date_to.strftime("%Y-%m-%d") or "?"
            report.name = self.env._("Balance Sheet as at %(as_at)s", as_at=as_at)

    @api.depends("date_from", "date_to", "company_id")
    def _compute_totals(self):
        """Live figures from posted moves — a window on the GL, not a snapshot."""
        for report in self:
            data = report._get_report_data()
            report.total_assets = data["total_assets"]
            report.total_liabilities_and_equity = data["total_liabilities_and_equity"]
            report.result_for_period = data["result_for_period"]
            report.tie_out_ok = data["tie_out_ok"]

    # ---- position, not flow ---------------------------------------------

    def _statement_line_domain(self):
        """Every posted line UP TO the closing date, with no lower bound.

        Balance-sheet accounts carry forward: a receivable raised two years ago
        and still unpaid belongs on today's statement. Bounding the start — the
        way the period reports do — would silently drop every opening balance
        and still reconcile, because both sides of the identity would lose the
        same lines.
        """
        self.ensure_one()
        return [
            ("move_id.state", "=", "posted"),
            ("date", "<=", self.date_to),
            ("company_id", "=", self.company_id.id),
        ]

    def _statement_sections(self):
        """Which ACCOUNT TYPE prints on which LINE, under which caption.

        As with the profit & loss, this table says only which TYPE goes where.
        Which account carries which type is set once in the chart, so every
        report that reads types inherits the same answer.
        """
        assets = self.env._("Assets")
        liabilities = self.env._("Liabilities")
        equity = self.env._("Equity")
        return [
            {
                "key": "cash",
                "group": assets,
                "label": self.env._("Bank and Cash"),
                "types": ("asset_cash",),
                "credit_positive": False,
            },
            {
                "key": "receivables",
                "group": assets,
                "label": self.env._("Receivables"),
                "types": ("asset_receivable",),
                "credit_positive": False,
            },
            {
                "key": "prepayments",
                "group": assets,
                "label": self.env._("Prepayments"),
                "types": ("asset_prepayments",),
                "credit_positive": False,
            },
            {
                "key": "current_assets",
                "group": assets,
                "label": self.env._("Current Assets"),
                "types": ("asset_current",),
                "credit_positive": False,
            },
            {
                "key": "non_current_assets",
                "group": assets,
                "label": self.env._("Non-current Assets"),
                "types": ("asset_non_current",),
                "credit_positive": False,
            },
            {
                "key": "fixed_assets",
                "group": assets,
                "label": self.env._("Fixed Assets"),
                "types": ("asset_fixed",),
                "credit_positive": False,
            },
            {
                "key": "payables",
                "group": liabilities,
                "label": self.env._("Payables"),
                "types": ("liability_payable",),
                "credit_positive": True,
            },
            {
                "key": "credit_cards",
                "group": liabilities,
                "label": self.env._("Credit Cards"),
                "types": ("liability_credit_card",),
                "credit_positive": True,
            },
            {
                "key": "current_liabilities",
                "group": liabilities,
                "label": self.env._("Current Liabilities"),
                "types": ("liability_current",),
                "credit_positive": True,
            },
            {
                "key": "non_current_liabilities",
                "group": liabilities,
                "label": self.env._("Non-current Liabilities"),
                "types": ("liability_non_current",),
                "credit_positive": True,
            },
            {
                "key": "equity",
                "group": equity,
                "label": self.env._("Capital and Reserves"),
                "types": ("equity",),
                "credit_positive": True,
            },
            {
                "key": "equity_unaffected",
                "group": equity,
                "label": self.env._("Undistributed Earnings"),
                "types": ("equity_unaffected",),
                "credit_positive": True,
            },
        ]

    # ---- the accumulated result -----------------------------------------

    def _profit_and_loss_accounts(self):
        """Income and expense accounts — where the result of the year lives."""
        self.ensure_one()
        account_model = self.env["account.account"]
        return account_model.search(
            [
                *account_model._check_company_domain(self.company_id),
                ("internal_group", "in", ("income", "expense")),
            ]
        )

    def _result_between(self, accounts, date_from, date_to):
        """Credit-positive result of ``accounts`` between two dates, inclusive.

        Summed straight off the ledger. The profit & loss builds the same figure
        by adding up its section totals, which is what makes the cross-statement
        check worth having.
        """
        self.ensure_one()
        if not accounts:
            return 0.0
        domain = [
            ("move_id.state", "=", "posted"),
            ("date", "<=", date_to),
            ("company_id", "=", self.company_id.id),
            ("account_id", "in", accounts.ids),
        ]
        if date_from:
            domain.append(("date", ">=", date_from))
        lines = self.env["account.move.line"].search(domain)
        return self.currency_id.round(-sum(lines.mapped("balance")))

    def _profit_and_loss_net_profit(self):
        """What the profit & loss statement says for the same company and period.

        Built through the P&L model itself, on an unsaved record, so this reads
        the statement a client would print rather than a re-derivation of it.
        """
        self.ensure_one()
        statement = self.env["l10n.et.profit.loss"].new(
            {
                "company_id": self.company_id.id,
                "date_from": self.date_from,
                "date_to": self.date_to,
            }
        )
        return statement._get_report_data()["net_profit"]

    # ---- the statement ---------------------------------------------------

    def _get_report_data(self):
        """Full statement dataset for rendering, export and tests."""
        self.ensure_one()
        rounding = self.currency_id.round
        accounts = self._statement_accounts()
        balances = self._account_balances(accounts)
        awaiting = self._awaiting_classification_accounts(accounts)
        sections, placed, held_back = self._build_sections(accounts, balances, awaiting)

        # Totals accumulate from the SECTION TOTALS, never from a raw sum over
        # the accounts: if both sides of the identity below came from one figure
        # it could not disagree.
        total_assets = 0.0
        total_liabilities = 0.0
        total_equity_accounts = 0.0
        for section in sections:
            if section["key"] == "awaiting_classification":
                for row in section["accounts"]:
                    if row["credit_positive"]:
                        total_equity_accounts += row["amount"]
                    else:
                        total_assets += row["amount"]
                continue
            if section["credit_positive"]:
                if section["key"] in ("equity", "equity_unaffected"):
                    total_equity_accounts += section["total"]
                else:
                    total_liabilities += section["total"]
            else:
                total_assets += section["total"]

        pl_accounts = self._profit_and_loss_accounts()
        brought_forward = self._result_between(pl_accounts, None, self.date_from - ONE_DAY)
        result_for_period = self._result_between(pl_accounts, self.date_from, self.date_to)
        total_equity = rounding(total_equity_accounts + brought_forward + result_for_period)
        total_assets = rounding(total_assets)
        total_liabilities = rounding(total_liabilities)
        total_liabilities_and_equity = rounding(total_liabilities + total_equity)

        difference = rounding(total_liabilities_and_equity - total_assets)
        pl_net_profit = self._profit_and_loss_net_profit()
        pl_difference = rounding(pl_net_profit - result_for_period)
        tie_out = [
            {
                "label": self.env._("Total assets vs total liabilities and equity"),
                "accounts": "",
                "report_total": total_assets,
                "gl_total": total_liabilities_and_equity,
                "difference": difference,
                "ok": self.currency_id.is_zero(difference),
            },
            {
                "label": self.env._("Result for the period vs the profit and loss statement"),
                "accounts": "",
                "report_total": result_for_period,
                "gl_total": pl_net_profit,
                "difference": pl_difference,
                "ok": self.currency_id.is_zero(pl_difference),
            },
        ]

        classification = self._classification_check(accounts, placed, held_back)
        warnings = []
        if not classification["ok"]:
            warnings.append(classification["message"])
        off_balance = self.env["account.account"].search_count(
            [
                *self.env["account.account"]._check_company_domain(self.company_id),
                ("internal_group", "=", "off_balance"),
            ]
        )
        if off_balance:
            warnings.append(
                self.env._(
                    "%(count)s off-balance-sheet account(s) exist in this chart and "
                    "are excluded from this statement by definition.",
                    count=off_balance,
                )
            )
        return {
            "sections": sections,
            "equity_lines": [
                {
                    "label": self.env._("Retained earnings brought forward"),
                    "amount": brought_forward,
                },
                {
                    "label": self.env._("Result for the period"),
                    "amount": result_for_period,
                },
            ],
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "total_liabilities_and_equity": total_liabilities_and_equity,
            "result_for_period": result_for_period,
            "brought_forward": brought_forward,
            "classification": classification,
            "off_balance_accounts": off_balance,
            "tie_out": tie_out,
            "tie_out_ok": all(row["ok"] for row in tie_out) and classification["ok"],
            "warnings": warnings,
        }

    # ---- outputs ---------------------------------------------------------

    def action_print_pdf(self):
        """Print the branded balance sheet."""
        self.ensure_one()
        return self.env.ref("l10n_et_reports.action_report_balance_sheet").report_action(self)

    def action_export_csv(self):
        """Regenerate the CSV export: sections, totals, all three checks."""
        self.ensure_one()
        data = self._get_report_data()
        rows = [["Group", "Section", "Code", "Account", "Amount"]]
        for section in data["sections"]:
            group = section.get("group", "")
            for row in section["accounts"]:
                rows.append(
                    [group, section["label"], row["code"], row["name"], f"{row['amount']:.2f}"]
                )
            rows.append([group, section["label"], "", "TOTAL", f"{section['total']:.2f}"])
        rows.append([])
        for line in data["equity_lines"]:
            rows.append(["Equity", line["label"], "", "", f"{line['amount']:.2f}"])
        rows.append([])
        rows.append(["TOTAL ASSETS", "", "", "", f"{data['total_assets']:.2f}"])
        rows.append(["TOTAL LIABILITIES", "", "", "", f"{data['total_liabilities']:.2f}"])
        rows.append(["TOTAL EQUITY", "", "", "", f"{data['total_equity']:.2f}"])
        rows.append(
            [
                "TOTAL LIABILITIES AND EQUITY",
                "",
                "",
                "",
                f"{data['total_liabilities_and_equity']:.2f}",
            ]
        )
        for warning in data["warnings"]:
            rows.append([])
            rows.append(["WARNING", warning])
        rows.extend(self._csv_tie_out_rows(data["tie_out"]))
        rows.append(self._csv_classification_row(data["classification"]))
        self._store_csv(rows, "balance_sheet")
        return True
