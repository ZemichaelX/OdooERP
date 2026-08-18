# -*- coding: utf-8 -*-
"""Profit and loss statement, grouped by ACCOUNT TYPE.

Odoo Community ships no profit & loss statement (defect register entry 27), and
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

from odoo.addons.l10n_et_base.models.template_et import ACCOUNTS_AWAITING_CLASSIFICATION

# Account types Odoo puts in the profit & loss (``internal_group`` income or
# expense). Named here so a type Odoo adds in a future version is caught by the
# classification check rather than silently ignored.
PL_INTERNAL_GROUPS = ("income", "expense")


class L10nEtProfitLoss(models.Model):
    _name = "l10n.et.profit.loss"
    _description = "Ethiopian Profit and Loss Statement"
    _inherit = ["l10n.et.report.period.mixin"]
    _order = "date_from desc, id desc"

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

    def _pl_sections(self):
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

    def _pl_accounts(self):
        """Every profit & loss account in this company's chart.

        Selected by Odoo's own ``internal_group``, DELIBERATELY not by the type
        lists in ``_pl_sections``. If the two disagree the classification check
        reports the difference; were both sides read from the same table the
        check could not fail.
        """
        self.ensure_one()
        account_model = self.env["account.account"]
        return account_model.search(
            [
                *account_model._check_company_domain(self.company_id),
                ("internal_group", "in", PL_INTERNAL_GROUPS),
            ]
        )

    def _account_period_movement(self, accounts):
        """Period movement per account, as ``{account: balance}`` (signed).

        One grouped read for the whole statement; the tie-out deliberately runs
        its own separate query so the two figures come from different paths.
        """
        self.ensure_one()
        if not accounts:
            return {}
        groups = self.env["account.move.line"]._read_group(
            self._period_line_domain() + [("account_id", "in", accounts.ids)],
            groupby=["account_id"],
            aggregates=["balance:sum"],
        )
        return {account: balance for account, balance in groups}

    def _section_rows(self, accounts, balances, credit_positive):
        """Account rows of one section: report-positive amounts, movement only.

        Accounts with no movement in the period are left off the face of the
        statement — they are still counted by the classification check, which is
        what keeps an unclassified dormant account visible.
        """
        rounding = self.currency_id.round
        sign = -1 if credit_positive else 1
        rows = []
        for account in accounts:
            balance = balances.get(account, 0.0)
            amount = rounding(sign * balance)
            if not self.currency_id.is_zero(amount):
                rows.append(
                    {
                        "code": account.with_company(self.company_id).code,
                        "name": account.name,
                        "amount": amount,
                    }
                )
        rows.sort(key=lambda row: row["code"] or "")
        return rows

    def _awaiting_classification_accounts(self, accounts):
        """Chart accounts held back from a section pending an accountant's answer.

        Keyed by code from ``l10n_et_base`` — company-dependent, hence
        ``with_company``. These are shown in their own section, included in the
        totals so the ledger still ties, and counted as UNCLASSIFIED by the
        check, every printing, until somebody classifies them.
        """
        self.ensure_one()
        by_code = {account.with_company(self.company_id).code: account for account in accounts}
        return [
            (by_code[code], reason)
            for code, reason in sorted(ACCOUNTS_AWAITING_CLASSIFICATION.items())
            if code in by_code
        ]

    def _get_report_data(self):
        """Full statement dataset for rendering, export and tests."""
        self.ensure_one()
        rounding = self.currency_id.round
        accounts = self._pl_accounts()
        balances = self._account_period_movement(accounts)
        awaiting = self._awaiting_classification_accounts(accounts)
        held_back = self.env["account.account"].union(*(a for a, _reason in awaiting))

        sections = []
        placed = self.env["account.account"]
        net_profit = 0.0
        gross_profit = 0.0
        for spec in self._pl_sections():
            members = (
                accounts.filtered(lambda a, types=spec["types"]: a.account_type in types)
                - held_back
            )
            placed |= members
            rows = self._section_rows(members, balances, spec["credit_positive"])
            total = rounding(sum(row["amount"] for row in rows))
            net_profit += total if spec["credit_positive"] else -total
            section = dict(spec, accounts=rows, total=total)
            if spec.get("subtotal"):
                gross_profit = rounding(net_profit)
                section["subtotal_amount"] = gross_profit
            sections.append(section)

        if awaiting:
            # Expenses debit, income credits: sign each held-back account by its
            # own group so the ledger still ties while the name stays visible.
            rows = []
            for account, reason in awaiting:
                credit_positive = account.internal_group == "income"
                row = self._section_rows(account, balances, credit_positive)
                amount = row[0]["amount"] if row else 0.0
                net_profit += amount if credit_positive else -amount
                rows.append(
                    {
                        "code": account.with_company(self.company_id).code,
                        "name": account.name,
                        "amount": amount,
                        "reason": reason,
                    }
                )
            sections.append(
                {
                    "key": "awaiting_classification",
                    "label": self.env._("Awaiting Classification"),
                    "credit_positive": False,
                    "accounts": rows,
                    "total": rounding(sum(row["amount"] for row in rows)),
                }
            )
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

    def _classification_check(self, accounts, placed, held_back):
        """`61 of 62 accounts classified` — and the shortfall BY NAME.

        Three ways to fail, and each is a real defect rather than a formatting
        nit:

        * an account held back pending classification (`592100` today);
        * an account whose type no section claims — a chart error, and its
          movement is left out of the totals so the ledger check goes red too;
        * a chart with no income or expense accounts at all, which would
          otherwise produce a statement of zeros that reconciles perfectly.
        """
        self.ensure_one()
        unplaced = accounts - placed - held_back
        unclassified = [
            {
                "code": account.with_company(self.company_id).code,
                "name": account.name,
                "reason": self.env._(
                    "type %(account_type)s is on no line of this statement",
                    account_type=account.account_type,
                ),
            }
            for account in unplaced
        ] + [
            {
                "code": account.with_company(self.company_id).code,
                "name": account.name,
                "reason": reason,
            }
            for account, reason in self._awaiting_classification_accounts(accounts)
        ]
        unclassified.sort(key=lambda row: row["code"] or "")
        total = len(accounts)
        classified = total - len(unclassified)
        if not total:
            message = self.env._(
                "This company's chart of accounts contains no income or expense "
                "accounts, so this statement is empty. Load a chart of accounts "
                "before relying on it."
            )
        elif unclassified:
            message = self.env._(
                "%(count)s of %(total)s accounts classified. Unclassified: " "%(names)s",
                count=classified,
                total=total,
                names="; ".join(
                    "%s %s (%s)" % (row["code"], row["name"], row["reason"])
                    for row in unclassified
                ),
            )
        else:
            message = self.env._(
                "%(total)s of %(total)s accounts classified, unclassified: none",
                total=total,
            )
        return {
            "classified": classified,
            "total": total,
            "unclassified": unclassified,
            "ok": bool(total) and not unclassified,
            "message": message,
            "summary": self.env._(
                "%(count)s of %(total)s accounts classified",
                count=classified,
                total=total,
            ),
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
        classification = data["classification"]
        rows.append(
            [
                "Accounts classified",
                "",
                f"{classification['classified']}",
                f"{classification['total']}",
                "OK" if classification["ok"] else classification["message"],
            ]
        )
        self._store_csv(rows, "profit_loss")
        return True
