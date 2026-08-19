# -*- coding: utf-8 -*-
"""Shared machinery for the financial statements (P&L, balance sheet).

Extracted when the balance sheet arrived and wanted the same thing the profit &
loss already did. The alternative was a second copy of the section grouping and
the classification check in shipping code, and two copies of a check drift
apart quietly — one gets a fix and the other keeps the bug, with both green.

What lives here is the SHAPE of a statement:

* accounts selected by Odoo's ``internal_group``, deliberately not by the
  statement's own type lists, so the classification check has two independent
  sides and can actually fail;
* per-account period movement in one grouped read;
* sections built from account TYPES (the grouping itself is set once in the
  chart by ``l10n_et_base``, never by a prefix table inside a report);
* accounts held back pending an accountant's answer, shown in their own section
  and counted as unclassified on every printing;
* the ``N of M accounts classified`` check, which names its shortfall and
  refuses a chart with nothing in it.

What does NOT live here is any opinion about which line an account belongs on,
or what the statement's totals mean. Each statement supplies
``_statement_sections`` and its own reconciliation.
"""

from odoo import models

from odoo.addons.l10n_et_base.models.template_et import ACCOUNTS_AWAITING_CLASSIFICATION


class L10nEtStatementMixin(models.AbstractModel):
    _name = "l10n.et.statement.mixin"
    _description = "Ethiopian Financial Statement (mixin)"
    _inherit = ["l10n.et.report.period.mixin"]

    #: Odoo ``internal_group`` values this statement is responsible for.
    #: Read from Odoo's own classification rather than from
    #: ``_statement_sections``, so an account type no section claims shows up as
    #: unclassified instead of vanishing.
    _statement_internal_groups = ()

    #: Human name of what the classification check is counting, for its message.
    _statement_account_label = "accounts"

    def _statement_sections(self):
        """Which ACCOUNT TYPE prints on which LINE, in statement order.

        Each entry: ``key``, ``label``, ``types``, ``credit_positive``, and
        optionally ``subtotal`` (a running-total line printed after it) and
        ``group`` (a caption the statement groups sections under).
        """
        raise NotImplementedError

    def _statement_accounts(self):
        """Every account in this company's chart that this statement covers."""
        self.ensure_one()
        account_model = self.env["account.account"]
        return account_model.search(
            [
                *account_model._check_company_domain(self.company_id),
                ("internal_group", "in", list(self._statement_internal_groups)),
            ]
        )

    def _statement_line_domain(self):
        """Journal items this statement reads.

        The profit & loss wants the period; the balance sheet wants everything
        up to the closing date. Overriding this one method is the whole
        difference between a flow statement and a position statement.
        """
        return self._period_line_domain()

    def _account_balances(self, accounts):
        """``{account: balance}`` over ``_statement_line_domain``, in one read.

        The reconciliation checks deliberately run their own separate query, so
        the two sides of every tie-out come from different paths.
        """
        self.ensure_one()
        if not accounts:
            return {}
        groups = self.env["account.move.line"]._read_group(
            self._statement_line_domain() + [("account_id", "in", accounts.ids)],
            groupby=["account_id"],
            aggregates=["balance:sum"],
        )
        return {account: balance for account, balance in groups}

    def _section_rows(self, accounts, balances, credit_positive):
        """Account rows of one section: report-positive amounts, movement only.

        Accounts with nothing on them are left off the face of the statement —
        they are still counted by the classification check, which is what keeps
        a dormant unclassified account visible.
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
        totals so the statement still reconciles, and counted as UNCLASSIFIED by
        the check, every printing, until somebody classifies them.
        """
        self.ensure_one()
        by_code = {account.with_company(self.company_id).code: account for account in accounts}
        return [
            (by_code[code], reason)
            for code, reason in sorted(ACCOUNTS_AWAITING_CLASSIFICATION.items())
            if code in by_code
        ]

    def _build_sections(self, accounts, balances, awaiting):
        """Place every account on a line, and report what could not be placed.

        Returns ``(sections, placed, held_back)``. A statement adds its own
        totals on top; this only decides where each account goes.
        """
        self.ensure_one()
        rounding = self.currency_id.round
        held_back = self.env["account.account"].union(*(a for a, _reason in awaiting))
        sections = []
        placed = self.env["account.account"]
        for spec in self._statement_sections():
            members = (
                accounts.filtered(lambda a, types=spec["types"]: a.account_type in types)
                - held_back
            )
            placed |= members
            rows = self._section_rows(members, balances, spec["credit_positive"])
            sections.append(
                dict(spec, accounts=rows, total=rounding(sum(row["amount"] for row in rows)))
            )
        if awaiting:
            rows = []
            for account, reason in awaiting:
                # Sign each held-back account by its own group, so the statement
                # still reconciles while its name stays visible.
                credit_positive = account.internal_group in ("income", "liability", "equity")
                row = self._section_rows(account, balances, credit_positive)
                rows.append(
                    {
                        "code": account.with_company(self.company_id).code,
                        "name": account.name,
                        "amount": row[0]["amount"] if row else 0.0,
                        "credit_positive": credit_positive,
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
        return sections, placed, held_back

    def _classification_check(self, accounts, placed, held_back):
        """`N of M accounts classified` — and the shortfall BY NAME.

        Three ways to fail, and each is a real defect rather than a formatting
        nit:

        * an account held back pending classification;
        * an account whose type no section claims — a chart error, and its
          balance is left out of the totals so the statement's reconciliation
          goes red too;
        * a chart with none of these accounts at all, which would otherwise
          produce a statement of zeros that reconciles perfectly.
        """
        self.ensure_one()
        label = self._statement_account_label
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
                "This company's chart of accounts contains no %(label)s, so this "
                "statement is empty. Load a chart of accounts before relying on it.",
                label=label,
            )
        elif unclassified:
            message = self.env._(
                "%(count)s of %(total)s accounts classified. Unclassified: %(names)s",
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

    def _csv_classification_row(self, classification):
        """The coverage check as a CSV row, in the tie-out block's shape."""
        return [
            "Accounts classified",
            "",
            f"{classification['classified']}",
            f"{classification['total']}",
            "OK" if classification["ok"] else classification["message"],
        ]
