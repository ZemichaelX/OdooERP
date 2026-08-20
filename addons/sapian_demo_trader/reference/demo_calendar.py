# -*- coding: utf-8 -*-
"""When the demo tenant traded. Computed from the build date, never pinned.

WHY THIS REPLACED A PINNED MONTH
--------------------------------
Every date in this demo used to be a literal inside July 2026, and the reason
given was a good one: statutory reports need one clean period window with exact
GL tie-outs, and a demo whose numbers move with the calendar cannot have
goldens.

What that reasoning missed is that the demo is not only a fixture. It is what a
prospect is shown, and it is what the landing page reads — and the landing page
shows THE MONTH THAT HAS FINISHED, because that is the month with a filing
deadline attached. A tenant pinned to July 2026 is the right month while the
build happens in August 2026 and is silently the wrong one from September
onwards: the page correctly reports that it has nothing to show, and the demo
correctly has nothing to show it.

So the anchor moves and the SHAPE does not. Every window here is a whole
calendar month, and the goldens assert the shape — four consecutive months,
opening the day before the first of them — rather than four particular dates.
That keeps exact tie-outs (the reports still see one clean month) without
pinning the tenant to a month that recedes.

    opening   the last day of the month BEFORE the first trading month.
              Stock and capital arrive here, so the first trading month opens
              with something to trade.
    early     three months back: the oldest trading month.
    middle    two months back.
    current   ONE month back — the month the landing page reads, the month
              with a filing deadline, and the month carrying the full
              compliance showcase.

A demo whose books begin twenty days before the demo is its own kind of
unconvincing, which is the other half of why there are three trading months and
not one.

PAYROLL RUNS ON ETHIOPIAN MONTHS, AND THE REST DOES NOT
--------------------------------------------------------
`docs/ethiopian-tax-reference.md` section 2 is VERIFIED that the employment
income tax period is an ETHIOPIAN month, and records that the payroll CYCLE
itself is a business choice: one accountant runs Ethiopian months, the other
Gregorian. This tenant runs Ethiopian months — accountant 1's practice — because
that is the cycle the reference settles the filing mapping for. A Gregorian-cycle
run cannot be placed onto a filing month from anything the reference says, and a
demo should not show the product guessing.

The two calendars overlap rather than nest, which is exactly what a real
Ethiopian company's books look like: trading, VAT and withholding on Gregorian
months, payroll and its declaration on Ethiopian ones. `ethiopian_payroll_months`
returns one Ethiopian month ending inside each Gregorian trading month, plus the
last complete Ethiopian month — the one the landing page asks for.
"""

import importlib.util
import os
import sys as _sys
from datetime import date, timedelta

# The Ethiopian calendar, reachable from inside Odoo and from `tests_fast/`,
# which loads this file by path. Same shape as the fallback in
# sapian_landing/reference/filing_status.py, and for the same reason: a package
# import would make the goldens uncollectable, and a silent None would make them
# pass by not running.
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
    _NAME = "sapian_demo_trader._et_calendar_offdisk"
    _spec = importlib.util.spec_from_file_location(_NAME, _ET)
    et_calendar = importlib.util.module_from_spec(_spec)
    _sys.modules[_NAME] = et_calendar  # dataclasses reads sys.modules on decorate
    _spec.loader.exec_module(et_calendar)

#: How many whole trading months the tenant has traded for.
TRADING_MONTHS = 3


def month_window(anchor, months_back):
    """The (first, last) day of the calendar month ``months_back`` before ``anchor``.

    ``months_back=1`` from any day in August is the whole of July. Walked back
    a month at a time through the first of each month rather than by
    subtracting days, because "30 days ago" is not "last month" and the
    difference lands on exactly the month boundaries this demo is made of.
    """
    first = anchor.replace(day=1)
    for _ in range(months_back):
        first = (first - timedelta(days=1)).replace(day=1)
    last = _end_of_month(first)
    return first, last


def _end_of_month(first_of_month):
    return (first_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(
        days=1
    )


def demo_calendar(today=None):
    """Every window the demo needs, from one anchor.

    Returns a dict of ``{name: (first, last)}`` plus ``opening``, a single
    date. The caller passes the build date so tests can build any month they
    like and the provisioner passes the real one.
    """
    today = today or date.today()
    current = month_window(today, 1)
    middle = month_window(today, 2)
    early = month_window(today, 3)
    return {
        "current": current,
        "middle": middle,
        "early": early,
        # The day before trading starts. Opening stock and opening capital are
        # dated here so the first trading month's cost of sales draws on goods
        # that were already on hand, rather than on goods received the same day
        # they were sold.
        "opening": early[0] - timedelta(days=1),
    }


def day_in(window, day):
    """The ``day``-th of a window's month, clamped to the month's length.

    Clamped rather than validated: the demo's day numbers are chosen for a
    31-day month, and a February build must move them rather than raise. A
    provisioner that crashes in February is worse than one whose 30th lands on
    the 28th.
    """
    first, last = window
    return first.replace(day=min(day, last.day))


#: How many Ethiopian payroll months the tenant runs. One ends inside each of
#: the three Gregorian trading months, and the fourth is the last Ethiopian
#: month to have finished — which is the one the landing page asks for and the
#: whole reason the count is four rather than three.
PAYROLL_MONTHS = 4


def _ethiopian_month_window(year, month):
    last_day = et_calendar.days_in_month(year, month)
    return (
        et_calendar.ethiopian_to_gregorian(year, month, 1),
        et_calendar.ethiopian_to_gregorian(year, month, last_day),
    )


def ethiopian_payroll_months(today=None):
    """The Ethiopian months this tenant runs payroll for, oldest first.

    The newest is the last Ethiopian month to have FINISHED before ``today``,
    because that is the period the landing page shows as due — a run for the
    month still in progress would be a half-month payslip under a deadline.

    Thirteen months to the Ethiopian year, and the thirteenth (Pagume) is 5 or 6
    days long. It is not skipped: a company pays its staff in Pagume too, and
    Pagume is the one month where "+30 days" and "the end of the following
    month" give different filing deadlines, so a demo that stepped over it would
    never show the difference.
    """
    today = today or date.today()
    current = et_calendar.gregorian_to_ethiopian(today)
    index = (current.year * 13) + (current.month - 1) - 1  # the month before this one
    months = []
    for offset in range(PAYROLL_MONTHS - 1, -1, -1):
        year, month = divmod(index - offset, 13)
        months.append(_ethiopian_month_window(year, month + 1))
    return months


def iso(value):
    """A date as the ISO string the ORM and the report models both accept."""
    return value.strftime("%Y-%m-%d")


__all__ = [
    "TRADING_MONTHS",
    "month_window",
    "demo_calendar",
    "day_in",
    "iso",
    "date",
]
