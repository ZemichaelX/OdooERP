# -*- coding: utf-8 -*-
"""Tests for the bank transfer export, payslip PDF and statutory reports."""

import base64

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPayrollReports(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("et")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.env.user.group_ids += cls.env.ref("hr.group_hr_manager")
        cls.company.partner_id.l10n_et_tin = "0099887766"
        cls.bank = cls.env["res.bank"].create({"name": "Test Bank ET"})
        ethiopia = cls.env.ref("base.et")

        def employee(name, wage, tin=False, pension_id=False, account=False):
            emp = cls.env["hr.employee"].create(
                {
                    "name": name,
                    "company_id": cls.company.id,
                    "country_id": ethiopia.id,
                    "l10n_et_tin": tin,
                    "l10n_et_pension_id": pension_id,
                }
            )
            emp.version_id.write({"wage": wage})
            if account and emp.work_contact_id:
                bank_account = cls.env["res.partner.bank"].create(
                    {
                        "partner_id": emp.work_contact_id.id,
                        "bank_id": cls.bank.id,
                        "acc_number": account,
                    }
                )
                emp.bank_account_ids = [Command.link(bank_account.id)]
            return emp

        cls.emp_full = employee(
            "Complete Employee",
            10000,
            tin="0012121212",
            pension_id="POESSA-0001",
            account="ACC-001",
        )
        cls.emp_no_pension_id = employee(
            "No Pension ID",
            1800,
            tin="0013131313",
            account="ACC-002",
        )

        cls.payroll_run = cls.env["l10n.et.payroll.run"].create(
            {
                "company_id": cls.company.id,
                "date_from": "2026-07-01",
                "date_to": "2026-07-31",
                "employee_ids": [Command.set((cls.emp_full | cls.emp_no_pension_id).ids)],
            }
        )
        cls.payroll_run.action_generate_payslips()
        cls.payroll_run.action_confirm()

    def _render(self, report_xmlid, records):
        return (
            self.env["ir.actions.report"]
            ._render_qweb_html(report_xmlid, records.ids)[0]
            .decode()
        )

    def test_employee_tin_validated_and_normalized(self):
        """Employee TINs go through the reference validator like partner TINs."""
        emp = self.env["hr.employee"].create(
            {
                "name": "Hyphen TIN",
                "company_id": self.company.id,
                "l10n_et_tin": "0014-1414-14",
            }
        )
        self.assertEqual(emp.l10n_et_tin, "0014141414")
        with self.assertRaises(ValidationError):
            self.env["hr.employee"].create(
                {
                    "name": "Bad TIN",
                    "company_id": self.company.id,
                    "l10n_et_tin": "12345",
                }
            )

    def test_bank_export_content_and_totals(self):
        """The CSV has one row per employee (name, bank, account, net) plus a
        totals row matching the run total."""
        self.payroll_run.action_export_bank_file()
        content = base64.b64decode(self.payroll_run.bank_export_file).decode()
        lines = [line for line in content.strip().splitlines() if line]
        self.assertEqual(lines[0], "Employee Name,Bank Name,Account Number,Net Pay")
        self.assertIn("Complete Employee,Test Bank ET,ACC-001,7650.00", lines[1])
        self.assertIn("No Pension ID,Test Bank ET,ACC-002,1674.00", lines[2])
        self.assertEqual(lines[-1], f"TOTAL,,,{self.payroll_run.total_net:.2f}")

    def test_bank_export_requires_confirmed_run(self):
        run = self.env["l10n.et.payroll.run"].create(
            {
                "company_id": self.company.id,
                "date_from": "2026-08-01",
                "date_to": "2026-08-31",
            }
        )
        with self.assertRaises(UserError):
            run.action_export_bank_file()

    def test_payslip_pdf_renders_breakdown(self):
        """The payslip shows employer TIN, employee TIN, PAYE, pension, net."""
        slip = self.payroll_run.payslip_ids.filtered(lambda s: s.employee_id == self.emp_full)
        html = self._render("l10n_et_payroll.report_payslip", slip)
        self.assertIn("0099887766", html, "employer TIN missing")
        self.assertIn("0012121212", html, "employee TIN missing")
        self.assertIn("1,650", html, "PAYE missing")
        self.assertIn("7,650", html, "net pay missing")

    def test_paye_declaration_lists_tins_and_total(self):
        html = self._render("l10n_et_payroll.report_paye_declaration", self.payroll_run)
        self.assertIn("0012121212", html)
        self.assertIn("0013131313", html)
        self.assertIn("1,650", html)

    def test_pension_schedule_warns_on_missing_pension_id(self):
        """The employee without a POESSA ID is flagged MISSING and the warning
        banner names them; the complete employee's ID is listed."""
        html = self._render("l10n_et_payroll.report_pension_schedule", self.payroll_run)
        self.assertIn("POESSA-0001", html)
        self.assertIn("MISSING", html)
        self.assertIn("No Pension ID", html)
        warnings = self.payroll_run._l10n_et_identifier_warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("No Pension ID", warnings[0])

    def test_paye_declaration_warns_on_missing_tin(self):
        """Removing a TIN adds a declaration warning naming the employee."""
        self.payroll_run.action_reset_to_draft()
        self.emp_full.l10n_et_tin = False
        self.payroll_run.action_confirm()
        warnings = self.payroll_run._l10n_et_identifier_warnings()
        self.assertTrue(any("Complete Employee" in warning for warning in warnings))
        html = self._render("l10n_et_payroll.report_paye_declaration", self.payroll_run)
        self.assertIn("MISSING", html)

    def test_print_actions_log_warnings_to_chatter(self):
        """The print buttons post the identifier warnings for the audit trail."""
        before = len(self.payroll_run.message_ids)
        self.payroll_run.action_print_pension_schedule()
        self.assertGreater(len(self.payroll_run.message_ids), before)
