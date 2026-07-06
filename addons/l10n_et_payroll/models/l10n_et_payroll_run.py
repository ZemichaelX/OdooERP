# -*- coding: utf-8 -*-
"""Monthly payroll batch run: generate payslips, confirm, post the journal entry.

Posting follows the Epic 3 pattern: idempotent (confirming twice raises, reset
cleanly removes the entry) with a chatter audit trail carrying the totals.
"""

import base64
import csv
import io
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_et_base.reference import et_tax_calc


class L10nEtPayrollRun(models.Model):
    _name = "l10n.et.payroll.run"
    _description = "Ethiopian Payroll Run"
    _inherit = ["mail.thread"]
    _order = "date_from desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        help="Payroll never crosses companies.",
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    date_from = fields.Date(
        required=True,
        default=lambda self: date.today().replace(day=1),
        help="First day of the pay period (inclusive).",
    )
    date_to = fields.Date(
        required=True,
        default=lambda self: date.today().replace(day=1) + relativedelta(months=1, days=-1),
        help="Last day of the pay period (inclusive); PAYE bands and pension "
        "rates effective on this date apply.",
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("done", "Confirmed")],
        default="draft",
        required=True,
        tracking=True,
    )
    employee_ids = fields.Many2many(
        "hr.employee",
        string="Employees",
        check_company=True,
        help="Employees to include when generating payslips. Defaults to all "
        "active employees of the company.",
    )
    payslip_ids = fields.One2many("l10n.et.payslip", "run_id", string="Payslips")
    move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        readonly=True,
        copy=False,
        help="The aggregated payroll entry posted at confirmation.",
    )
    bank_export_file = fields.Binary(
        string="Bank Transfer File",
        readonly=True,
        copy=False,
        help="Generic CSV salary transfer file (per-bank formats come later).",
    )
    bank_export_filename = fields.Char(readonly=True, copy=False)
    payslip_count = fields.Integer(compute="_compute_totals")
    total_gross = fields.Monetary(compute="_compute_totals")
    total_paye = fields.Monetary(string="Total PAYE", compute="_compute_totals")
    total_pension_employee = fields.Monetary(compute="_compute_totals")
    total_pension_employer = fields.Monetary(compute="_compute_totals")
    total_deductions = fields.Monetary(compute="_compute_totals")
    total_net = fields.Monetary(compute="_compute_totals")

    @api.depends("date_from", "date_to", "company_id")
    def _compute_name(self):
        """Label, e.g. 'Payroll 2026-07'."""
        for run in self:
            period = run.date_from and run.date_from.strftime("%Y-%m") or "?"
            run.name = self.env._("Payroll %(period)s", period=period)

    @api.depends(
        "payslip_ids.gross",
        "payslip_ids.paye",
        "payslip_ids.pension_employee",
        "payslip_ids.pension_employer",
        "payslip_ids.other_deductions",
        "payslip_ids.net_pay",
    )
    def _compute_totals(self):
        """Run-level sums, currency-rounded for display and posting."""
        for run in self:
            rounding = run.currency_id.round if run.currency_id else round
            run.payslip_count = len(run.payslip_ids)
            run.total_gross = rounding(sum(run.payslip_ids.mapped("gross")))
            run.total_paye = rounding(sum(run.payslip_ids.mapped("paye")))
            run.total_pension_employee = rounding(
                sum(run.payslip_ids.mapped("pension_employee"))
            )
            run.total_pension_employer = rounding(
                sum(run.payslip_ids.mapped("pension_employer"))
            )
            run.total_deductions = rounding(sum(run.payslip_ids.mapped("other_deductions")))
            run.total_net = rounding(sum(run.payslip_ids.mapped("net_pay")))

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        """A period must be a forward range."""
        for run in self:
            if run.date_from and run.date_to and run.date_from > run.date_to:
                raise UserError(self.env._("The period start must be before its end."))

    def action_generate_payslips(self):
        """Create one draft payslip per selected employee (skipping existing).

        Basic salary defaults from the employee's current version wage. The
        pension flag follows Proc 1268/2022 (accountant-verified Jul 2026):
        Ethiopian nationals mandatory (unset nationality counts as Ethiopian —
        the common case for local staff); foreign nationals of Ethiopian
        origin only when opted in; other foreign nationals excluded.
        """
        self.ensure_one()
        if self.state != "draft":
            raise UserError(self.env._("Payslips can only be generated on a draft run."))
        employees = self.employee_ids
        if not employees:
            employees = self.env["hr.employee"].search(
                [("company_id", "=", self.company_id.id)]
            )
            self.employee_ids = employees
        existing = self.payslip_ids.mapped("employee_id")
        created = self.env["l10n.et.payslip"]
        ethiopia = self.env.ref("base.et")
        for employee in employees - existing:
            # sudo: the monthly wage on hr.version is HR-manager-restricted;
            # generating payroll legitimately needs it regardless of which HR
            # group runs the batch. Only the wage value is read.
            wage = employee.sudo().current_version_id.wage
            is_ethiopian = not employee.country_id or employee.country_id == ethiopia
            pension_applies = is_ethiopian or employee.sudo().l10n_et_pension_opt_in
            created |= self.env["l10n.et.payslip"].create(
                {
                    "run_id": self.id,
                    "employee_id": employee.id,
                    "basic_salary": wage,
                    "is_citizen": pension_applies,
                }
            )
        if created:
            self.message_post(
                body=self.env._("Generated %(count)s payslip(s).", count=len(created))
            )
        return True

    def _prepare_move_line_vals(self):
        """Build the balanced payroll entry lines from the run totals.

        Debits: gross earnings to salary expense, employer pension to pension
        expense. Credits: PAYE payable, pension payable (EE + ER), other
        deductions (loan/advance recoveries), net wages payable. Zero lines are
        skipped. Balance holds by construction: net = gross − PAYE − EE pension
        − deductions.
        """
        company = self.company_id
        line_vals = []

        def add(account, debit=0.0, credit=0.0, label=""):
            if company.currency_id.is_zero(debit) and company.currency_id.is_zero(credit):
                return
            line_vals.append(
                Command.create(
                    {
                        "account_id": account.id,
                        "debit": debit,
                        "credit": credit,
                        "name": label,
                    }
                )
            )

        period = self.name
        add(
            company.l10n_et_salary_expense_account_id,
            debit=self.total_gross,
            label=self.env._("%(period)s — gross salaries", period=period),
        )
        add(
            company.l10n_et_pension_expense_account_id,
            debit=self.total_pension_employer,
            label=self.env._("%(period)s — employer pension", period=period),
        )
        add(
            company.l10n_et_paye_payable_account_id,
            credit=self.total_paye,
            label=self.env._("%(period)s — PAYE withheld", period=period),
        )
        add(
            company.l10n_et_pension_payable_account_id,
            credit=self.currency_id.round(
                self.total_pension_employee + self.total_pension_employer
            ),
            label=self.env._("%(period)s — pension contributions", period=period),
        )
        add(
            company.l10n_et_payroll_deduction_account_id,
            credit=self.total_deductions,
            label=self.env._("%(period)s — payslip deductions", period=period),
        )
        add(
            company.l10n_et_net_wages_account_id,
            credit=self.total_net,
            label=self.env._("%(period)s — net wages", period=period),
        )
        return line_vals

    def action_confirm(self):
        """Freeze the payslips and post the aggregated payroll journal entry.

        Idempotent: a confirmed run cannot be confirmed again; resetting to
        draft removes the entry first, so there is never more than one posted
        payroll entry per run.
        """
        self.ensure_one()
        if self.state != "draft":
            raise UserError(self.env._("This payroll run is already confirmed."))
        if not self.payslip_ids:
            raise UserError(self.env._("Generate payslips before confirming."))
        company = self.company_id
        company._l10n_et_payroll_ensure_config()
        # sudo: posting the payroll entry is an accounting operation, but payroll
        # confirmation is an HR-manager action; the entry is fixed-format,
        # balanced by construction, and fully logged in the chatter below.
        move = (
            self.env["account.move"]
            .sudo()
            .create(
                {
                    "move_type": "entry",
                    "journal_id": company.l10n_et_payroll_journal_id.id,
                    "company_id": company.id,
                    "date": self.date_to,
                    "ref": self.name,
                    "line_ids": self._prepare_move_line_vals(),
                }
            )
        )
        move.action_post()
        self.move_id = move
        self.state = "done"
        self.message_post(
            body=self.env._(
                "Payroll confirmed and posted (%(move)s): gross %(gross).2f, "
                "employer pension %(pension_er).2f, PAYE %(paye).2f, pension "
                "payable %(pension_total).2f, deductions %(deductions).2f, net "
                "wages %(net).2f. Rates per the effective-dated PAYE bands and "
                "pension configuration — re-verify with MoR before go-live.",
                move=move.name,
                gross=self.total_gross,
                pension_er=self.total_pension_employer,
                paye=self.total_paye,
                pension_total=self.total_pension_employee + self.total_pension_employer,
                deductions=self.total_deductions,
                net=self.total_net,
            )
        )
        return True

    def action_export_bank_file(self):
        """Build the generic salary transfer CSV and attach it to the run.

        Columns: employee name, bank name, account number, net pay — plus a
        totals row. Employees without a bank account get empty bank columns and
        a chatter warning, so the file is always complete for review.
        """
        self.ensure_one()
        if self.state != "done":
            raise UserError(
                self.env._("Confirm the payroll run before exporting the bank file.")
            )
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Employee Name", "Bank Name", "Account Number", "Net Pay"])
        missing_accounts = []
        for slip in self.payslip_ids.sorted(lambda s: s.employee_id.name or ""):
            # sudo: bank account fields on hr.employee are HR-group restricted;
            # building the salary file legitimately needs account number + bank.
            account = slip.employee_id.sudo().primary_bank_account_id
            if not account:
                missing_accounts.append(slip.employee_id.name)
            # Neutralize spreadsheet formula injection: employee/bank names are
            # user-influenced and this file is opened in Excel/LibreOffice.
            writer.writerow(
                [
                    et_tax_calc.csv_safe_cell(slip.employee_id.name),
                    et_tax_calc.csv_safe_cell(account.bank_id.name or ""),
                    et_tax_calc.csv_safe_cell(account.acc_number or ""),
                    f"{slip.net_pay:.2f}",
                ]
            )
        writer.writerow(["TOTAL", "", "", f"{self.total_net:.2f}"])
        self.bank_export_file = base64.b64encode(buffer.getvalue().encode("utf-8"))
        self.bank_export_filename = f"salary_transfer_{self.date_to:%Y_%m}.csv"
        if missing_accounts:
            self.message_post(
                body=self.env._(
                    "Bank file exported with MISSING bank accounts for: "
                    "%(names)s. Add bank accounts on the employee records and "
                    "re-export before sending to the bank.",
                    names=", ".join(missing_accounts),
                )
            )
        else:
            self.message_post(body=self.env._("Bank transfer file exported."))
        return True

    def _l10n_et_identifier_warnings(self):
        """Return human-readable warnings for missing statutory identifiers.

        MoR rejects PAYE declarations without employee TINs and pension
        remittances without POESSA registration numbers; surfacing this at
        print time (chatter + report banner) beats a rejected filing.
        """
        self.ensure_one()
        # sudo: identifier fields on hr.employee are HR-group restricted; the
        # report needs presence/absence only.
        missing_tin = self.payslip_ids.filtered(
            lambda s: not s.employee_id.sudo().l10n_et_tin
        ).mapped("employee_id.name")
        missing_pension = self.payslip_ids.filtered(
            lambda s: s.is_citizen and not s.employee_id.sudo().l10n_et_pension_id
        ).mapped("employee_id.name")
        warnings = []
        if missing_tin:
            warnings.append(
                self.env._(
                    "Missing employee TIN (PAYE declaration will be rejected by "
                    "MoR): %(names)s",
                    names=", ".join(missing_tin),
                )
            )
        if missing_pension:
            warnings.append(
                self.env._(
                    "Missing POESSA pension ID (pension remittance will be "
                    "rejected): %(names)s",
                    names=", ".join(missing_pension),
                )
            )
        return warnings

    def _l10n_et_post_identifier_warnings(self):
        """Log identifier warnings on the run's chatter (audit trail)."""
        self.ensure_one()
        for warning in self._l10n_et_identifier_warnings():
            self.message_post(body=warning)

    def action_print_paye_declaration(self):
        """Print the PAYE monthly declaration, warning on missing TINs."""
        self.ensure_one()
        self._l10n_et_post_identifier_warnings()
        return self.env.ref("l10n_et_payroll.action_report_paye_declaration").report_action(
            self
        )

    def action_print_pension_schedule(self):
        """Print the pension remittance schedule, warning on missing IDs."""
        self.ensure_one()
        self._l10n_et_post_identifier_warnings()
        return self.env.ref("l10n_et_payroll.action_report_pension_schedule").report_action(
            self
        )

    @api.model
    def _l10n_et_payroll_generate_demo(self):
        """Create the demo payroll on the ET demo company (demo data only).

        Three employees covering the golden cases: basic 10,000; basic 10,000 +
        taxable overtime 2,000; basic 1,800 (below the PAYE threshold) — the
        last one deliberately WITHOUT a POESSA pension ID to demonstrate the
        missing-identifier warning on the pension remittance schedule. The run
        is generated, confirmed and the bank file exported. Guarded and
        idempotent, like the l10n_et_base demo loader.
        """
        company = self.env.ref("base.demo_company_et", raise_if_not_found=False)
        if not company or company.chart_template != "et":
            return
        if self.search_count([("company_id", "=", company.id)]):
            return
        ethiopia = self.env.ref("base.et")
        bank = self.env["res.bank"].create(
            {"name": "Commercial Bank of Ethiopia", "bic": "CBETETAA"}
        )
        employee_model = self.env["hr.employee"].with_company(company)

        def make_employee(name, wage, tin, pension_id, account_number):
            employee = employee_model.create(
                {
                    "name": name,
                    "company_id": company.id,
                    "country_id": ethiopia.id,
                    "l10n_et_tin": tin,
                    "l10n_et_pension_id": pension_id,
                }
            )
            # sudo: wage/bank fields are HR-group restricted; demo loading runs
            # as the superuser anyway, sudo keeps it explicit.
            employee.sudo().version_id.write({"wage": wage})
            partner = employee.work_contact_id
            if partner and account_number:
                account = self.env["res.partner.bank"].create(
                    {
                        "partner_id": partner.id,
                        "bank_id": bank.id,
                        "acc_number": account_number,
                    }
                )
                employee.sudo().bank_account_ids = [Command.link(account.id)]
            return employee

        emp_basic = make_employee(
            "Almaz Tadesse", 10000, "0012121212", "POESSA-001122", "1000200030001"
        )
        emp_overtime = make_employee(
            "Bekele Worku", 10000, "0013131313", "POESSA-003344", "1000200030002"
        )
        # No pension ID: exercises the missing-identifier warning path.
        emp_low = make_employee("Chaltu Deme", 1800, "0014141414", False, "1000200030003")

        run = self.create(
            {
                "company_id": company.id,
                "date_from": "2026-07-01",
                "date_to": "2026-07-31",
                "employee_ids": [Command.set((emp_basic | emp_overtime | emp_low).ids)],
            }
        )
        run.action_generate_payslips()
        overtime_slip = run.payslip_ids.filtered(lambda slip: slip.employee_id == emp_overtime)
        self.env["l10n.et.payslip.input"].create(
            {
                "payslip_id": overtime_slip.id,
                "name": "Overtime July",
                "category": "earning",
                "taxable": True,
                "amount": 2000.0,
            }
        )
        run.action_confirm()
        run.action_export_bank_file()
        run._l10n_et_post_identifier_warnings()

    def action_reset_to_draft(self):
        """Undo a confirmation: cancel and remove the journal entry, reopen."""
        self.ensure_one()
        if self.state != "done":
            raise UserError(self.env._("Only confirmed runs can be reset."))
        move = self.move_id
        if move:
            # Refuse to tear down an entry whose payables were already settled:
            # unlinking it would silently un-reconcile the remittance/salary
            # payments and desync the ledger.
            if move.sudo().line_ids.filtered(
                lambda line: line.matched_debit_ids or line.matched_credit_ids
            ):
                raise UserError(
                    self.env._(
                        "This payroll entry has reconciled lines (salary/PAYE/"
                        "pension already paid). Un-reconcile those payments "
                        "before resetting the run."
                    )
                )
            # sudo: same justification as posting — symmetric accounting cleanup
            # of the run's own fixed-format entry, logged below.
            move.sudo().button_draft()
            move.sudo().unlink()
        self.move_id = False
        # A stale bank file carries the pre-reset net amounts; drop it so a
        # re-export is forced after any edit.
        self.bank_export_file = False
        self.bank_export_filename = False
        self.state = "draft"
        self.message_post(body=self.env._("Payroll reset to draft; journal entry removed."))
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        """A confirmed run owns a posted journal entry; deleting it would
        orphan the GL entry and cascade-delete the payslips (posted history).
        Reset to draft first."""
        if any(run.state == "done" for run in self):
            raise UserError(
                self.env._(
                    "Cannot delete a confirmed payroll run — reset it to draft "
                    "first (that removes the journal entry cleanly)."
                )
            )
