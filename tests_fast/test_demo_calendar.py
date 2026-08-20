# -*- coding: utf-8 -*-
"""Goldens for the demo tenant's calendar. Shape, not particular dates.

The point of the module under test is that the dates MOVE, so a golden that
pinned one would assert the defect it was written to remove. What is fixed is
the shape: three consecutive whole trading months ending in the month before
the build, opening the day before the first of them.

Run: pytest tests_fast/
"""

import importlib.util
import os
import sys as _sys
from datetime import date, timedelta

_MOD = os.path.join(
    os.path.dirname(__file__),
    "..",
    "addons",
    "sapian_demo_trader",
    "reference",
    "demo_calendar.py",
)
_spec = importlib.util.spec_from_file_location("demo_calendar", _MOD)
cal = importlib.util.module_from_spec(_spec)
_sys.modules[_spec.name] = cal
_spec.loader.exec_module(cal)


def test_the_newest_month_is_the_one_that_has_finished():
    """The month the landing page reads, on any day of the build month."""
    for day in (1, 15, 31):
        built = date(2026, 8, day)
        assert cal.demo_calendar(built)["current"] == (date(2026, 7, 1), date(2026, 7, 31))


def test_three_consecutive_trading_months():
    windows = cal.demo_calendar(date(2026, 8, 20))
    assert windows["early"] == (date(2026, 5, 1), date(2026, 5, 31))
    assert windows["middle"] == (date(2026, 6, 1), date(2026, 6, 30))
    assert windows["current"] == (date(2026, 7, 1), date(2026, 7, 31))
    assert cal.TRADING_MONTHS == 3


def test_the_months_touch_with_no_gap_and_no_overlap():
    """Asserted rather than eyeballed: a gap month would leave the balance
    sheet's brought-forward figure with nothing to carry."""
    windows = cal.demo_calendar(date(2026, 8, 20))
    for earlier, later in (("early", "middle"), ("middle", "current")):
        assert windows[earlier][1] + timedelta(days=1) == windows[later][0]


def test_opening_is_the_day_before_trading_starts():
    """So the first month's cost of sales draws on goods already on hand."""
    windows = cal.demo_calendar(date(2026, 8, 20))
    assert windows["opening"] == date(2026, 4, 30)
    assert windows["opening"] + timedelta(days=1) == windows["early"][0]


def test_the_calendar_crosses_a_year_boundary():
    windows = cal.demo_calendar(date(2026, 2, 3))
    assert windows["current"] == (date(2026, 1, 1), date(2026, 1, 31))
    assert windows["middle"] == (date(2025, 12, 1), date(2025, 12, 31))
    assert windows["early"] == (date(2025, 11, 1), date(2025, 11, 30))
    assert windows["opening"] == date(2025, 10, 31)


def test_february_is_a_whole_month_too():
    windows = cal.demo_calendar(date(2024, 4, 10))
    assert windows["middle"] == (date(2024, 2, 1), date(2024, 2, 29))


def test_a_day_number_is_clamped_to_a_short_month():
    """A build in March must not crash on a demo date of the 30th.

    The day numbers are chosen for a 31-day month. Clamping moves them; raising
    would take the whole demo down every February.
    """
    february = cal.month_window(date(2026, 3, 5), 1)
    assert cal.day_in(february, 30) == date(2026, 2, 28)
    assert cal.day_in(february, 6) == date(2026, 2, 6)


def test_a_day_number_inside_the_month_is_left_alone():
    july = cal.month_window(date(2026, 8, 20), 1)
    assert cal.day_in(july, 31) == date(2026, 7, 31)
    assert cal.iso(cal.day_in(july, 6)) == "2026-07-06"


# ---------------------------------------------------------------------------
# THE PAYROLL CALENDAR, which is NOT the trading calendar
#
# The employment income tax period is an ETHIOPIAN month — VERIFIED,
# docs/ethiopian-tax-reference.md section 2 — and the reference records the
# payroll CYCLE itself as a business choice. This tenant runs the Ethiopian
# cycle, because that is the one whose mapping onto a filing month the
# reference settles. Trading, VAT and withholding stay on Gregorian months, so
# the two calendars overlap rather than nest.
#
# The goldens assert the SHAPE, as everywhere else in this file: four months,
# consecutive, ending with the last Ethiopian month to have finished, one of
# them ending inside each Gregorian trading month.
# ---------------------------------------------------------------------------


def _months(today):
    return cal.ethiopian_payroll_months(today)


def test_there_are_four_payroll_months_ending_with_the_finished_one():
    months = _months(date(2026, 8, 20))
    assert len(months) == cal.PAYROLL_MONTHS == 4
    # 20 Aug 2026 is Nehase 14, 2018; the last month to have FINISHED is Hamle.
    assert months[-1] == (date(2026, 7, 8), date(2026, 8, 6))


def test_the_payroll_months_are_consecutive_and_touch():
    months = _months(date(2026, 8, 20))
    for earlier, later in zip(months, months[1:]):
        assert later[0] == earlier[1] + timedelta(days=1), (earlier, later)


def test_the_newest_payroll_month_has_finished_on_any_build_day():
    """A run for the month still in progress would be half a month's payslips."""
    for day in (date(2026, 7, 8), date(2026, 7, 9), date(2026, 8, 6), date(2026, 8, 7)):
        assert _months(day)[-1][1] < day, day


def test_one_payroll_month_ends_inside_each_gregorian_trading_month():
    """Which is why there are four and not three.

    Each trading month's profit still carries a month's wages, and the fourth
    ends after all of them — in the month the landing page reads.
    """
    today = date(2026, 8, 20)
    windows = cal.demo_calendar(today)
    ends = [end for _start, end in _months(today)]
    for key in ("early", "middle", "current"):
        start, stop = windows[key]
        inside = [end for end in ends if start <= end <= stop]
        assert len(inside) == 1, (key, inside)
    assert ends[-1] > windows["current"][1]


def test_pagume_is_not_skipped():
    """Five days long, and staff are paid in it.

    The one month where "+30 days" and "the end of the following month" give
    different filing deadlines, so a demo that stepped over it would never show
    the difference.
    """
    months = _months(date(2026, 9, 20))
    assert (date(2026, 9, 6), date(2026, 9, 10)) in months


def test_the_payroll_months_move_with_the_build_and_never_repeat():
    a = _months(date(2026, 8, 20))
    b = _months(date(2026, 9, 20))
    assert a != b
    assert len({tuple(m) for m in a}) == len(a)
