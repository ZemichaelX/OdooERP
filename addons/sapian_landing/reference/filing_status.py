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

from datetime import date, timedelta

#: The four statutory filings this product can put a number against.
FILING_KEYS = ("vat", "wht", "paye", "pension")

#: A filing whose deadline cannot be established at all.
UNKNOWN = "unknown"
#: Recorded as submitted.
FILED = "filed"
#: Not submitted, deadline still ahead.
DUE = "due"
#: Not submitted, deadline passed.
LATE = "late"


def deadline_for(period_end, days_after_period_end):
    """The date a period's filing is due, or ``None`` when no rule applies.

    ``None`` and not a guess: a period with no effective rule has an UNKNOWN
    status on the page, which is the honest answer and the one the operator can
    act on. Inventing "probably the 30th" would be a placeholder wearing a date.
    """
    if not period_end or days_after_period_end is None:
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
    """The period a monthly filing is about: the month before ``today``.

    Returned as (first_day, last_day). The current month is never the period —
    a monthly return is filed for a month that has finished, and showing the
    running month as "due" would put a half-collected figure under a deadline.
    """
    first_of_this = today.replace(day=1)
    last_of_prev = first_of_this - timedelta(days=1)
    return last_of_prev.replace(day=1), last_of_prev


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
    "UNKNOWN",
    "FILED",
    "DUE",
    "LATE",
    "deadline_for",
    "status_for",
    "days_remaining",
    "previous_month",
    "is_complete_month",
    "effective_rule",
    "date",
]
