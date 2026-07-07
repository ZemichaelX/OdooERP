# -*- coding: utf-8 -*-
"""Provision the rehearsal tenant inside a transaction and prove every book
ties out. The hand-computed payroll totals are asserted explicitly here so a
silent regression in the allowance-cap or pension logic is caught by value,
not only by the self-consistent exam."""

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDressRehearsal(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["sapian.dress.rehearsal"]._provision(
            company_name="Rehearsal Exam Co"
        )
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))
        cls.result = cls.env["sapian.dress.rehearsal.exam"].run(cls.company)

    def test_all_checks_pass(self):
        """The whole reconciliation is green — any mismatch is a finding."""
        failures = [c for c in self.result["checks"] if not c["ok"]]
        report = self.env["sapian.dress.rehearsal.exam"].format_report(self.result)
        self.assertFalse(
            failures,
            "Dress-rehearsal exam has mismatches:\n" + report,
        )
        self.assertTrue(self.result["all_ok"])

    def test_payroll_hand_computed_totals(self):
        """Explicit hand-computed August payroll (5 employees):
        gross 59,500 · taxable 58,000 · PAYE 11,650 · pension EE 2,905 /
        ER 4,565 · net 44,945 — incl. the transport allowance capped at 25% of
        6,000 = 1,500 (< 2,200) and the pension-exempt foreigner."""
        run = self.env["l10n.et.payroll.run"].search(
            [("company_id", "=", self.company.id)], limit=1
        )
        self.assertEqual(run.total_gross, 59500.0)
        self.assertEqual(run.total_paye, 11650.0)
        self.assertEqual(run.total_pension_employee, 2905.0)
        self.assertEqual(run.total_pension_employer, 4565.0)
        self.assertEqual(run.total_net, 44945.0)

    def test_transport_allowance_capped_from_config(self):
        """The transport employee's taxable income is 7,500 (basic 6,000 +
        taxable transport excess 1,500), proving the config-driven cap fired."""
        run = self.env["l10n.et.payroll.run"].search(
            [("company_id", "=", self.company.id)], limit=1
        )
        slip = run.payslip_ids.filtered(
            lambda s: s.input_line_ids.filtered("allowance_type_id")
        )
        self.assertEqual(len(slip), 1)
        self.assertEqual(slip.basic_salary, 6000.0)
        self.assertEqual(slip.taxable_income, 7500.0)
        self.assertEqual(slip.gross, 9000.0)  # 6,000 + 1,500 exempt + 1,500 taxable

    def test_foreigner_pension_exempt(self):
        """The foreign national's payslip carries zero pension."""
        run = self.env["l10n.et.payroll.run"].search(
            [("company_id", "=", self.company.id)], limit=1
        )
        foreigner = run.payslip_ids.filtered(lambda s: not s.is_citizen)
        self.assertEqual(len(foreigner), 1)
        self.assertEqual(foreigner.pension_employee, 0.0)

    def test_wht_three_profiles_present(self):
        """The WHT summary shows all three rate profiles (3% / 30% / 15%)."""
        summary = self.env["l10n.et.wht.summary"].search(
            [("company_id", "=", self.company.id)], limit=1
        )
        rates = set(summary._get_report_data()["totals_by_rate"])
        self.assertEqual(rates, {3.0, 30.0, 15.0})

    def test_reports_tie_out_to_gl(self):
        """Both statutory reports reconcile to the general ledger."""
        vat = self.env["l10n.et.vat.declaration"].search(
            [("company_id", "=", self.company.id)], limit=1
        )
        wht = self.env["l10n.et.wht.summary"].search(
            [("company_id", "=", self.company.id)], limit=1
        )
        self.assertTrue(vat._get_report_data()["tie_out_ok"])
        self.assertTrue(wht._get_report_data()["tie_out_ok"])
