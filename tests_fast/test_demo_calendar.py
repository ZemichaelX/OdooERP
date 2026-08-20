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
