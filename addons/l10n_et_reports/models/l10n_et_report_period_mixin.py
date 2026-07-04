# -*- coding: utf-8 -*-
"""Shared plumbing for the Ethiopian statutory period reports.

Everything reads LIVE from posted journal items — a report record is a period
window over the GL, not a snapshot, so reprinting after corrections always
shows current numbers. The tie-out helpers compare each report total against
the full GL movement of the accounts configured on the underlying taxes'
repartition lines: a manual journal entry that bypasses the tax engine makes
the tie-out fail visibly instead of silently under-declaring.
"""

import base64
import csv
import io
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class L10nEtReportPeriodMixin(models.AbstractModel):
    _name = "l10n.et.report.period.mixin"
    _description = "Ethiopian Statutory Report Period (mixin)"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        help="Statutory reports never cross companies.",
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    date_from = fields.Date(
        required=True,
        default=lambda self: date.today().replace(day=1) - relativedelta(months=1),
        help="First day of the declaration period (inclusive). Defaults to the "
        "previous month — the one being declared.",
    )
    date_to = fields.Date(
        required=True,
        default=lambda self: date.today().replace(day=1) - relativedelta(days=1),
        help="Last day of the declaration period (inclusive).",
    )
    csv_export_file = fields.Binary(
        string="CSV Export",
        readonly=True,
        copy=False,
        help="Machine-readable export of the report (regenerated on demand).",
    )
    csv_export_filename = fields.Char(readonly=True, copy=False)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        """A period must be a forward range."""
        for report in self:
            if report.date_from and report.date_to and report.date_from > report.date_to:
                raise UserError(self.env._("The period start must be before its end."))

    def _ref_tax(self, xmlid):
        """Resolve a chart-template tax for this report's company (may be empty
        on companies that are not on the Ethiopian chart)."""
        self.ensure_one()
        return (
            self.env["account.chart.template"]
            .with_company(self.company_id)
            .ref(xmlid, raise_if_not_found=False)
        )

    def _period_line_domain(self):
        """Domain for posted journal items of this company inside the period."""
        self.ensure_one()
        return [
            ("move_id.state", "=", "posted"),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("company_id", "=", self.company_id.id),
        ]

    @staticmethod
    def _tax_sign(tax):
        """Report-positive sign: sale-side amounts are credits (negative balance),
        purchase-side are debits."""
        return -1 if tax.type_tax_use == "sale" else 1

    def _tax_base_total(self, tax):
        """Period base total for ``tax``: signed sum of the base lines that carry
        it (refunds net out automatically)."""
        lines = self.env["account.move.line"].search(
            self._period_line_domain() + [("tax_ids", "in", tax.id)]
        )
        return self.currency_id.round(self._tax_sign(tax) * sum(lines.mapped("balance")))

    def _tax_amount_total(self, tax):
        """Period tax total for ``tax``: signed sum of its tax lines."""
        lines = self.env["account.move.line"].search(
            self._period_line_domain() + [("tax_line_id", "=", tax.id)]
        )
        return self.currency_id.round(self._tax_sign(tax) * sum(lines.mapped("balance")))

    @staticmethod
    def _tax_accounts(taxes):
        """The GL accounts these taxes post to (their 'tax' repartition lines)."""
        return taxes.repartition_line_ids.filtered(
            lambda line: line.repartition_type == "tax"
        ).account_id

    def _account_movement(self, accounts, credit_positive):
        """FULL period movement of ``accounts`` (every journal item, not only
        tax-engine ones) — the GL side of the tie-out."""
        if not accounts:
            return 0.0
        lines = self.env["account.move.line"].search(
            self._period_line_domain() + [("account_id", "in", accounts.ids)]
        )
        sign = -1 if credit_positive else 1
        return self.currency_id.round(sign * sum(lines.mapped("balance")))

    def _store_csv(self, rows, filename_prefix):
        """Serialize ``rows`` (lists of cells) to the record's CSV export field."""
        self.ensure_one()
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerows(rows)
        self.csv_export_file = base64.b64encode(buffer.getvalue().encode("utf-8"))
        self.csv_export_filename = f"{filename_prefix}_{self.date_from:%Y_%m}.csv"

    @staticmethod
    def _csv_tie_out_rows(tie_out):
        """Tie-out block shared by both CSV exports — mismatches always visible."""
        rows = [[], ["Tie-out", "Accounts", "Report total", "GL total", "Status"]]
        for tie in tie_out:
            rows.append(
                [
                    tie["label"],
                    tie["accounts"],
                    f"{tie['report_total']:.2f}",
                    f"{tie['gl_total']:.2f}",
                    "OK" if tie["ok"] else f"MISMATCH ({tie['difference']:.2f})",
                ]
            )
        return rows

    def _tie_out_row(self, label, report_total, accounts, credit_positive):
        """One reconciliation row: report total vs GL movement, with an ok flag.

        ``ok`` is False on any difference — the reports render that as a
        warning; a mismatch must never pass silently.
        """
        gl_total = self._account_movement(accounts, credit_positive)
        # Account codes are company-dependent: read them as the report company,
        # not the environment's active company.
        codes = accounts.with_company(self.company_id).mapped("code")
        return {
            "label": label,
            "accounts": ", ".join(code for code in codes if code),
            "report_total": report_total,
            "gl_total": gl_total,
            "difference": self.currency_id.round(gl_total - report_total),
            "ok": self.currency_id.is_zero(gl_total - report_total),
        }
