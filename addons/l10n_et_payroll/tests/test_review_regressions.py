# -*- coding: utf-8 -*-
"""Regression tests for the Jul 2026 adversarial-review findings (payroll).

Each test reproduces the reported defect's exact path and asserts the fix.
"""

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPayrollReviewRegressions(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("et")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.ethiopia = cls.env.ref("base.et")
        cls.env.user.group_ids += cls.env.ref("hr.group_hr_manager")
        cls.transport = cls.env["l10n.et.allowance.type"].search(
            [("company_id", "=", cls.company.id), ("code", "=", "transport")], limit=1
        )
        cls.emp = cls.env["hr.employee"].create(
            {"name": "Regress One", "company_id": cls.company.id, "country_id": cls.ethiopia.id}
        )
        cls.emp.version_id.write({"wage": 10000})

    def _run(self):
        run = self.env["l10n.et.payroll.run"].create(
            {
                "company_id": self.company.id,
                "date_from": "2026-07-01",
                "date_to": "2026-07-31",
                "employee_ids": [Command.set(self.emp.ids)],
            }
        )
        run.action_generate_payslips()
        return run

    def _add_transport(self, slip, amount, name="Transport"):
        return self.env["l10n.et.payslip.input"].create(
            {
                "payslip_id": slip.id,
                "name": name,
                "category": "earning",
                "allowance_type_id": self.transport.id,
                "amount": amount,
            }
        )

    def test_multiple_transport_lines_share_one_ceiling(self):
        """R1#2: two transport lines get ONE monthly 2,200 ceiling, not two.
        2×2,200 = 4,400 → exempt 2,200, taxable 2,200 → PAYE on 12,200."""
        run = self._run()
        slip = run.payslip_ids
        self._add_transport(slip, 2200, "Transport")
        self._add_transport(slip, 2200, "Transport adjustment")
        self.assertEqual(slip.taxable_income, 12200.0)
        self.assertEqual(slip.paye, 2310.0)  # 0.30×12,200 − 1,350

    def test_allowance_edit_does_not_rewrite_confirmed_payslip(self):
        """R1#1/R3#1: editing the transport ceiling must NOT recompute a
        payslip whose run is confirmed (posted month is history)."""
        run = self._run()
        slip = run.payslip_ids
        self._add_transport(slip, 3000)
        self.assertEqual(slip.paye, 1890.0)  # exempt 2,200 / taxable 800
        run.action_confirm()
        frozen_paye = slip.paye
        self.transport.write({"cap_amount": 2600})  # a later-year ceiling change
        slip.invalidate_recordset()
        self.assertEqual(slip.paye, frozen_paye, "confirmed payslip must stay frozen")

    def test_confirmed_run_cannot_be_deleted(self):
        """R3#2: deleting a confirmed run would orphan the posted journal."""
        run = self._run()
        run.action_confirm()
        with self.assertRaises(UserError):
            run.unlink()

    def test_confirmed_payslip_cannot_be_deleted(self):
        run = self._run()
        run.action_confirm()
        with self.assertRaises(UserError):
            run.payslip_ids.unlink()

    def test_reset_blocked_when_move_reconciled(self):
        """R3#8: resetting a run whose payables were paid would un-reconcile
        the counterpart payment silently."""
        run = self._run()
        run.action_confirm()
        # Reconcile the net-wages payable line against a manual counterpart.
        net_line = run.move_id.line_ids.filtered(
            lambda line: line.account_id == self.company.l10n_et_net_wages_account_id
        )
        counter = self.env["account.move"].create(
            {
                "move_type": "entry",
                "company_id": self.company.id,
                "date": "2026-07-31",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.company.l10n_et_net_wages_account_id.id,
                            "debit": net_line.credit,
                            "credit": 0.0,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.company_data["default_account_revenue"].id,
                            "debit": 0.0,
                            "credit": net_line.credit,
                        }
                    ),
                ],
            }
        )
        counter.action_post()
        (
            net_line
            | counter.line_ids.filtered(
                lambda line: line.account_id == self.company.l10n_et_net_wages_account_id
            )
        ).reconcile()
        with self.assertRaises(UserError):
            run.action_reset_to_draft()

    def test_bank_file_cleared_on_reset(self):
        """R3#7: a stale salary CSV must not survive a reset-to-draft."""
        run = self._run()
        run.action_confirm()
        run.action_export_bank_file()
        self.assertTrue(run.bank_export_file)
        # Un-reconciled run resets cleanly and drops the file.
        run.action_reset_to_draft()
        self.assertFalse(run.bank_export_file)
        self.assertFalse(run.bank_export_filename)

    def test_paye_band_overlap_rejected(self):
        """R1#4: a band overlapping the seeded generation in time AND income
        without closing the old effective_to must be refused. Every company now
        owns seeded bands (A1: 2,000–4,000 @15% open-ended among them), so a new
        open-ended 2,000–4,000 band overlaps and is rejected."""
        band_model = self.env["l10n.et.paye.band"]
        seeded = band_model.search(
            [
                ("company_id", "=", self.company.id),
                ("lower_bound", "=", 2000.0),
                ("upper_bound", "=", 4000.0),
            ]
        )
        self.assertTrue(seeded, "the company owns seeded PAYE bands (A1)")
        with self.assertRaises(ValidationError):
            band_model.create(
                {
                    "company_id": self.company.id,
                    "lower_bound": 2000.0,
                    "upper_bound": 4000.0,
                    "rate": 0.20,
                    "deduction": 400.0,
                    "effective_from": "2026-10-01",
                }
            )

    def test_bank_csv_neutralizes_formula_injection(self):
        """R2#4: a malicious employee name must be defused in the salary CSV."""
        import base64

        evil = self.env["hr.employee"].create(
            {
                "name": "=WEBSERVICE(1)",
                "company_id": self.company.id,
                "country_id": self.ethiopia.id,
            }
        )
        evil.version_id.write({"wage": 5000})
        run = self.env["l10n.et.payroll.run"].create(
            {
                "company_id": self.company.id,
                "date_from": "2026-07-01",
                "date_to": "2026-07-31",
                "employee_ids": [Command.set(evil.ids)],
            }
        )
        run.action_generate_payslips()
        run.action_confirm()
        run.action_export_bank_file()
        content = base64.b64decode(run.bank_export_file).decode("utf-8")
        self.assertIn("'=WEBSERVICE(1)", content)
        self.assertNotIn(",=WEBSERVICE(1)", content)
