# -*- coding: utf-8 -*-
"""Pure-Python Ethiopian payroll calculator (no Odoo dependency).

This is the single source of truth for Ethiopian PAYE (employment income tax) and pension
math. The Odoo model `l10n.et.payslip.compute` calls these functions so the logic can be
unit-tested fast (pytest) without a running Odoo instance.

IMPORTANT — these are CONFIGURATION VALUES, not universal constants. They reflect Ethiopia's
2024/25 personal income tax reform (monthly PAYE) and the standard private/public pension
split. Re-verify against the Ministry of Revenue before any payroll go-live. In the Odoo
build, the bands live in effective-dated data records so historical payslips never change
when a future rate is amended.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

# Monthly PAYE bands, 2024/25 reform.
# Each tuple: (lower_bound_exclusive, upper_bound_inclusive, rate, deduction)
# PAYE = rate * taxable_income - deduction  (progressive "quick" formula).
# upper_bound None means "and above".
DEFAULT_PAYE_BANDS: List[Tuple[float, float, float, float]] = [
    (0.0, 2000.0, 0.00, 0.0),
    (2000.0, 4000.0, 0.15, 300.0),
    (4000.0, 7000.0, 0.20, 500.0),
    (7000.0, 10000.0, 0.25, 850.0),
    (10000.0, 14000.0, 0.30, 1350.0),
    (14000.0, None, 0.35, 2050.0),
]

DEFAULT_PENSION_EMPLOYEE_RATE = 0.07  # 7% employee
DEFAULT_PENSION_EMPLOYER_RATE = 0.11  # 11% employer
DEFAULT_PENSION_CAP = None  # optional monthly insurable-earning cap (ETB); None = uncapped


def _round2(value: float) -> float:
    """Round to 2 decimals (cents) using standard rounding."""
    return round(value + 1e-9, 2)


def compute_paye(taxable_income: float, bands=DEFAULT_PAYE_BANDS) -> float:
    """Return monthly PAYE for a given taxable income using the progressive band formula."""
    if taxable_income <= 0:
        return 0.0
    for lower, upper, rate, deduction in bands:
        in_band = taxable_income > lower and (upper is None or taxable_income <= upper)
        if in_band:
            return _round2(rate * taxable_income - deduction)
    return 0.0


def compute_pension(
    basic_salary: float,
    is_citizen: bool = True,
    employee_rate: float = DEFAULT_PENSION_EMPLOYEE_RATE,
    employer_rate: float = DEFAULT_PENSION_EMPLOYER_RATE,
    cap: float | None = DEFAULT_PENSION_CAP,
) -> Tuple[float, float]:
    """Return (employee_pension, employer_pension).

    Pension applies to Ethiopian citizens only (per the reference config). An optional
    monthly insurable-earnings `cap` limits the base if provided.
    """
    if not is_citizen or basic_salary <= 0:
        return 0.0, 0.0
    base = basic_salary if cap is None else min(basic_salary, cap)
    return _round2(base * employee_rate), _round2(base * employer_rate)


@dataclass
class PayrollInput:
    basic_salary: float
    taxable_allowances: float = 0.0  # allowances subject to PAYE
    non_taxable_allowances: float = 0.0  # exempt allowances (e.g. transport within limit)
    other_deductions: float = 0.0  # loans, etc. (post-tax)
    is_citizen: bool = True


@dataclass
class PayrollResult:
    gross: float
    taxable_income: float
    paye: float
    pension_employee: float
    pension_employer: float
    net_pay: float
    total_cost_to_employer: float
    breakdown: dict = field(default_factory=dict)


def compute_payroll(
    inp: PayrollInput,
    bands=DEFAULT_PAYE_BANDS,
    pension_employee_rate: float = DEFAULT_PENSION_EMPLOYEE_RATE,
    pension_employer_rate: float = DEFAULT_PENSION_EMPLOYER_RATE,
    pension_cap: float | None = DEFAULT_PENSION_CAP,
) -> PayrollResult:
    """Compute a full monthly payroll result for one employee.

    Net = gross - PAYE - employee pension - other deductions.
    PAYE base = basic + taxable allowances (exempt allowances excluded).
    """
    gross = _round2(inp.basic_salary + inp.taxable_allowances + inp.non_taxable_allowances)
    taxable_income = _round2(inp.basic_salary + inp.taxable_allowances)
    paye = compute_paye(taxable_income, bands=bands)
    pension_ee, pension_er = compute_pension(
        inp.basic_salary,
        is_citizen=inp.is_citizen,
        employee_rate=pension_employee_rate,
        employer_rate=pension_employer_rate,
        cap=pension_cap,
    )
    net = _round2(gross - paye - pension_ee - inp.other_deductions)
    cost = _round2(gross + pension_er)
    return PayrollResult(
        gross=gross,
        taxable_income=taxable_income,
        paye=paye,
        pension_employee=pension_ee,
        pension_employer=pension_er,
        net_pay=net,
        total_cost_to_employer=cost,
        breakdown={
            "basic_salary": inp.basic_salary,
            "taxable_allowances": inp.taxable_allowances,
            "non_taxable_allowances": inp.non_taxable_allowances,
            "other_deductions": inp.other_deductions,
        },
    )
