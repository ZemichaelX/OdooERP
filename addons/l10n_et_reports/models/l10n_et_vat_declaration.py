# -*- coding: utf-8 -*-
"""Monthly VAT declaration (Proc 1341/2024): output vs input VAT with GL tie-out.

Rows follow the MoR return structure at section level (output VAT by rate
class, input VAT, net payable/credit); the exact form layout must be verified
against the current MoR form before filing (see README). Amounts come from the
core l10n_et VAT tax codes resolved per company — nothing is duplicated here.
"""

from odoo import api, fields, models

# (template tax xmlid, row label) — declaration structure per side.
OUTPUT_TAX_ROWS = [
    ("id_tax03", "Sales at standard rate (15%)"),
    ("id_tax04", "Zero-rated sales (0%)"),
    ("id_tax06", "Exempt sales"),
]
INPUT_TAX_ROWS = [
    ("id_tax08", "Purchases at standard rate (15%)"),
    ("id_tax07", "Zero-rated purchases (0%)"),
    ("id_tax10", "Exempt purchases"),
]


class L10nEtVatDeclaration(models.Model):
    _name = "l10n.et.vat.declaration"
    _description = "Ethiopian Monthly VAT Declaration"
    _inherit = ["l10n.et.report.period.mixin"]
    _order = "date_from desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    output_vat_total = fields.Monetary(
        compute="_compute_totals",
        help="VAT charged on sales in the period.",
    )
    input_vat_total = fields.Monetary(
        compute="_compute_totals",
        help="VAT paid on purchases in the period (creditable).",
    )
    net_vat = fields.Monetary(
        compute="_compute_totals",
        help="Output minus input VAT: positive = payable to MoR, negative = "
        "credit carried forward.",
    )
    off_chart = fields.Boolean(
        string="Not on Ethiopian Chart",
        compute="_compute_totals",
        help="True when the company is not on the Ethiopian chart of accounts, "
        "so no VAT tax codes resolve. Totals read as zero rather than raising.",
    )

    @api.depends("date_from", "company_id")
    def _compute_name(self):
        """Label, e.g. 'VAT Declaration 2026-07'."""
        for report in self:
            period = report.date_from and report.date_from.strftime("%Y-%m") or "?"
            report.name = self.env._("VAT Declaration %(period)s", period=period)

    @api.depends("date_from", "date_to", "company_id")
    def _compute_totals(self):
        """Live totals from posted moves (see mixin docstring).

        Never raises on read (A4): a company that is not on the Ethiopian chart
        reads as zeros with ``off_chart`` set, so the list/form stay usable and
        surface the reason instead of erroring.
        """
        for report in self:
            data = report._get_report_data()
            report.output_vat_total = data["output_total_tax"]
            report.input_vat_total = data["input_total_tax"]
            report.net_vat = data["net_vat"]
            report.off_chart = data["off_chart"]

    def _tax_rows(self, row_specs):
        """Build (label, base, tax) rows for one side of the declaration.

        Missing tax records (e.g. a company not on the 'et' chart) are skipped;
        callers error out only when NO tax resolves at all.
        """
        rows = []
        for xmlid, label in row_specs:
            tax = self._ref_tax(xmlid)
            if not tax:
                continue
            rows.append(
                {
                    "label": self.env._(label),
                    "tax": tax,
                    "base": self._tax_base_total(tax),
                    "amount": self._tax_amount_total(tax),
                }
            )
        return rows

    def _get_report_data(self):
        """Full declaration dataset for rendering, export and tests.

        Does not raise when the company is off the Ethiopian chart (A4): it
        returns zeroed totals with ``off_chart=True`` so reading the record
        (list view, form, export) is always safe. The print/export actions and
        the form surface the warning instead of erroring.
        """
        self.ensure_one()
        output_rows = self._tax_rows(OUTPUT_TAX_ROWS)
        input_rows = self._tax_rows(INPUT_TAX_ROWS)
        off_chart = not output_rows and not input_rows
        rounding = self.currency_id.round
        output_total_tax = rounding(sum(row["amount"] for row in output_rows))
        input_total_tax = rounding(sum(row["amount"] for row in input_rows))
        net_vat = rounding(output_total_tax - input_total_tax)
        output_taxes = self.env["account.tax"].union(*(row["tax"] for row in output_rows))
        input_taxes = self.env["account.tax"].union(*(row["tax"] for row in input_rows))
        tie_out = [
            self._tie_out_row(
                self.env._("Output VAT vs GL"),
                output_total_tax,
                self._tax_accounts(output_taxes),
                credit_positive=True,
            ),
            self._tie_out_row(
                self.env._("Input VAT vs GL"),
                input_total_tax,
                self._tax_accounts(input_taxes),
                credit_positive=False,
            ),
        ]
        return {
            "output_rows": output_rows,
            "input_rows": input_rows,
            "output_total_base": rounding(sum(row["base"] for row in output_rows)),
            "output_total_tax": output_total_tax,
            "input_total_base": rounding(sum(row["base"] for row in input_rows)),
            "input_total_tax": input_total_tax,
            "net_vat": net_vat,
            "is_payable": net_vat > 0,
            "tie_out": tie_out,
            "tie_out_ok": all(row["ok"] for row in tie_out),
            "off_chart": off_chart,
            "off_chart_warning": (
                self.env._(
                    "%(company)s is not on the Ethiopian chart of accounts — "
                    "no VAT tax codes resolve, so all figures are zero. Load "
                    "the Ethiopian chart before filing.",
                    company=self.company_id.display_name,
                )
                if off_chart
                else ""
            ),
        }

    def action_print_pdf(self):
        """Print the branded VAT declaration PDF."""
        self.ensure_one()
        return self.env.ref("l10n_et_reports.action_report_vat_declaration").report_action(self)

    def action_export_csv(self):
        """Regenerate the CSV export: section rows, totals, net, tie-out."""
        self.ensure_one()
        data = self._get_report_data()
        rows = [["Section", "Row", "Base", "Tax"]]
        for row in data["output_rows"]:
            rows.append(
                ["Output VAT", row["label"], f"{row['base']:.2f}", f"{row['amount']:.2f}"]
            )
        rows.append(
            [
                "Output VAT",
                "TOTAL",
                f"{data['output_total_base']:.2f}",
                f"{data['output_total_tax']:.2f}",
            ]
        )
        for row in data["input_rows"]:
            rows.append(
                ["Input VAT", row["label"], f"{row['base']:.2f}", f"{row['amount']:.2f}"]
            )
        rows.append(
            [
                "Input VAT",
                "TOTAL",
                f"{data['input_total_base']:.2f}",
                f"{data['input_total_tax']:.2f}",
            ]
        )
        rows.append(
            [
                "Net",
                "VAT payable" if data["is_payable"] else "VAT credit carried forward",
                "",
                f"{data['net_vat']:.2f}",
            ]
        )
        rows.extend(self._csv_tie_out_rows(data["tie_out"]))
        self._store_csv(rows, "vat_declaration")
        return True
