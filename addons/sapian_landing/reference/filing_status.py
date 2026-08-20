# -*- coding: utf-8 -*-
"""When a filing is due, and whether it is filed, due or late.

PLAIN PYTHON (CLAUDE.md rule 10). Dates and comparisons, no ORM, so the goldens
run in milliseconds and the Odoo model calls this rather than restating it.

WHAT THIS IS NOT
----------------
It is not a source of AMOUNTS. Every figure on the landing page comes from the
report that owns it; this file only answers "by when" and "has it gone in yet",
which no report in this product tracks.

THE DEADLINE RULE IS CONFIGURATION, NOT A CONSTANT HERE
--------------------------------------------------------
`days_after_period_end` is passed in, read from `sapian.filing.deadline` records
that carry an `effective_from` date — CLAUDE.md rule 4, the same discipline as
PAYE bands and WHT rates. Changing a future deadline must never move a period
that has already been assessed against the old one, and a rule with an
effective date is the only shape that holds.

AND IT IS UNVERIFIED. The 30-day figure in the seed data is the practice this
project has recorded (CLAUDE.md: pension "within 30 days"), applied to the other
three by analogy. It has NOT been checked against a current Ministry of Revenues
schedule. That is why it is a dated config row an accountant can correct without
a code change, and why the landing page labels the deadline as such.
"""

import importlib.util
import os
import sys as _sys
from datetime import date, timedelta

# THE ETHIOPIAN CALENDAR, reachable from BOTH sides.
#
# `sapian_landing` declares `l10n_et_calendar` as a hard dependency, so inside
# Odoo the package import is the right one. But this file is also loaded BY PATH
# from `tests_fast/`, where `odoo.addons` does not exist and no package context
# is set up — see the header of tests_fast/test_landing_filing_status.py. A
# plain package import would make every golden here uncollectable, and a guard
# that silently returned None on the fallback would make them pass by not
# running. So: try the real import, and fall back to loading the sibling module
# off disk, which is where a hard dependency always is.
try:  # pragma: no cover - exercised on whichever side is running
    from odoo.addons.l10n_et_calendar.reference import et_calendar
except ImportError:  # pragma: no cover
    _ET = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "l10n_et_calendar",
        "reference",
        "et_calendar.py",
    )
    _NAME = "sapian_landing._et_calendar_offdisk"
    _spec = importlib.util.spec_from_file_location(_NAME, _ET)
    et_calendar = importlib.util.module_from_spec(_spec)
    # REGISTERED BEFORE EXEC, and not for tidiness: `et_calendar` defines a
    # frozen `@dataclass`, and dataclasses resolves its field types through
    # `sys.modules[cls.__module__]`. Load it without registering and the
    # decorator dies on `NoneType has no attribute __dict__` — the module
    # imports fine everywhere else and is unloadable only here.
    _sys.modules[_NAME] = et_calendar
    _spec.loader.exec_module(et_calendar)

#: The four statutory filings this product can put a number against.
FILING_KEYS = ("vat", "wht", "paye", "pension")

#: The calendars a filing period can be counted in. WHICH ONE APPLIES TO WHICH
#: FILING IS DATA, not a constant here — `sapian.filing.period` carries it with
#: an effective date, the same discipline as the deadline rules below.
GREGORIAN = "gregorian"
ETHIOPIAN = "ethiopian"
CALENDARS = (GREGORIAN, ETHIOPIAN)

#: A filing whose deadline cannot be established at all.
UNKNOWN = "unknown"
#: Recorded as submitted.
FILED = "filed"
#: Not submitted, deadline still ahead.
DUE = "due"
#: Not submitted, deadline passed.
LATE = "late"


#: The deadline is a fixed number of days after the period ends.
WINDOW_DAYS = "days"
#: The deadline is the last day of the period FOLLOWING the one being filed.
WINDOW_END_OF_NEXT_PERIOD = "end_of_next_period"
WINDOWS = (WINDOW_DAYS, WINDOW_END_OF_NEXT_PERIOD)


def deadline_for(period_end, days_after_period_end, window=WINDOW_DAYS, calendar=GREGORIAN):
    """The date a period's filing is due, or ``None`` when no rule applies.

    ``None`` and not a guess: a period with no effective rule has an UNKNOWN
    status on the page, which is the honest answer and the one the operator can
    act on. Inventing "probably the 30th" would be a placeholder wearing a date.

    TWO SHAPES, because the two filings this product can cite a source for have
    two different shapes. Pension is *"within 30 days"* — a day count. Employment
    income tax is *"during the following Ethiopian month"* — a period. Expressing
    the second as "+30 days" is right eleven times a year and wrong at Pagume,
    which is 5 or 6 days long; a rule that is right by coincidence is not a rule.
    """
    if not period_end:
        return None
    if window == WINDOW_END_OF_NEXT_PERIOD:
        return next_period_end(calendar, period_end)
    if days_after_period_end is None:
        return None
    return period_end + timedelta(days=int(days_after_period_end))


def status_for(deadline, filed_on, today=None):
    """``filed`` / ``due`` / ``late`` / ``unknown`` for one filing.

    ``filed`` wins over a passed deadline on purpose: a return submitted after
    its deadline is filed late, and the page's job is to show what still needs
    doing. A late-but-filed return is not outstanding work.
    """
    if filed_on:
        return FILED
    if deadline is None:
        return UNKNOWN
    today = today or date.today()
    return LATE if today > deadline else DUE


def days_remaining(deadline, today=None):
    """Signed days to the deadline: positive ahead, negative past, None unknown."""
    if deadline is None:
        return None
    return (deadline - (today or date.today())).days


def previous_month(today):
    """The Gregorian month before ``today``, as (first_day, last_day).

    Kept as its own name because the BUSINESS half of the landing page — sales,
    cash, profit — is a Gregorian month and is not a filing at all. The
    compliance half goes through `previous_period` instead, which asks the
    configured calendar.
    """
    first_of_this = today.replace(day=1)
    last_of_prev = first_of_this - timedelta(days=1)
    return last_of_prev.replace(day=1), last_of_prev


# ---- periods, in whichever calendar the filing is counted in ---------------
#
# A monthly return is filed for a period that has FINISHED. The current period
# is never the one shown: putting a half-collected figure under a deadline is
# how a landing page invites somebody to file early and short.


def _ethiopian_month_bounds(year, month):
    """First and last Gregorian day of one Ethiopian month.

    Pagume is month 13 and is 5 or 6 days long, not 30. `days_in_month` knows;
    nothing here may assume 30, and the Pagume case is exactly where a
    "+30 days" deadline and "the end of the following month" stop agreeing.
    """
    last_day = et_calendar.days_in_month(year, month)
    return (
        et_calendar.ethiopian_to_gregorian(year, month, 1),
        et_calendar.ethiopian_to_gregorian(year, month, last_day),
    )


def _step_ethiopian_month(year, month, step):
    """The Ethiopian month ``step`` places from (year, month). 13 months."""
    index = (year * 13) + (month - 1) + step
    return divmod(index, 13)[0], divmod(index, 13)[1] + 1


def period_containing(calendar, day):
    """The whole period of ``calendar`` that contains ``day``.

    Returned as (first_day, last_day) in Gregorian dates, because every date
    stored in the database is Gregorian — the calendar decides where the
    BOUNDARIES fall, not how a date is written down.
    """
    _require_calendar(calendar)
    if calendar == GREGORIAN:
        first = day.replace(day=1)
        return first, _end_of_gregorian_month(first)
    ethiopian = et_calendar.gregorian_to_ethiopian(day)
    return _ethiopian_month_bounds(ethiopian.year, ethiopian.month)


def previous_period(calendar, today):
    """The last period of ``calendar`` that had finished before ``today``."""
    _require_calendar(calendar)
    start, _end = period_containing(calendar, today)
    return period_containing(calendar, start - timedelta(days=1))


def next_period_end(calendar, period_end):
    """The last day of the period that FOLLOWS the one ending at ``period_end``.

    This is the employment income tax filing window: the reference records it as
    *"The declaration for one Ethiopian month is filed at any time during the
    following Ethiopian month"*, with the accountant's example *"Sene taxes must
    be reported from Hamle 01 to Hamle 30"* — so the deadline is the last day of
    the next month, not a day count. The two agree for every ordinary Ethiopian
    month, which is 30 days; they part company at Pagume, which is 5 or 6.
    """
    _require_calendar(calendar)
    if calendar == GREGORIAN:
        first_of_next = (period_end.replace(day=1) + timedelta(days=32)).replace(day=1)
        return _end_of_gregorian_month(first_of_next)
    ethiopian = et_calendar.gregorian_to_ethiopian(period_end)
    year, month = _step_ethiopian_month(ethiopian.year, ethiopian.month, 1)
    return _ethiopian_month_bounds(year, month)[1]


def is_whole_period(calendar, date_from, date_to):
    """True when [date_from, date_to] is exactly one period of ``calendar``.

    The predicate behind the page's label rule: a range that is a whole month
    may be NAMED as that month, and a range that is not must be described as
    what it actually is. "Sene 2018 – Hamle 2018" over 31 days beginning
    mid-Sene named two months and covered neither.
    """
    if not date_from or not date_to or calendar not in CALENDARS:
        return False
    return (date_from, date_to) == period_containing(calendar, date_from)


def _end_of_gregorian_month(first_of_month):
    return (first_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)


def _require_calendar(calendar):
    if calendar not in CALENDARS:
        raise ValueError(
            "unknown filing calendar %r; expected one of %r" % (calendar, CALENDARS)
        )


def is_complete_month(date_from, date_to, today=None):
    """True when the window is a whole calendar month already in the past."""
    if not date_from or not date_to:
        return False
    if date_from.day != 1:
        return False
    next_month = (date_to.replace(day=1) + timedelta(days=32)).replace(day=1)
    if date_to != next_month - timedelta(days=1):
        return False
    return date_to < (today or date.today())


def effective_rule(rules, on_date):
    """The rule in force on ``on_date``: the latest one that had started.

    ``rules`` is an iterable of (effective_from, days). Returns the days, or
    None when nothing had started yet — which is what makes a period assessed
    before any rule existed read UNKNOWN instead of borrowing a later rule.
    """
    best = None
    for effective_from, days in rules:
        if effective_from is None or effective_from > on_date:
            continue
        if best is None or effective_from > best[0]:
            best = (effective_from, days)
    return None if best is None else best[1]


__all__ = [
    "FILING_KEYS",
    "GREGORIAN",
    "ETHIOPIAN",
    "CALENDARS",
    "WINDOW_DAYS",
    "WINDOW_END_OF_NEXT_PERIOD",
    "WINDOWS",
    "UNKNOWN",
    "FILED",
    "DUE",
    "LATE",
    "deadline_for",
    "status_for",
    "days_remaining",
    "previous_month",
    "period_containing",
    "previous_period",
    "next_period_end",
    "is_whole_period",
    "is_complete_month",
    "effective_rule",
    "date",
]
