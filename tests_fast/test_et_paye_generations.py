# -*- coding: utf-8 -*-
"""PAYE band GENERATIONS: the right schedule for the payslip's date.

The bands we ship (0/15/20/25/30/35%, exempt to 2,000, top above 14,000) are
those of Income Tax (Amendment) Proclamation 1395/2025, in force from
8 July 2025. They were seeded as effective 1 July 2024 — twelve months before
the proclamation existed — so every payslip dated 1 Jul 2024 → 7 Jul 2025
computed PAYE on bands more generous than the law of the day, understating the
tax. Understated PAYE is the employer's liability at assessment.

The regime in force before that boundary is Proclamation 979/2016. Its absence
is the second half of the defect: a table that cannot answer "what was the tax
in May 2025?" is not effective-dated, it is one rate set with a date column.

These goldens are hand-checked against both published schedules.
"""

import importlib.util
import os
import sys as _sys
from datetime import date

import pytest

# Same standalone loader the other fast tests use: no Odoo, no package imports.
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


class TestBandSelectionByDate:
    """Which generation applies on a given date — the boundary is 8 Jul 2025."""

    def test_june_2025_uses_979_2016_bands(self):
        assert calc.get_paye_bands(date(2025, 6, 30)) == calc.PAYE_BANDS_979_2016

    def test_august_2025_uses_1395_2025_bands(self):
        assert calc.get_paye_bands(date(2025, 8, 1)) == calc.PAYE_BANDS_1395_2025

    def test_commencement_day_is_inclusive(self):
        """8 July 2025 is the first day of the new regime, not the last of the old."""
        assert calc.get_paye_bands(date(2025, 7, 8)) == calc.PAYE_BANDS_1395_2025

    def test_day_before_commencement_is_the_old_regime(self):
        """The exclusive side: 7 July 2025 is still 979/2016, and a salary that
        straddles a band boundary is taxed differently one day apart."""
        assert calc.get_paye_bands(date(2025, 7, 7)) == calc.PAYE_BANDS_979_2016
        seventh = calc.compute_paye(6000.0, bands=calc.get_paye_bands(date(2025, 7, 7)))
        eighth = calc.compute_paye(6000.0, bands=calc.get_paye_bands(date(2025, 7, 8)))
        assert seventh == pytest.approx(935.0, abs=0.01)
        assert eighth == pytest.approx(700.0, abs=0.01)

    def test_default_bands_are_the_current_generation(self):
        """DEFAULT_PAYE_BANDS keeps meaning "the bands in force now"."""
        assert calc.DEFAULT_PAYE_BANDS == calc.PAYE_BANDS_1395_2025


class TestWorkedExamplesBothRegimes:
    """One salary, two regimes, different band and different tax.

    Gross 6,000, no allowances, so taxable = 6,000 (pension is not deductible
    from the PAYE base in this engine — see compute_payroll).

    * 979/2016:  6,000 falls in 5,251–7,800 → 25%, deduction 565
                 → 0.25 * 6,000 − 565 = 1,500 − 565 = 935
    * 1395/2025: 6,000 falls in 4,001–7,000 → 20%, deduction 500
                 → 0.20 * 6,000 − 500 = 1,200 − 500 = 700
    The 2025 bands are the more generous pair: 235 less tax on the same salary,
    which is exactly why back-dating them understated PAYE.
    """

    def test_6000_under_979_2016(self):
        tax = calc.compute_paye(6000.0, bands=calc.PAYE_BANDS_979_2016)
        assert tax == pytest.approx(935.0, abs=0.01)

    def test_6000_under_1395_2025(self):
        tax = calc.compute_paye(6000.0, bands=calc.PAYE_BANDS_1395_2025)
        assert tax == pytest.approx(700.0, abs=0.01)

    def test_same_salary_by_date(self):
        """The date alone decides, through get_paye_bands."""
        june = calc.compute_paye(6000.0, bands=calc.get_paye_bands(date(2025, 6, 30)))
        august = calc.compute_paye(6000.0, bands=calc.get_paye_bands(date(2025, 8, 1)))
        assert june == pytest.approx(935.0, abs=0.01)
        assert august == pytest.approx(700.0, abs=0.01)
        assert june - august == pytest.approx(235.0, abs=0.01)

    @pytest.mark.parametrize(
        "income,expected",
        [
            (600.0, 0.0),  # exempt ceiling under 979/2016
            (1000.0, 40.0),  # 0.10 * 1,000 − 60
            (2000.0, 157.5),  # 0.15 * 2,000 − 142.50
            (5000.0, 697.5),  # 0.20 * 5,000 − 302.50
            (10900.0, 2315.0),  # 0.30 * 10,900 − 955, top of the 6th band
            (12000.0, 2700.0),  # 0.35 * 12,000 − 1,500, top band
        ],
    )
    def test_979_2016_schedule_points(self, income, expected):
        assert calc.compute_paye(income, bands=calc.PAYE_BANDS_979_2016) == pytest.approx(
            expected, abs=0.01
        )

    def test_979_2016_bands_are_continuous(self):
        """No gap or jump at a boundary — the quick-formula deductions line up."""
        for lower, _upper, _rate, _deduction in calc.PAYE_BANDS_979_2016[1:]:
            below = calc.compute_paye(lower, bands=calc.PAYE_BANDS_979_2016)
            above = calc.compute_paye(lower + 0.01, bands=calc.PAYE_BANDS_979_2016)
            assert above >= below
            assert above - below < 0.02


class TestGenerationMetadata:
    """Each generation carries its commencement date and its citation."""

    def test_generations_are_ordered_and_cited(self):
        dates = [gen.effective_from for gen in calc.PAYE_BAND_GENERATIONS]
        assert dates == sorted(dates)
        assert all(gen.citation for gen in calc.PAYE_BAND_GENERATIONS)

    def test_1395_2025_commences_8_july_2025(self):
        current = calc.PAYE_BAND_GENERATIONS[-1]
        assert current.effective_from == date(2025, 7, 8)
        assert current.bands == calc.PAYE_BANDS_1395_2025
