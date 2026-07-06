# -*- coding: utf-8 -*-
"""Per-company payroll accounting configuration (journal + posting accounts).

Accounts are CONFIGURATION, not code: they live on the company and are
auto-resolved from the Ethiopian chart template ('et', extended by l10n_et_base)
when unset, so a SaaS tenant needs zero manual setup but any client can remap.
"""

from odoo import api, fields, models
from odoo.exceptions import UserError

# Default template xmlids on chart 'et' (core l10n_et + l10n_et_base additions).
DEFAULT_ACCOUNT_XMLIDS = {
    "l10n_et_salary_expense_account_id": "l10n_et6111",  # Salaries to permanent staff
    "l10n_et_pension_expense_account_id": "l10n_et6131",  # Contribution to staff pensions
    "l10n_et_paye_payable_account_id": "l10n_et_base_3009",  # PAYE Payable
    "l10n_et_pension_payable_account_id": "l10n_et3003",  # Pension contribution payable
    "l10n_et_net_wages_account_id": "l10n_et3004",  # Salary payable
    "l10n_et_payroll_deduction_account_id": "l10n_et2203",  # Advance to staff
}


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model_create_multi
    def create(self, vals_list):
        """New companies get the statutory allowance types seeded immediately
        (they are per-company configuration, like the WHT/cash-cap configs)."""
        companies = super().create(vals_list)
        allowance_types = self.env["l10n.et.allowance.type"].sudo()
        for company in companies:
            allowance_types._l10n_et_ensure_defaults(company)
        return companies

    l10n_et_payroll_journal_id = fields.Many2one(
        "account.journal",
        string="Payroll Journal",
        check_company=True,
        domain=[("type", "=", "general")],
        help="Journal for the monthly payroll entry. Auto-created ('PAY') on the "
        "first payroll confirmation if unset.",
    )
    l10n_et_salary_expense_account_id = fields.Many2one(
        "account.account",
        string="Salary Expense Account",
        check_company=True,
        help="Debited with the gross earnings of each payroll run.",
    )
    l10n_et_pension_expense_account_id = fields.Many2one(
        "account.account",
        string="Employer Pension Expense Account",
        check_company=True,
        help="Debited with the employer (11%) pension contribution.",
    )
    l10n_et_paye_payable_account_id = fields.Many2one(
        "account.account",
        string="PAYE Payable Account",
        check_company=True,
        help="Credited with employment income tax withheld, pending remittance "
        "to the Ministry of Revenue.",
    )
    l10n_et_pension_payable_account_id = fields.Many2one(
        "account.account",
        string="Pension Payable Account",
        check_company=True,
        help="Credited with employee (7%) + employer (11%) pension contributions.",
    )
    l10n_et_net_wages_account_id = fields.Many2one(
        "account.account",
        string="Net Wages Payable Account",
        check_company=True,
        help="Credited with the net pay owed to employees.",
    )
    l10n_et_payroll_deduction_account_id = fields.Many2one(
        "account.account",
        string="Payroll Deductions Account",
        check_company=True,
        help="Credited with other payslip deductions (loan/advance recoveries).",
    )

    def _l10n_et_payroll_ensure_config(self):
        """Resolve missing payroll accounts/journal, raising if any remain unset.

        Defaults come from the Ethiopian chart template records (per-company
        xmlids), so companies on chart 'et' work out of the box; other charts
        must configure the accounts on the company form.
        """
        self.ensure_one()
        chart_template = self.env["account.chart.template"].with_company(self)
        for field_name, xmlid in DEFAULT_ACCOUNT_XMLIDS.items():
            if not self[field_name]:
                account = chart_template.ref(xmlid, raise_if_not_found=False)
                if account:
                    self[field_name] = account
        if not self.l10n_et_payroll_journal_id:
            journal_model = self.env["account.journal"]
            journal = journal_model.search(
                [
                    *journal_model._check_company_domain(self),
                    ("type", "=", "general"),
                    ("code", "=", "PAY"),
                ],
                limit=1,
            )
            if not journal:
                # sudo: journal creation is accounting-admin territory, but the
                # payroll manager confirming the first run must not be blocked;
                # the created journal is a fixed, benign 'general' journal.
                journal = journal_model.sudo().create(
                    {
                        "name": self.env._("Payroll"),
                        "code": "PAY",
                        "type": "general",
                        "company_id": self.id,
                    }
                )
            self.l10n_et_payroll_journal_id = journal
        missing = [
            self._fields[field_name].string
            for field_name in DEFAULT_ACCOUNT_XMLIDS
            if not self[field_name]
        ]
        if missing:
            raise UserError(
                self.env._(
                    "Payroll accounting is not configured for %(company)s. "
                    "Set the following on the company form (Ethiopian Payroll "
                    "tab): %(fields)s",
                    company=self.display_name,
                    fields=", ".join(missing),
                )
            )
