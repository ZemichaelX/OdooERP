# -*- coding: utf-8 -*-
"""Compute helper wrapping the tested pure-Python reference calculator.

The calculator lives in ../reference/et_payroll_calc.py as plain Python (so it can be unit
tested with pytest, no Odoo needed). We load it by file path to avoid coupling the Odoo
package layout to the standalone test layout."""
import importlib.util
import os
import sys as _sys

from odoo import api, models

_CALC_PATH = os.path.join(os.path.dirname(__file__), "..", "reference", "et_payroll_calc.py")
_spec = importlib.util.spec_from_file_location("et_payroll_calc", _CALC_PATH)
_calc = importlib.util.module_from_spec(_spec)
_sys.modules[_spec.name] = _calc
_spec.loader.exec_module(_calc)


class L10nEtPayslipCompute(models.AbstractModel):
    _name = "l10n.et.payslip.compute"
    _description = "Ethiopian Payslip Computation Helper"

    @api.model
    def compute_for(self, basic_salary, taxable_allowances=0.0,
                    non_taxable_allowances=0.0, other_deductions=0.0,
                    is_citizen=True, on_date=None):
        """Return a dict payslip result using the company's active bands/pension config."""
        bands = self.env["l10n.et.paye.band"].get_active_bands(on_date=on_date) or _calc.DEFAULT_PAYE_BANDS
        cfg = self.env["l10n.et.pension.config"].search(
            [("company_id", "=", self.env.company.id)], order="effective_from desc", limit=1
        )
        ee_rate = cfg.employee_rate if cfg else 0.07
        er_rate = cfg.employer_rate if cfg else 0.11
        cap = (cfg.insurable_cap or None) if cfg else None

        result = _calc.compute_payroll(
            _calc.PayrollInput(
                basic_salary=basic_salary,
                taxable_allowances=taxable_allowances,
                non_taxable_allowances=non_taxable_allowances,
                other_deductions=other_deductions,
                is_citizen=is_citizen,
            ),
            bands=bands,
            pension_employee_rate=ee_rate,
            pension_employer_rate=er_rate,
            pension_cap=cap,
        )
        return {
            "gross": result.gross,
            "taxable_income": result.taxable_income,
            "paye": result.paye,
            "pension_employee": result.pension_employee,
            "pension_employer": result.pension_employer,
            "net_pay": result.net_pay,
            "total_cost_to_employer": result.total_cost_to_employer,
        }
