# -*- coding: utf-8 -*-
"""The exam: prove the books of a provisioned rehearsal tenant.

Every check RECOMPUTES the expected figure from source documents by a path
independent of the thing it checks — sale/purchase orders for stock, invoice
untaxed bases for VAT, the reference calculators for WHT and payroll — then
compares expected vs actual and vs the GL. Any mismatch is a finding.

Returns a structured reconciliation so the same logic backs the pytest/HttpCase
suite AND the human-readable table the pre-release script prints.
"""

from odoo import api, models

from odoo.addons.l10n_et_base.reference import et_tax_calc
from odoo.addons.l10n_et_payroll.reference import et_payroll_calc

from .sapian_dress_rehearsal import PERIOD_FROM, PERIOD_TO

VAT_RATE = 0.15


class SapianDressRehearsalExam(models.AbstractModel):
    _name = "sapian.dress.rehearsal.exam"
    _description = "SapianERP Dress-Rehearsal Exam (independent tie-out)"

    @api.model
    def run(self, company):
        """Run every check against ``company`` and return the reconciliation."""
        exam = self.with_company(company)
        checks = []
        checks += exam._check_trial_balance(company)
        checks += exam._check_vat(company)
        checks += exam._check_wht(company)
        checks += exam._check_payroll(company)
        checks += exam._check_stock(company)
        return {
            "company": company.display_name,
            "checks": checks,
            "all_ok": all(c["ok"] for c in checks),
        }

    # ------------------------------------------------------------- helpers
    def _round(self, company, value):
        return company.currency_id.round(value)

    def _posted_lines_domain(self, company):
        return [
            ("move_id.state", "=", "posted"),
            ("company_id", "=", company.id),
            ("date", ">=", PERIOD_FROM),
            ("date", "<=", PERIOD_TO),
        ]

    @staticmethod
    def _check(name, expected, actual, detail=""):
        """One reconciliation row; ok on exact (rounded) agreement."""
        ok = abs(round(expected - actual, 2)) < 0.005
        return {
            "name": name,
            "expected": round(expected, 2),
            "actual": round(actual, 2),
            "ok": ok,
            "detail": detail,
        }

    # ----------------------------------------------------- 1. trial balance
    def _check_trial_balance(self, company):
        """Every posted move balances, and company-wide debits == credits."""
        moves = self.env["account.move"].search(
            [
                ("state", "=", "posted"),
                ("company_id", "=", company.id),
                ("date", ">=", PERIOD_FROM),
                ("date", "<=", PERIOD_TO),
            ]
        )
        unbalanced = sum(
            1
            for m in moves
            if not company.currency_id.is_zero(sum(m.line_ids.mapped("balance")))
        )
        lines = self.env["account.move.line"].search(self._posted_lines_domain(company))
        total_debit = self._round(company, sum(lines.mapped("debit")))
        total_credit = self._round(company, sum(lines.mapped("credit")))
        return [
            self._check(
                "Trial balance — unbalanced moves",
                0,
                unbalanced,
                f"{len(moves)} posted moves in period",
            ),
            self._check(
                "Trial balance — total debits vs credits",
                total_debit,
                total_credit,
                f"{total_debit:,.2f}",
            ),
        ]

    # -------------------------------------------------------------- 2. VAT
    def _check_vat(self, company):
        """Independent base × 15% vs the declaration vs the GL."""
        declaration = self.env["l10n.et.vat.declaration"].search(
            [("company_id", "=", company.id)], limit=1
        )
        data = declaration._get_report_data()
        # Independent bases from move untaxed totals (signed by move type).
        sale_moves = self.env["account.move"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "posted"),
                ("move_type", "in", ("out_invoice", "out_refund")),
                ("invoice_date", ">=", PERIOD_FROM),
                ("invoice_date", "<=", PERIOD_TO),
            ]
        )
        purchase_moves = self.env["account.move"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "posted"),
                ("move_type", "in", ("in_invoice", "in_refund")),
                ("invoice_date", ">=", PERIOD_FROM),
                ("invoice_date", "<=", PERIOD_TO),
            ]
        )
        # Unsigned untaxed base, netted by document direction (refund subtracts).
        output_base = sum(
            (1 if m.move_type == "out_invoice" else -1) * m.amount_untaxed for m in sale_moves
        )
        input_base = sum(
            (1 if m.move_type == "in_invoice" else -1) * m.amount_untaxed
            for m in purchase_moves
        )
        expected_output = self._round(company, VAT_RATE * output_base)
        expected_input = self._round(company, VAT_RATE * input_base)
        return [
            self._check(
                "VAT — output (15% × sales base) vs declaration",
                expected_output,
                declaration.output_vat_total,
                f"base {output_base:,.2f}",
            ),
            self._check(
                "VAT — input (15% × purchase base) vs declaration",
                expected_input,
                declaration.input_vat_total,
                f"base {input_base:,.2f}",
            ),
            self._check(
                "VAT — declaration ties to GL (output+input)",
                2,
                sum(1 for row in data["tie_out"] if row["ok"]),
                "both tie-out rows OK",
            ),
        ]

    # -------------------------------------------------------------- 3. WHT
    def _check_wht(self, company):
        """Recompute WHT per bill from the calculator; totals by rate; GL tie."""
        summary = self.env["l10n.et.wht.summary"].search(
            [("company_id", "=", company.id)], limit=1
        )
        data = summary._get_report_data()
        config = self.env["l10n.et.wht.config"]._get_config(company, PERIOD_TO)
        bills = self.env["account.move"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "posted"),
                ("move_type", "=", "in_invoice"),
                ("invoice_date", ">=", PERIOD_FROM),
                ("invoice_date", "<=", PERIOD_TO),
            ]
        )
        expected_total = 0.0
        for bill in bills:
            partner = bill.commercial_partner_id
            has_tin = et_tax_calc.validate_tin(partner.l10n_et_tin).valid
            has_licence = partner.l10n_et_has_valid_licence
            product_lines = bill.invoice_line_ids.filtered(
                lambda line: line.display_type == "product"
            )
            if partner.l10n_et_is_foreign_digital:
                groups = {et_tax_calc.KIND_FOREIGN_DIGITAL: product_lines}
            else:
                groups = {}
                for line in product_lines:
                    kind = (
                        et_tax_calc.KIND_SERVICE
                        if line.product_id.type == "service"
                        else et_tax_calc.KIND_GOODS
                    )
                    groups.setdefault(kind, self.env["account.move.line"])
                    groups[kind] |= line
            for kind, lines in groups.items():
                base = abs(sum(lines.mapped("balance")))
                result = et_tax_calc.compute_wht(
                    base,
                    kind=kind,
                    has_tin=has_tin,
                    has_licence=has_licence,
                    punitive_respects_thresholds=config.punitive_respects_thresholds,
                    rate_standard=config.rate_standard,
                    rate_punitive=config.rate_punitive,
                    rate_foreign_digital=config.rate_foreign_digital,
                    threshold_goods=config.threshold_goods,
                    threshold_service=config.threshold_service,
                )
                expected_total += result.amount
        expected_total = self._round(company, expected_total)
        return [
            self._check(
                "WHT — recomputed per bill vs summary total",
                expected_total,
                summary.total_wht,
                "by-rate: "
                + ", ".join(f"{r:.0f}%→{t:,.0f}" for r, t in data["totals_by_rate"].items()),
            ),
            self._check(
                "WHT — summary ties to WHT-payable GL",
                1,
                sum(1 for row in data["tie_out"] if row["ok"]),
                "tie-out row OK",
            ),
        ]

    # ---------------------------------------------------------- 4. payroll
    def _check_payroll(self, company):
        """Recompute each payslip from the reference calculator with CONFIG-
        sourced bands/rates; assert config records exist (not hardcoded)."""
        run = self.env["l10n.et.payroll.run"].search([("company_id", "=", company.id)], limit=1)
        bands = self.env["l10n.et.paye.band"].get_active_bands(on_date=PERIOD_TO)
        pension_cfg = self.env["l10n.et.pension.config"].search(
            [("company_id", "=", company.id)], limit=1
        )
        checks = []
        expected_paye_total = 0.0
        expected_pension_ee_total = 0.0
        expected_net_total = 0.0
        for slip in run.payslip_ids:
            earnings = slip.input_line_ids.filtered(lambda line: line.category == "earning")
            taxable_extra = 0.0
            exempt_extra = 0.0
            for line in earnings:
                if line.allowance_type_id:
                    exempt, taxable = line.allowance_type_id.split(
                        line.amount, slip.basic_salary
                    )
                elif line.taxable:
                    exempt, taxable = 0.0, line.amount
                else:
                    exempt, taxable = line.amount, 0.0
                taxable_extra += taxable
                exempt_extra += exempt
            result = et_payroll_calc.compute_payroll(
                et_payroll_calc.PayrollInput(
                    basic_salary=slip.basic_salary,
                    taxable_allowances=taxable_extra,
                    non_taxable_allowances=exempt_extra,
                    is_citizen=slip.is_citizen,
                ),
                bands=bands,
                pension_employee_rate=pension_cfg.employee_rate,
                pension_employer_rate=pension_cfg.employer_rate,
                pension_cap=(pension_cfg.insurable_cap or None),
            )
            expected_paye_total += result.paye
            expected_pension_ee_total += result.pension_employee
            expected_net_total += result.net_pay
            checks.append(
                self._check(
                    f"Payroll — {slip.employee_id.name.split(' — ')[0]} net",
                    result.net_pay,
                    slip.net_pay,
                    f"PAYE {result.paye:,.2f} / pension {result.pension_employee:,.2f}",
                )
            )
        checks.append(
            self._check(
                "Payroll — total PAYE vs run",
                self._round(company, expected_paye_total),
                run.total_paye,
            )
        )
        checks.append(
            self._check(
                "Payroll — total employee pension vs run",
                self._round(company, expected_pension_ee_total),
                run.total_pension_employee,
            )
        )
        checks.append(
            self._check(
                "Payroll — computed from CONFIG records (bands+pension+allowance)",
                1,
                1 if (bands and pension_cfg and self._allowance_types_seeded(company)) else 0,
                f"{len(bands)} PAYE bands, pension {pension_cfg.employee_rate:.0%}",
            )
        )
        return checks

    def _allowance_types_seeded(self, company):
        return bool(
            self.env["l10n.et.allowance.type"].search_count(
                [("company_id", "=", company.id), ("code", "=", "transport")]
            )
        )

    # ------------------------------------------------------------ 5. stock
    def _check_stock(self, company):
        """On-hand per product = received (PO) − delivered (SO) ± inventory
        adjustment, all from source documents, vs the stock quant."""
        products = self.env["product.product"].search(
            [
                ("company_id", "in", (False, company.id)),
                ("is_storable", "=", True),
                ("type", "=", "consu"),
            ]
        )
        checks = []
        for product in products:
            received = sum(
                self.env["purchase.order.line"]
                .search(
                    [
                        ("company_id", "=", company.id),
                        ("product_id", "=", product.id),
                    ]
                )
                .mapped("qty_received")
            )
            delivered = sum(
                self.env["sale.order.line"]
                .search(
                    [
                        ("company_id", "=", company.id),
                        ("product_id", "=", product.id),
                    ]
                )
                .mapped("qty_delivered")
            )
            adjustment = self._inventory_delta(company, product)
            expected = received - delivered + adjustment
            actual = self._on_hand(company, product)
            checks.append(
                self._check(
                    f"Stock — {product.name.split(' — ')[0]} on-hand",
                    expected,
                    actual,
                    f"recv {received:g} − deliv {delivered:g} + adj {adjustment:g}",
                )
            )
        return checks

    def _inventory_delta(self, company, product):
        """Signed quantity of the period's inventory-adjustment moves for the
        product (independent source: is_inventory moves only)."""
        moves = self.env["stock.move"].search(
            [
                ("company_id", "=", company.id),
                ("product_id", "=", product.id),
                ("is_inventory", "=", True),
                ("state", "=", "done"),
            ]
        )
        delta = 0.0
        for move in moves:
            if move.location_dest_id.usage == "internal":
                delta += move.quantity
            if move.location_id.usage == "internal":
                delta -= move.quantity
        return delta

    def _on_hand(self, company, product):
        quants = self.env["stock.quant"].search(
            [
                ("company_id", "=", company.id),
                ("product_id", "=", product.id),
                ("location_id.usage", "=", "internal"),
            ]
        )
        return sum(quants.mapped("quantity"))

    # -------------------------------------------------------- presentation
    @api.model
    def format_report(self, result):
        """Render the reconciliation as a fixed-width text table."""
        lines = [
            "",
            "=" * 78,
            f"  DRESS-REHEARSAL EXAM — {result['company']}",
            f"  Period: {PERIOD_FROM} .. {PERIOD_TO}",
            "=" * 78,
            f"  {'CHECK':<48}{'EXPECTED':>12}{'ACTUAL':>12}  ",
            "-" * 78,
        ]
        for check in result["checks"]:
            status = "OK " if check["ok"] else "XX "
            lines.append(
                f"{status} {check['name']:<46}"
                f"{check['expected']:>12,.2f}{check['actual']:>12,.2f}"
            )
            if check["detail"]:
                lines.append(f"      ({check['detail']})")
        lines.append("-" * 78)
        verdict = "ALL CHECKS PASSED" if result["all_ok"] else "MISMATCHES FOUND — SEE XX ROWS"
        lines.append(f"  {verdict}")
        lines.append("=" * 78)
        return "\n".join(lines)
