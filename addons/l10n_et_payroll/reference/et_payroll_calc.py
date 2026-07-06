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
from decimal import ROUND_HALF_UP, Decimal
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

# Transport allowance exemption ceiling — accountant-verified Jul 2026:
# exempt up to the LOWER of ETB 2,200/month or 25% of basic salary; the excess
# is taxable. These are the seeded defaults for the 'transport' allowance type;
# the Odoo layer passes the effective configuration in.
DEFAULT_TRANSPORT_EXEMPT_CAP = 2200.0
DEFAULT_TRANSPORT_EXEMPT_SALARY_PCT = 0.25


def _round2(value: float) -> float:
    """Round half-up to 2 decimals (cents) in exact decimal arithmetic.

    Mirrors the l10n_et_base tax calculator: ``Decimal(repr(value))`` sees the
    float's shortest decimal form so accumulated float dust rounds away, and
    half-up survives at any magnitude and sign (the old ``round(value + 1e-9,
    2)`` nudge is lost to float ULP above ~ETB 600M and points the wrong way
    for negatives)."""
    return float(Decimal(repr(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


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


def split_allowance(
    amount: float,
    basic_salary: float,
    cap_amount: float | None = None,
    cap_salary_pct: float | None = None,
) -> Tuple[float, float]:
    """Split one allowance into ``(exempt, taxable)`` under an exemption ceiling.

    The exempt portion is the allowance up to the LOWEST of the configured
    ceilings — an absolute monthly amount (``cap_amount``) and/or a fraction of
    basic salary (``cap_salary_pct``); whatever exceeds the ceiling is taxable.
    With no ceiling configured the allowance is fully exempt (that is the
    'hardship'/'medical' rule); a fully-taxable allowance simply never calls
    this function.

    Golden (transport, accountant-verified Jul 2026): salary 10,000 + transport
    3,000 with caps (2,200, 25%) → exempt 2,200, taxable 800.
    """
    if amount <= 0:
        return 0.0, 0.0
    ceilings = []
    if cap_amount is not None:
        ceilings.append(max(cap_amount, 0.0))
    if cap_salary_pct is not None:
        ceilings.append(max(basic_salary, 0.0) * cap_salary_pct)
    # Round the exempt part first, then take the remainder, so the two halves
    # always sum back to ``amount`` (rounding both independently can invent a
    # cent when a ceiling lands on a half-cent, e.g. 25% of 8,000.02).
    exempt = _round2(min([amount, *ceilings]))
    return exempt, _round2(amount - exempt)


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
