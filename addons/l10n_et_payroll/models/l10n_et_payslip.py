# -*- coding: utf-8 -*-
"""Ethiopian payslip document + manual input lines.

All math comes from the tested reference calculator via the
``l10n.et.payslip.compute`` helper (CLAUDE.md rule #10 — never re-implement).
A payslip belongs to a payroll run; amounts freeze when the run is confirmed
(write-guarded), so a future rate change can never rewrite a posted month.
"""

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class L10nEtPayslip(models.Model):
    _name = "l10n.et.payslip"
    _description = "Ethiopian Payslip"
    _order = "run_id desc, employee_id"

    name = fields.Char(compute="_compute_name", store=True)
    run_id = fields.Many2one(
        "l10n.et.payroll.run",
        required=True,
        ondelete="cascade",
        index=True,
        help="The monthly batch this payslip belongs to.",
    )
    company_id = fields.Many2one(related="run_id.company_id", store=True, index=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        check_company=True,
        help="Employee this payslip pays.",
    )
    date_from = fields.Date(related="run_id.date_from", store=True)
    date_to = fields.Date(related="run_id.date_to", store=True)
    state = fields.Selection(related="run_id.state", store=True)
    basic_salary = fields.Monetary(
        required=True,
        help="Monthly basic salary — defaults from the employee's current "
        "version wage at generation; editable while the run is draft.",
    )
    is_citizen = fields.Boolean(
        string="Ethiopian Citizen",
        default=True,
        help="Pension (Proc 1268/2022) applies to Ethiopian citizens only.",
    )
    input_line_ids = fields.One2many(
        "l10n.et.payslip.input",
        "payslip_id",
        string="Input Lines",
        help="Manual earnings (overtime, bonus, allowances) and post-tax "
        "deductions (loans, advances) for the month.",
    )
    gross = fields.Monetary(
        compute="_compute_amounts",
        store=True,
        help="Basic + all earning inputs (taxable and exempt).",
    )
    taxable_income = fields.Monetary(
        compute="_compute_amounts",
        store=True,
        help="PAYE base: basic + taxable earning inputs.",
    )
    paye = fields.Monetary(
        string="PAYE",
        compute="_compute_amounts",
        store=True,
        help="Employment income tax per the bands effective on the period end.",
    )
    pension_employee = fields.Monetary(
        string="Pension (Employee)",
        compute="_compute_amounts",
        store=True,
        help="Employee pension contribution (basic salary only).",
    )
    pension_employer = fields.Monetary(
        string="Pension (Employer)",
        compute="_compute_amounts",
        store=True,
        help="Employer pension contribution (basic salary only).",
    )
    other_deductions = fields.Monetary(
        compute="_compute_amounts",
        store=True,
        help="Sum of post-tax deduction input lines.",
    )
    net_pay = fields.Monetary(
        compute="_compute_amounts",
        store=True,
        help="Gross − PAYE − employee pension − other deductions.",
    )

    _employee_unique_per_run = models.Constraint(
        "unique(run_id, employee_id)",
        "An employee can only appear once per payroll run.",
    )

    @api.depends("employee_id", "date_to")
    def _compute_name(self):
        """Human label, e.g. 'Abebe Kebede — 2026-07'."""
        for slip in self:
            period = slip.date_to and slip.date_to.strftime("%Y-%m") or "?"
            slip.name = f"{slip.employee_id.name or '?'} — {period}"

    @api.depends(
        "basic_salary",
        "is_citizen",
        "date_to",
        "input_line_ids.amount",
        "input_line_ids.category",
        "input_line_ids.taxable",
    )
    def _compute_amounts(self):
        """Delegate the payroll math to the reference calculator (via the
        compute helper) with the configuration effective on the period end."""
        for slip in self:
            earnings = slip.input_line_ids.filtered(lambda line: line.category == "earning")
            taxable_extra = sum(earnings.filtered("taxable").mapped("amount"))
            exempt_extra = sum(
                earnings.filtered(lambda line: not line.taxable).mapped("amount")
            )
            deductions = sum(
                slip.input_line_ids.filtered(lambda line: line.category == "deduction").mapped(
                    "amount"
                )
            )
            result = (
                slip.env["l10n.et.payslip.compute"]
                .with_company(slip.company_id or slip.env.company)
                .compute_for(
                    basic_salary=slip.basic_salary,
                    taxable_allowances=taxable_extra,
                    non_taxable_allowances=exempt_extra,
                    other_deductions=deductions,
                    is_citizen=slip.is_citizen,
                    on_date=slip.date_to,
                )
            )
            slip.gross = result["gross"]
            slip.taxable_income = result["taxable_income"]
            slip.paye = result["paye"]
            slip.pension_employee = result["pension_employee"]
            slip.pension_employer = result["pension_employer"]
            slip.other_deductions = deductions
            slip.net_pay = result["net_pay"]

    @api.constrains("basic_salary")
    def _check_basic_salary(self):
        """A negative basic salary is always a data-entry error."""
        for slip in self:
            if slip.basic_salary < 0:
                raise ValidationError(self.env._("Basic salary cannot be negative."))

    def write(self, vals):
        """Freeze payslips of confirmed runs: posted months are history."""
        protected = {"basic_salary", "is_citizen", "employee_id", "input_line_ids"}
        if protected & set(vals) and any(slip.state == "done" for slip in self):
            raise UserError(
                self.env._(
                    "This payslip belongs to a confirmed payroll run. Reset the "
                    "run to draft before editing."
                )
            )
        return super().write(vals)


class L10nEtPayslipInput(models.Model):
    _name = "l10n.et.payslip.input"
    _description = "Ethiopian Payslip Input Line"

    payslip_id = fields.Many2one(
        "l10n.et.payslip",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="payslip_id.company_id", store=True, index=True)
    currency_id = fields.Many2one(related="payslip_id.currency_id")
    name = fields.Char(
        required=True,
        help="What this line is, e.g. 'Overtime June', 'Loan repayment'.",
    )
    category = fields.Selection(
        selection=[("earning", "Earning"), ("deduction", "Deduction")],
        required=True,
        default="earning",
        help="Earnings add to gross; deductions are POST-TAX (loans, advances, "
        "court orders) and only reduce net pay.",
    )
    taxable = fields.Boolean(
        default=True,
        help="Earnings only: whether this amount enters the PAYE base "
        "(overtime and bonuses are taxable; some allowances are exempt within "
        "directive limits). Ignored on deductions — all deductions are post-tax.",
    )
    amount = fields.Monetary(
        required=True,
        help="Positive amount; the category decides the direction.",
    )

    @api.constrains("amount")
    def _check_amount(self):
        """Direction comes from the category; negative amounts would silently
        invert it."""
        for line in self:
            if line.amount < 0:
                raise ValidationError(
                    self.env._(
                        "Input amounts must be positive — use the category to "
                        "choose earning vs deduction."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Block adding lines to payslips of confirmed runs."""
        slips = self.env["l10n.et.payslip"].browse(
            [vals["payslip_id"] for vals in vals_list if vals.get("payslip_id")]
        )
        if any(slip.state == "done" for slip in slips):
            raise UserError(self.env._("Cannot add input lines to a confirmed payroll run."))
        return super().create(vals_list)

    def write(self, vals):
        """Block editing lines of confirmed runs."""
        if any(line.payslip_id.state == "done" for line in self):
            raise UserError(self.env._("Cannot edit input lines of a confirmed payroll run."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed_run(self):
        """Block removing lines from confirmed runs (posted months are history)."""
        if any(line.payslip_id.state == "done" for line in self):
            raise UserError(
                self.env._("Cannot remove input lines from a confirmed payroll run.")
            )
