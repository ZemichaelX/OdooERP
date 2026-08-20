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
from datetime import date

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
