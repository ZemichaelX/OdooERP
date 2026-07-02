# -*- coding: utf-8 -*-
"""Integration tests for the payroll batch run and journal posting.

Golden values are hand-computed from the Proc 1395/2025 PAYE bands and the
7%/11% pension split, mirroring the reference-calculator goldens in tests_fast/.
"""

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPayrollRun(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("et")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.ethiopia = cls.env.ref("base.et")
        # The accounting test user runs the payroll in these tests: grant HR
        # manager so employee/payslip creation passes the payroll ACLs.
        cls.env.user.group_ids += cls.env.ref("hr.group_hr_manager")

        def employee(name, wage):
            emp = cls.env["hr.employee"].create(
                {
                    "name": name,
                    "company_id": cls.company.id,
                    "country_id": cls.ethiopia.id,
                }
            )
            emp.version_id.write({"wage": wage})
            return emp

        cls.emp_10k = employee("Golden One", 10000)
        cls.emp_10k_ot = employee("Golden Two (overtime)", 10000)
        cls.emp_low = employee("Below Threshold", 1800)

    def _create_run(self, employees):
        return self.env["l10n.et.payroll.run"].create(
            {
                "company_id": self.company.id,
                "date_from": "2026-07-01",
                "date_to": "2026-07-31",
                "employee_ids": [Command.set(employees.ids)],
            }
        )

    def _slip(self, run, employee):
        return run.payslip_ids.filtered(lambda s: s.employee_id == employee)

    def test_golden_case_basic_10000(self):
        """Basic 10,000, no inputs → PAYE 1,650, pension 700/1,100, net 7,650."""
        run = self._create_run(self.emp_10k)
        run.action_generate_payslips()
        slip = self._slip(run, self.emp_10k)
        self.assertEqual(slip.basic_salary, 10000.0)
        self.assertEqual(slip.paye, 1650.0)
        self.assertEqual(slip.pension_employee, 700.0)
        self.assertEqual(slip.pension_employer, 1100.0)
        self.assertEqual(slip.net_pay, 7650.0)

    def test_golden_case_journal_posting(self):
        """Single 10,000 slip journal: expenses 11,100 (10,000 + 1,100 ER
        pension); payables PAYE 1,650 + pension 1,800 + net 7,650; balanced."""
        run = self._create_run(self.emp_10k)
        run.action_generate_payslips()
        run.action_confirm()
        move = run.move_id
        self.assertEqual(move.state, "posted")
        self.assertEqual(move.journal_id.code, "PAY")

        def line_for(account):
            return move.line_ids.filtered(lambda line: line.account_id == account)

        company = self.company
        self.assertEqual(line_for(company.l10n_et_salary_expense_account_id).debit, 10000.0)
        self.assertEqual(line_for(company.l10n_et_pension_expense_account_id).debit, 1100.0)
        self.assertEqual(line_for(company.l10n_et_paye_payable_account_id).credit, 1650.0)
        self.assertEqual(line_for(company.l10n_et_pension_payable_account_id).credit, 1800.0)
        self.assertEqual(line_for(company.l10n_et_net_wages_account_id).credit, 7650.0)
        self.assertEqual(sum(move.line_ids.mapped("debit")), 11100.0)
        self.assertEqual(
            sum(move.line_ids.mapped("debit")), sum(move.line_ids.mapped("credit"))
        )
        # Default accounts resolved from the Ethiopian chart.
        self.assertEqual(company.l10n_et_paye_payable_account_id.code, "300900")
        self.assertEqual(company.l10n_et_net_wages_account_id.code, "300400")

    def test_golden_case_taxable_overtime(self):
        """Basic 10,000 + taxable overtime 2,000 → PAYE on 12,000 = 2,250;
        pension still on basic only (700/1,100); net 9,050."""
        run = self._create_run(self.emp_10k_ot)
        run.action_generate_payslips()
        slip = self._slip(run, self.emp_10k_ot)
        self.env["l10n.et.payslip.input"].create(
            {
                "payslip_id": slip.id,
                "name": "Overtime July",
                "category": "earning",
                "taxable": True,
                "amount": 2000.0,
            }
        )
        self.assertEqual(slip.taxable_income, 12000.0)
        self.assertEqual(slip.paye, 2250.0)
        self.assertEqual(slip.pension_employee, 700.0)
        self.assertEqual(slip.pension_employer, 1100.0)
        self.assertEqual(slip.net_pay, 9050.0)

    def test_non_taxable_earning_excluded_from_paye(self):
        """An exempt allowance raises gross and net but not the PAYE base."""
        run = self._create_run(self.emp_10k)
        run.action_generate_payslips()
        slip = self._slip(run, self.emp_10k)
        self.env["l10n.et.payslip.input"].create(
            {
                "payslip_id": slip.id,
                "name": "Transport allowance (exempt)",
                "category": "earning",
                "taxable": False,
                "amount": 600.0,
            }
        )
        self.assertEqual(slip.taxable_income, 10000.0)
        self.assertEqual(slip.paye, 1650.0)
        self.assertEqual(slip.gross, 10600.0)
        self.assertEqual(slip.net_pay, 8250.0)

    def test_deduction_reduces_net_posts_to_deduction_account(self):
        """A 500 loan repayment: net 7,150; the journal credits the deductions
        account and still balances."""
        run = self._create_run(self.emp_10k)
        run.action_generate_payslips()
        slip = self._slip(run, self.emp_10k)
        self.env["l10n.et.payslip.input"].create(
            {
                "payslip_id": slip.id,
                "name": "Loan repayment",
                "category": "deduction",
                "amount": 500.0,
            }
        )
        self.assertEqual(slip.net_pay, 7150.0)
        run.action_confirm()
        move = run.move_id
        deduction_line = move.line_ids.filtered(
            lambda line: line.account_id == self.company.l10n_et_payroll_deduction_account_id
        )
        self.assertEqual(deduction_line.credit, 500.0)
        self.assertEqual(
            sum(move.line_ids.mapped("debit")), sum(move.line_ids.mapped("credit"))
        )

    def test_below_threshold_no_paye(self):
        """Basic 1,800 is under the tax-free band: PAYE 0, pension still due."""
        run = self._create_run(self.emp_low)
        run.action_generate_payslips()
        slip = self._slip(run, self.emp_low)
        self.assertEqual(slip.paye, 0.0)
        self.assertEqual(slip.pension_employee, 126.0)
        self.assertEqual(slip.pension_employer, 198.0)
        self.assertEqual(slip.net_pay, 1674.0)

    def test_batch_of_three_totals_and_balance(self):
        """The full demo batch: totals aggregate correctly and the single
        journal entry balances."""
        employees = self.emp_10k | self.emp_10k_ot | self.emp_low
        run = self._create_run(employees)
        run.action_generate_payslips()
        self.assertEqual(len(run.payslip_ids), 3)
        self.env["l10n.et.payslip.input"].create(
            {
                "payslip_id": self._slip(run, self.emp_10k_ot).id,
                "name": "Overtime July",
                "category": "earning",
                "taxable": True,
                "amount": 2000.0,
            }
        )
        run.action_confirm()
        self.assertEqual(run.total_gross, 23800.0)
        self.assertEqual(run.total_paye, 3900.0)
        self.assertEqual(run.total_net, 18374.0)
        move = run.move_id
        self.assertEqual(sum(move.line_ids.mapped("debit")), 26198.0)
        self.assertEqual(
            sum(move.line_ids.mapped("debit")), sum(move.line_ids.mapped("credit"))
        )

    def test_confirm_is_idempotent_and_reset_cleans_up(self):
        """Double confirm raises; reset removes the entry; reconfirm creates
        exactly one new posted entry."""
        run = self._create_run(self.emp_10k)
        run.action_generate_payslips()
        run.action_confirm()
        first_move = run.move_id
        with self.assertRaises(UserError):
            run.action_confirm()
        run.action_reset_to_draft()
        self.assertFalse(run.move_id)
        self.assertFalse(first_move.exists())
        run.action_confirm()
        self.assertTrue(run.move_id.exists())
        self.assertEqual(run.move_id.state, "posted")

    def test_confirmed_run_payslips_frozen(self):
        """Edits to payslips or their inputs are blocked once confirmed."""
        run = self._create_run(self.emp_10k)
        run.action_generate_payslips()
        slip = self._slip(run, self.emp_10k)
        run.action_confirm()
        with self.assertRaises(UserError):
            slip.basic_salary = 12000
        with self.assertRaises(UserError):
            self.env["l10n.et.payslip.input"].create(
                {
                    "payslip_id": slip.id,
                    "name": "Late bonus",
                    "category": "earning",
                    "amount": 1000.0,
                }
            )

    def test_generate_skips_existing_and_is_rerunnable(self):
        """Re-generating never duplicates payslips."""
        run = self._create_run(self.emp_10k | self.emp_low)
        run.action_generate_payslips()
        run.action_generate_payslips()
        self.assertEqual(len(run.payslip_ids), 2)
