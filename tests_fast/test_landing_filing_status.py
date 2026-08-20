# -*- coding: utf-8 -*-
"""Goldens for the landing page's deadline and filed/due/late logic.

Here rather than in `addons/sapian_landing/reference/` because CI runs
`pytest tests_fast/` and nothing else — see test_mail_debrand.py for why that
directory cannot be collected at all.

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
    "sapian_landing",
    "reference",
    "filing_status.py",
)
_spec = importlib.util.spec_from_file_location("filing_status", _MOD)
fs = importlib.util.module_from_spec(_spec)
_sys.modules[_spec.name] = fs
_spec.loader.exec_module(fs)

TODAY = date(2026, 8, 20)


# ---- the period a monthly filing is about ---------------------------------


def test_the_period_is_the_month_that_has_finished():
    """Never the running month.

    A monthly return is filed for a month that is over. Showing August on 20
    August would put a half-collected VAT figure under a deadline, which is a
    number that means nothing yet presented as one that is owed.
    """
    assert fs.previous_month(TODAY) == (date(2026, 7, 1), date(2026, 7, 31))


def test_the_period_crosses_a_year_boundary():
    assert fs.previous_month(date(2026, 1, 4)) == (date(2025, 12, 1), date(2025, 12, 31))


def test_february_in_a_leap_year():
    assert fs.previous_month(date(2024, 3, 1)) == (date(2024, 2, 1), date(2024, 2, 29))


# ---- deadlines -------------------------------------------------------------


def test_the_deadline_is_the_period_end_plus_the_configured_days():
    assert fs.deadline_for(date(2026, 7, 31), 30) == date(2026, 8, 30)


def test_no_rule_means_no_deadline_rather_than_a_guess():
    """The whole point of rule 2, applied to a date instead of an amount."""
    assert fs.deadline_for(date(2026, 7, 31), None) is None
    assert fs.deadline_for(None, 30) is None


def test_the_rule_in_force_is_the_latest_one_that_had_started():
    rules = [(date(2024, 1, 1), 30), (date(2026, 7, 1), 45)]
    assert fs.effective_rule(rules, date(2026, 6, 30)) == 30
    assert fs.effective_rule(rules, date(2026, 7, 1)) == 45


def test_a_period_before_every_rule_gets_none():
    """Not the earliest rule. A period assessed before any rule existed must
    not borrow one written later — that is how changing a future rate silently
    rewrites history, which CLAUDE.md forbids in those words."""
    rules = [(date(2024, 1, 1), 30)]
    assert fs.effective_rule(rules, date(2023, 12, 31)) is None


def test_a_rule_with_no_start_date_is_ignored():
    assert fs.effective_rule([(None, 30)], TODAY) is None


# ---- status ----------------------------------------------------------------


def test_due_before_the_deadline():
    assert fs.status_for(date(2026, 8, 30), None, today=TODAY) == fs.DUE


def test_late_after_the_deadline():
    assert fs.status_for(date(2026, 8, 19), None, today=TODAY) == fs.LATE


def test_the_deadline_day_itself_is_still_due():
    """Filing on the last day is filing on time."""
    assert fs.status_for(TODAY, None, today=TODAY) == fs.DUE


def test_filed_beats_a_passed_deadline():
    """A return submitted late is filed late, not outstanding.

    The page's job is to show what still needs doing.
    """
    assert fs.status_for(date(2026, 8, 1), date(2026, 8, 15), today=TODAY) == fs.FILED


def test_no_deadline_is_unknown_and_not_due():
    """Unknown is a fourth state on purpose.

    Defaulting an unknown deadline to "due" would invent an obligation, and to
    "filed" would hide one. Neither is a thing this product knows.
    """
    assert fs.status_for(None, None, today=TODAY) == fs.UNKNOWN


def test_days_remaining_is_signed_and_none_when_unknown():
    assert fs.days_remaining(date(2026, 8, 30), today=TODAY) == 10
    assert fs.days_remaining(date(2026, 8, 10), today=TODAY) == -10
    assert fs.days_remaining(None, today=TODAY) is None


# ---- whole-month check -----------------------------------------------------


def test_a_finished_calendar_month_is_complete():
    assert fs.is_complete_month(date(2026, 7, 1), date(2026, 7, 31), today=TODAY)


def test_the_running_month_is_not_complete():
    assert not fs.is_complete_month(date(2026, 8, 1), date(2026, 8, 31), today=TODAY)


def test_a_partial_window_is_not_a_month():
    assert not fs.is_complete_month(date(2026, 7, 2), date(2026, 7, 31), today=TODAY)
    assert not fs.is_complete_month(date(2026, 7, 1), date(2026, 7, 30), today=TODAY)


# ---------------------------------------------------------------------------
# PERIODS, IN WHICHEVER CALENDAR THE FILING IS COUNTED IN
#
# Added when the landing page stopped putting all four filings under one
# Gregorian month. `docs/ethiopian-tax-reference.md` section 2 is VERIFIED that
# the employment income tax period is an ETHIOPIAN month; the goldens below are
# the arithmetic that makes that true, and they are dated because Ethiopian
# month boundaries are the whole point.
# ---------------------------------------------------------------------------


def test_a_gregorian_period_is_still_a_gregorian_month():
    assert fs.previous_period(fs.GREGORIAN, TODAY) == (date(2026, 7, 1), date(2026, 7, 31))


def test_an_ethiopian_period_is_an_ethiopian_month_not_a_converted_one():
    """The defect, as arithmetic.

    On 20 August 2026 the last FINISHED Ethiopian month is Hamle 2018, which is
    8 July to 6 August. 1-31 July is not it: it begins 24 days into Sene and
    ends 24 days into Hamle, covering neither.
    """
    assert fs.previous_period(fs.ETHIOPIAN, TODAY) == (date(2026, 7, 8), date(2026, 8, 6))


def test_a_gregorian_month_is_not_a_whole_ethiopian_month():
    assert not fs.is_whole_period(fs.ETHIOPIAN, date(2026, 7, 1), date(2026, 7, 31))
    assert fs.is_whole_period(fs.GREGORIAN, date(2026, 7, 1), date(2026, 7, 31))
    assert fs.is_whole_period(fs.ETHIOPIAN, date(2026, 7, 8), date(2026, 8, 6))


def test_the_filing_window_is_the_following_month_not_thirty_days():
    """Sene's return is due at the end of Hamle — the accountant's own example.

    They agree here, because an Ethiopian month is 30 days. That agreement is
    what let a wrong rule look right for eleven months of the year.
    """
    sene_end = date(2026, 7, 7)
    assert fs.next_period_end(fs.ETHIOPIAN, sene_end) == date(2026, 8, 6)
    assert sene_end + timedelta(days=30) == date(2026, 8, 6)


def test_pagume_is_where_the_two_rules_disagree():
    """Nehase's return is due at the end of Pagume, which is 5 days long.

    This is the case that makes the shape worth recording: "+30 days" says
    5 October, twenty-five days after the return was actually due.
    """
    nehase_end = date(2026, 9, 5)
    assert fs.next_period_end(fs.ETHIOPIAN, nehase_end) == date(2026, 9, 10)
    assert nehase_end + timedelta(days=30) == date(2026, 10, 5)


def test_pagume_is_a_period_of_its_own_and_is_not_skipped():
    """Thirteen months, and staff are paid in the thirteenth too."""
    assert fs.period_containing(fs.ETHIOPIAN, date(2026, 9, 8)) == (
        date(2026, 9, 6),
        date(2026, 9, 10),
    )
    assert fs.next_period_end(fs.ETHIOPIAN, date(2026, 9, 10)) == date(2026, 10, 10)


def test_the_deadline_shape_is_read_from_the_rule_not_assumed():
    sene_end = date(2026, 7, 7)
    assert fs.deadline_for(sene_end, None, fs.WINDOW_END_OF_NEXT_PERIOD, fs.ETHIOPIAN) == date(
        2026, 8, 6
    )
    assert fs.deadline_for(sene_end, 45, fs.WINDOW_DAYS) == date(2026, 8, 21)


def test_an_unknown_calendar_raises_rather_than_defaulting():
    """Defaulting to Gregorian is how the original defect got in."""
    try:
        fs.previous_period("julian", TODAY)
    except ValueError as exc:
        assert "julian" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("an unknown calendar was silently accepted")


def test_the_old_rule_was_late_on_every_day_of_three_years():
    """The size of the defect, swept rather than sampled.

    Old behaviour: the previous GREGORIAN month, due 30 days after it ends.
    Real rule for the filing that period BEGINS in: the end of the following
    Ethiopian month. The old answer is never early, and it is 24 days late on
    20 August 2026 — the day this was found.
    """
    deltas = []
    day = date(2026, 1, 1)
    while day < date(2029, 1, 1):
        _start, end = fs.previous_period(fs.GREGORIAN, day)
        begins_in = fs.period_containing(fs.ETHIOPIAN, fs.previous_period(fs.GREGORIAN, day)[0])
        real = fs.next_period_end(fs.ETHIOPIAN, begins_in[1])
        deltas.append(((end + timedelta(days=30)) - real).days)
        day += timedelta(days=1)
    assert min(deltas) > 0, "the old rule was early on some day; it was not"
    assert (min(deltas), max(deltas)) == (20, 50)
    _start, end = fs.previous_period(fs.GREGORIAN, TODAY)
    begins_in = fs.period_containing(fs.ETHIOPIAN, fs.previous_period(fs.GREGORIAN, TODAY)[0])
    assert (
        (end + timedelta(days=30)) - fs.next_period_end(fs.ETHIOPIAN, begins_in[1])
    ).days == 24
