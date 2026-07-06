# -*- coding: utf-8 -*-
"""Fast golden-value tests for the Ethiopian payroll calculator (no Odoo needed).

Loads the pure-Python calculator by file path so it works standalone. Every expected
number is hand-computed from the 2024/25 monthly PAYE bands (tax-free <= 2,000;
15/20/25/30/35% with deductions 300/500/850/1350/2050) and the 7%/11% pension split.
Run: pytest tests_fast/
"""

import importlib.util
import os
import sys as _sys

import pytest

_CALC = os.path.join(
    os.path.dirname(__file__),
    "..",
    "addons",
    "l10n_et_payroll",
    "reference",
    "et_payroll_calc.py",
)
_spec = importlib.util.spec_from_file_location("et_payroll_calc", _CALC)
calc = importlib.util.module_from_spec(_spec)
_sys.modules[_spec.name] = calc
_spec.loader.exec_module(calc)


@pytest.mark.parametrize(
    "income,expected",
    [
        (0, 0.0),
        (2000, 0.0),
        (2000.01, 0.0015),
        (3000, 150.0),
        (4000, 300.0),
        (5000, 500.0),
        (7000, 900.0),
        (8500, 1275.0),
        (10000, 1650.0),
        (12000, 2250.0),
        (14000, 2850.0),
        (20000, 4950.0),
        (50000, 15450.0),
    ],
)
def test_paye_bands(income, expected):
    assert calc.compute_paye(income) == pytest.approx(expected, abs=0.01)


def test_paye_continuity_at_boundaries():
    for b in [2000, 4000, 7000, 10000, 14000]:
        lo, hi = calc.compute_paye(b), calc.compute_paye(b + 0.01)
        assert hi >= lo and (hi - lo) < 0.02


def test_pension_basic():
    assert calc.compute_pension(10000, is_citizen=True) == (700.0, 1100.0)


def test_pension_non_citizen_is_zero():
    assert calc.compute_pension(10000, is_citizen=False) == (0.0, 0.0)


def test_pension_cap_applies():
    assert calc.compute_pension(20000, is_citizen=True, cap=15000) == (1050.0, 1650.0)


def test_payroll_10000():
    r = calc.compute_payroll(calc.PayrollInput(basic_salary=10000))
    assert (r.gross, r.paye, r.pension_employee, r.pension_employer) == (
        10000.0,
        1650.0,
        700.0,
        1100.0,
    )
    assert r.net_pay == 7650.0 and r.total_cost_to_employer == 11100.0


def test_payroll_5000():
    r = calc.compute_payroll(calc.PayrollInput(basic_salary=5000))
    assert (r.paye, r.pension_employee, r.net_pay) == (500.0, 350.0, 4150.0)


def test_payroll_2000_taxfree():
    r = calc.compute_payroll(calc.PayrollInput(basic_salary=2000))
    assert (r.paye, r.pension_employee, r.net_pay) == (0.0, 140.0, 1860.0)


def test_payroll_with_allowances():
    r = calc.compute_payroll(
        calc.PayrollInput(
            basic_salary=8000, taxable_allowances=1000, non_taxable_allowances=500
        )
    )
    assert r.taxable_income == 9000.0
    assert r.paye == pytest.approx(1400.0, abs=0.01)
    assert r.pension_employee == 560.0
    assert r.gross == 9500.0
    assert r.net_pay == pytest.approx(7540.0, abs=0.01)


def test_payroll_non_citizen_no_pension():
    r = calc.compute_payroll(calc.PayrollInput(basic_salary=10000, is_citizen=False))
    assert r.pension_employee == 0.0 and r.net_pay == 8350.0


# --------------------------------------------------------------------------------------
# Allowance exemption split (accountant-verified Jul 2026)
# --------------------------------------------------------------------------------------
def test_transport_allowance_golden_10000_salary_3000_transport():
    """Kickoff golden: salary 10,000 + transport 3,000 → exempt 2,200 (the
    2,200 ceiling is lower than 25% = 2,500), taxable 800 — PAYE on 10,800."""
    exempt, taxable = calc.split_allowance(
        3000,
        10000,
        cap_amount=calc.DEFAULT_TRANSPORT_EXEMPT_CAP,
        cap_salary_pct=calc.DEFAULT_TRANSPORT_EXEMPT_SALARY_PCT,
    )
    assert (exempt, taxable) == (2200.0, 800.0)
    r = calc.compute_payroll(
        calc.PayrollInput(
            basic_salary=10000, taxable_allowances=taxable, non_taxable_allowances=exempt
        )
    )
    assert r.taxable_income == 10800.0
    assert r.paye == pytest.approx(1890.0, abs=0.01)  # 30% × 10,800 − 1,350


def test_transport_allowance_salary_pct_binds_on_low_salary():
    """Salary 8,000 → 25% = 2,000 is LOWER than 2,200: transport 3,000 →
    exempt 2,000, taxable 1,000."""
    exempt, taxable = calc.split_allowance(3000, 8000, cap_amount=2200, cap_salary_pct=0.25)
    assert (exempt, taxable) == (2000.0, 1000.0)


def test_transport_allowance_under_both_ceilings_fully_exempt():
    exempt, taxable = calc.split_allowance(1500, 10000, cap_amount=2200, cap_salary_pct=0.25)
    assert (exempt, taxable) == (1500.0, 0.0)


def test_allowance_no_ceiling_fully_exempt():
    """Hardship/medical rule: no configured ceiling → fully exempt."""
    exempt, taxable = calc.split_allowance(5000, 10000)
    assert (exempt, taxable) == (5000.0, 0.0)


def test_allowance_zero_or_negative_amount_is_noop():
    assert calc.split_allowance(0, 10000, cap_amount=2200) == (0.0, 0.0)
    assert calc.split_allowance(-100, 10000, cap_amount=2200) == (0.0, 0.0)


def test_allowance_zero_salary_pct_ceiling_all_taxable():
    """Percentage ceiling with zero salary: nothing can be exempted via the
    salary fraction."""
    exempt, taxable = calc.split_allowance(1000, 0, cap_amount=2200, cap_salary_pct=0.25)
    assert (exempt, taxable) == (0.0, 1000.0)


# --------------------------------------------------------------------------------------
# Adversarial-review regressions (Jul 2026)
# --------------------------------------------------------------------------------------
def test_split_allowance_no_invented_cent_on_half_cent_ceiling():
    """R1#5: exempt + taxable must sum back to the amount even when 25% of
    salary lands on a half-cent (25% of 8,000.02 = 2,000.005)."""
    exempt, taxable = calc.split_allowance(3000, 8000.02, cap_amount=2200, cap_salary_pct=0.25)
    assert round(exempt + taxable, 2) == 3000.00


def test_round2_half_up_at_magnitude_and_sign():
    """R1#6: Decimal half-up survives large magnitudes and negatives (the old
    +1e-9 nudge silently reverted to banker's/​wrong-way rounding)."""
    assert calc._round2(700000000.005) == 700000000.01
    assert calc._round2(-1.005) == -1.01
    assert calc._round2(2.675) == 2.68
