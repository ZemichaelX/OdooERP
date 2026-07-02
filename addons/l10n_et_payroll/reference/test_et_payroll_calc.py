# -*- coding: utf-8 -*-
"""Golden-value tests for the Ethiopian payroll calculator.

Every expected number here is hand-computed from the 2024/25 monthly PAYE bands
(tax-free <= 2,000; 15/20/25/30/35% with deductions 300/500/850/1350/2050) and the
7%/11% pension split. If a band changes, update both the config data AND these goldens.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import pytest
from et_payroll_calc import (
    compute_paye,
    compute_pension,
    compute_payroll,
    PayrollInput,
)


# ---- PAYE band boundaries and interior points ----
@pytest.mark.parametrize(
    "income,expected",
    [
        (0, 0.0),
        (2000, 0.0),  # top of tax-free band
        (2000.01, 0.0015),  # just into 15% band: 0.15*2000.01-300 = 0.0015
        (3000, 150.0),  # 0.15*3000-300
        (4000, 300.0),  # boundary 15%: 0.15*4000-300 ; also 0.20*4000-500
        (5000, 500.0),  # 0.20*5000-500
        (7000, 900.0),  # boundary: 0.20*7000-500 = 0.25*7000-850
        (8500, 1275.0),  # 0.25*8500-850
        (10000, 1650.0),  # boundary: 0.25*10000-850 = 0.30*10000-1350
        (12000, 2250.0),  # 0.30*12000-1350
        (14000, 2850.0),  # boundary: 0.30*14000-1350 = 0.35*14000-2050
        (20000, 4950.0),  # 0.35*20000-2050
        (50000, 15450.0),  # 0.35*50000-2050
    ],
)
def test_paye_bands(income, expected):
    assert compute_paye(income) == pytest.approx(expected, abs=0.01)


def test_paye_continuity_at_boundaries():
    """PAYE must be continuous across every band boundary."""
    for b in [2000, 4000, 7000, 10000, 14000]:
        lo = compute_paye(b)
        hi = compute_paye(b + 0.01)
        assert hi >= lo
        assert hi - lo < 0.02  # only the marginal cent differs


# ---- Pension ----
def test_pension_basic():
    ee, er = compute_pension(10000, is_citizen=True)
    assert ee == 700.0  # 7%
    assert er == 1100.0  # 11%


def test_pension_non_citizen_is_zero():
    ee, er = compute_pension(10000, is_citizen=False)
    assert (ee, er) == (0.0, 0.0)


def test_pension_cap_applies():
    ee, er = compute_pension(20000, is_citizen=True, cap=15000)
    assert ee == 1050.0  # 7% of capped 15000
    assert er == 1650.0  # 11% of capped 15000


# ---- Full payroll golden cases (hand-computed) ----
def test_payroll_10000():
    r = compute_payroll(PayrollInput(basic_salary=10000))
    assert r.gross == 10000.0
    assert r.paye == 1650.0
    assert r.pension_employee == 700.0
    assert r.pension_employer == 1100.0
    assert r.net_pay == 7650.0  # 10000 - 1650 - 700
    assert r.total_cost_to_employer == 11100.0  # 10000 + 1100


def test_payroll_5000():
    r = compute_payroll(PayrollInput(basic_salary=5000))
    assert r.paye == 500.0
    assert r.pension_employee == 350.0
    assert r.net_pay == 4150.0  # 5000 - 500 - 350


def test_payroll_2000_taxfree():
    r = compute_payroll(PayrollInput(basic_salary=2000))
    assert r.paye == 0.0
    assert r.pension_employee == 140.0
    assert r.net_pay == 1860.0  # 2000 - 0 - 140


def test_payroll_with_allowances():
    # basic 8000 + taxable allowance 1000 (PAYE base 9000) + non-taxable transport 500
    r = compute_payroll(
        PayrollInput(
            basic_salary=8000,
            taxable_allowances=1000,
            non_taxable_allowances=500,
        )
    )
    assert r.taxable_income == 9000.0
    assert r.paye == pytest.approx(0.25 * 9000 - 850, abs=0.01)  # 1400
    assert r.pension_employee == 560.0  # 7% of basic 8000 only
    assert r.gross == 9500.0
    # net = 9500 - 1400 - 560 - 0
    assert r.net_pay == pytest.approx(7540.0, abs=0.01)


def test_payroll_non_citizen_no_pension():
    r = compute_payroll(PayrollInput(basic_salary=10000, is_citizen=False))
    assert r.pension_employee == 0.0
    assert r.net_pay == 8350.0  # 10000 - 1650 - 0
