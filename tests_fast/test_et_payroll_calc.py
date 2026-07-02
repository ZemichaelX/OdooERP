# -*- coding: utf-8 -*-
"""Fast golden-value tests for the Ethiopian payroll calculator (no Odoo needed).

Loads the pure-Python calculator by file path so it works standalone. Every expected
number is hand-computed from the 2024/25 monthly PAYE bands (tax-free <= 2,000;
15/20/25/30/35% with deductions 300/500/850/1350/2050) and the 7%/11% pension split.
Run: pytest tests_fast/
"""
import importlib.util
import os

import pytest

_CALC = os.path.join(
    os.path.dirname(__file__), "..", "addons", "l10n_et_payroll", "reference", "et_payroll_calc.py"
)
_spec = importlib.util.spec_from_file_location("et_payroll_calc", _CALC)
calc = importlib.util.module_from_spec(_spec)
import sys as _sys
_sys.modules[_spec.name] = calc
_spec.loader.exec_module(calc)


@pytest.mark.parametrize("income,expected", [
    (0, 0.0), (2000, 0.0), (2000.01, 0.0015), (3000, 150.0), (4000, 300.0),
    (5000, 500.0), (7000, 900.0), (8500, 1275.0), (10000, 1650.0), (12000, 2250.0),
    (14000, 2850.0), (20000, 4950.0), (50000, 15450.0),
])
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
    assert (r.gross, r.paye, r.pension_employee, r.pension_employer) == (10000.0, 1650.0, 700.0, 1100.0)
    assert r.net_pay == 7650.0 and r.total_cost_to_employer == 11100.0


def test_payroll_5000():
    r = calc.compute_payroll(calc.PayrollInput(basic_salary=5000))
    assert (r.paye, r.pension_employee, r.net_pay) == (500.0, 350.0, 4150.0)


def test_payroll_2000_taxfree():
    r = calc.compute_payroll(calc.PayrollInput(basic_salary=2000))
    assert (r.paye, r.pension_employee, r.net_pay) == (0.0, 140.0, 1860.0)


def test_payroll_with_allowances():
    r = calc.compute_payroll(calc.PayrollInput(
        basic_salary=8000, taxable_allowances=1000, non_taxable_allowances=500))
    assert r.taxable_income == 9000.0
    assert r.paye == pytest.approx(1400.0, abs=0.01)
    assert r.pension_employee == 560.0
    assert r.gross == 9500.0
    assert r.net_pay == pytest.approx(7540.0, abs=0.01)


def test_payroll_non_citizen_no_pension():
    r = calc.compute_payroll(calc.PayrollInput(basic_salary=10000, is_citizen=False))
    assert r.pension_employee == 0.0 and r.net_pay == 8350.0
