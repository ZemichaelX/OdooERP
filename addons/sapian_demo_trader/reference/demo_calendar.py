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
"""

from datetime import date, timedelta

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
