# -*- coding: utf-8 -*-
"""Withholding tax summary: per-bill rows with supplier TIN, totals by rate,
grand total tied to the WHT payable GL account.

Reuses the l10n_et_base WHT kind markers on taxes — one row per vendor bill
per WHT rate applied (a mixed goods+services bill can legitimately carry two
rates). Missing supplier TINs are flagged, mirroring the Epic A statutory
identifier warnings: MoR rejects filings without them.
"""

from odoo import api, fields, models


class L10nEtWhtSummary(models.Model):
    _name = "l10n.et.wht.summary"
    _description = "Ethiopian Withholding Tax Summary"
    _inherit = ["l10n.et.report.period.mixin"]
    _order = "date_from desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    total_wht = fields.Monetary(
        string="Total WHT Withheld",
        compute="_compute_totals",
        help="Total withholding tax on vendor bills in the period, to remit to "
        "MoR within 30 days of month end.",
    )

    @api.depends("date_from", "company_id")
    def _compute_name(self):
        """Label, e.g. 'WHT Summary 2026-07'."""
        for report in self:
            period = report.date_from and report.date_from.strftime("%Y-%m") or "?"
            report.name = self.env._("WHT Summary %(period)s", period=period)

    @api.depends("date_from", "date_to", "company_id")
    def _compute_totals(self):
        """Live total from posted moves."""
        for report in self:
            report.total_wht = report._get_report_data()["grand_total"]

    def _get_wht_tax_lines(self):
        """Posted purchase-side WHT tax lines of the period (bills + refunds)."""
        self.ensure_one()
        return self.env["account.move.line"].search(
            self._period_line_domain()
            + [
                ("tax_line_id.l10n_et_wht_kind", "!=", False),
                ("tax_line_id.type_tax_use", "=", "purchase"),
                ("move_id.move_type", "in", ("in_invoice", "in_refund")),
            ],
            order="date, move_name",
        )

    def _get_report_data(self):
        """Full summary dataset for rendering, export and tests."""
        self.ensure_one()
        rounding = self.currency_id.round
        rows = []
        totals_by_rate = {}
        missing_tin = []
        for line in self._get_wht_tax_lines():
            move = line.move_id
            partner = move.commercial_partner_id
            # sudo not needed: partner TIN (l10n_et_base) is not group-restricted.
            tin = partner.l10n_et_tin or ""
            rate = abs(line.tax_line_id.amount)
            # Bills credit WHT payable (negative balance); refunds net out.
            amount = rounding(-line.balance)
            base = rounding(line.tax_base_amount * (-1 if move.move_type == "in_refund" else 1))
            # Foreign digital providers legitimately have no Ethiopian TIN —
            # warning on them would be noise; domestic suppliers must have one.
            if (
                not tin
                and not partner.l10n_et_is_foreign_digital
                and partner.name not in missing_tin
            ):
                missing_tin.append(partner.name)
            rows.append(
                {
                    "move": move,
                    "date": move.invoice_date or move.date,
                    "supplier": partner.name,
                    "tin": tin,
                    "kind": line.tax_line_id.l10n_et_wht_kind,
                    "rate": rate,
                    "base": base,
                    "amount": amount,
                }
            )
            totals_by_rate[rate] = rounding(totals_by_rate.get(rate, 0.0) + amount)
        grand_total = rounding(sum(row["amount"] for row in rows))
        wht_taxes = self.env["account.tax"].search(
            [
                *self.env["account.tax"]._check_company_domain(self.company_id),
                ("l10n_et_wht_kind", "!=", False),
                ("type_tax_use", "=", "purchase"),
            ]
        )
        tie_out = [
            self._tie_out_row(
                self.env._("WHT withheld vs WHT payable GL"),
                grand_total,
                self._tax_accounts(wht_taxes),
                credit_positive=True,
            )
        ]
        warnings = []
        if missing_tin:
            warnings.append(
                self.env._(
                    "Missing supplier TIN (the WHT filing will be rejected by "
                    "MoR): %(names)s",
                    names=", ".join(missing_tin),
                )
            )
        return {
            "rows": rows,
            "totals_by_rate": dict(sorted(totals_by_rate.items())),
            "grand_total": grand_total,
            "tie_out": tie_out,
            "tie_out_ok": all(row["ok"] for row in tie_out),
            "missing_tin": missing_tin,
            "warnings": warnings,
        }

    @staticmethod
    def _tin_cell(row):
        """TIN display: foreign providers need no local TIN; domestic without
        one are flagged MISSING (MoR rejects the filing)."""
        if row["tin"]:
            return row["tin"]
        if row["kind"] == "foreign_digital":
            return "N/A (foreign)"
        return "MISSING"

    def action_print_pdf(self):
        """Print the branded WHT summary PDF."""
        self.ensure_one()
        return self.env.ref("l10n_et_reports.action_report_wht_summary").report_action(self)

    def action_export_csv(self):
        """Regenerate the CSV export: per-bill rows, rate totals, tie-out."""
        self.ensure_one()
        data = self._get_report_data()
        rows = [["Date", "Reference", "Supplier", "TIN", "Kind", "Rate %", "Base", "WHT"]]
        for row in data["rows"]:
            rows.append(
                [
                    row["date"],
                    row["move"].name,
                    row["supplier"],
                    self._tin_cell(row),
                    row["kind"],
                    f"{row['rate']:.0f}",
                    f"{row['base']:.2f}",
                    f"{row['amount']:.2f}",
                ]
            )
        for rate, total in data["totals_by_rate"].items():
            rows.append(["", "", "", "", "TOTAL", f"{rate:.0f}", "", f"{total:.2f}"])
        rows.append(["", "", "", "", "GRAND TOTAL", "", "", f"{data['grand_total']:.2f}"])
        for warning in data["warnings"]:
            rows.append([])
            rows.append(["WARNING", warning])
        rows.extend(self._csv_tie_out_rows(data["tie_out"]))
        self._store_csv(rows, "wht_summary")
        return True
