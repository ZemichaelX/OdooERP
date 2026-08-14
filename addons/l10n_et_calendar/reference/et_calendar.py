# -*- coding: utf-8 -*-
"""Ethiopian (Ge'ez) calendar ⇄ Gregorian conversion — pure Python, no Odoo.

CLAUDE.md rule 10: the conversion is arithmetic, so it lives here and the Odoo
layer only calls it. Same shape as the PAYE and pension calculators.

A CALENDAR THAT IS WRONG BY ONE DAY IS WORSE THAN NO CALENDAR, because it will
be trusted. So every constant below is sourced, both directions are total
functions that raise on invalid input, and the golden set in
tests_fast/test_et_calendar.py is validated against things OUTSIDE this file:
three project dates verified against proclamations, the Julian-calendar
invariant that defines the Ethiopic new year, and a one-off run against an
independent third-party implementation. Never against this file's own output.

THE STRUCTURE
-------------
Twelve months of exactly 30 days, then Pagume (ጳጉሜን), a thirteenth month of 5
days — 6 in a leap year. So a common year is 365 days and a leap year 366, the
same totals as the Gregorian calendar, which is why the two stay in step.

THE LEAP RULE, AND ITS SOURCE
-----------------------------
    An Ethiopian year Y is a leap year (Pagume has 6 days) if and only if
    Y mod 4 == 3.

Source: Nachum Dershowitz and Edward M. Reingold, *Calendrical Calculations*
(Cambridge University Press), which gives the Ethiopic calendar as the Coptic
calendar on a different epoch, both with an unbroken 4-year leap cycle and no
century exception. This is a SECONDARY source in the same sense as the PAYE
band citations in l10n_et_payroll — named so a reader can check it, not
presented as a gazette.

The rule is stated from the source rather than inferred from examples. It is
then corroborated two ways: an independent third-party implementation applies
the same `year % 4 == 3` predicate, and the Julian-calendar invariant holds
across 2,300 Ethiopian years — Meskerem 1 lands on 30 August Julian exactly in
the years following a leap year, which is only true if the leap rule is right.

Note the absence of a century rule. The Ethiopian calendar does NOT skip a leap
year in 1900/2100-style years, so the two calendars drift by one day at every
Gregorian century that is not a leap year. That drift is real, measured, and
the reason no Gregorian date of an Ethiopian month-start is a constant:

    Hamle 1 falls on   6 July in Gregorian 1708-1799
                       7 July in           1800-1899
                       8 July in           1900-2099   <- every date we handle
                       9 July in           2100-2199

Within a 4-year cycle it does not move at all: Pagume 6 pushes Meskerem 1 from
11 to 12 September, and the following Gregorian February gives the day back
with its own 29th. Only the century rule moves these boundaries.

THE EPOCH
---------
    Meskerem 1, 1 EC (Amete Mihret) = 29 August 8 CE in the JULIAN calendar,
    Julian Day Number 1_724_221.

Same source. Everything else is derived from that one anchor through Julian Day
Numbers, so there is a single place a date could be off by one, and three
independently verified anchors that would catch it if it were.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

__all__ = [
    "ETHIOPIC_EPOCH_JDN",
    "EthiopianDate",
    "MONTHS",
    "MONTHS_AMHARIC",
    "MONTHS_LATIN",
    "PAGUME",
    "days_in_month",
    "ethiopian_to_gregorian",
    "gregorian_to_ethiopian",
    "is_leap_year",
    "month_name",
]

# Julian Day Number of Meskerem 1, 1 EC (Amete Mihret) — see the module
# docstring for the source. This is the ONLY calendrical constant here; every
# other value is derived from it.
ETHIOPIC_EPOCH_JDN = 1_724_221

#: The thirteenth month, 5 days long (6 in a leap year).
PAGUME = 13

# Month names as DATA, in both scripts, so the Odoo layer can wrap them in _()
# and the Amharic actually renders in Amharic. Deliberately no English here: a
# hardcoded English string in a localisation library is a translation that can
# never be corrected.
#
# Transliteration follows the spelling used in Ethiopian government and banking
# practice (Meskerem, Tikimt, Hidar, …), which is what a user expects to see on
# a purchase order.
MONTHS: tuple[tuple[str, str], ...] = (
    ("Meskerem", "መስከረም"),
    ("Tikimt", "ጥቅምት"),
    ("Hidar", "ኅዳር"),
    ("Tahsas", "ታኅሣሥ"),
    ("Tir", "ጥር"),
    ("Yekatit", "የካቲት"),
    ("Megabit", "መጋቢት"),
    ("Miyazya", "ሚያዝያ"),
    ("Ginbot", "ግንቦት"),
    ("Sene", "ሰኔ"),
    ("Hamle", "ሐምሌ"),
    ("Nehase", "ነሐሴ"),
    ("Pagume", "ጳጉሜን"),
)
MONTHS_LATIN: tuple[str, ...] = tuple(latin for latin, _amharic in MONTHS)
MONTHS_AMHARIC: tuple[str, ...] = tuple(amharic for _latin, amharic in MONTHS)


@dataclass(frozen=True, order=True)
class EthiopianDate:
    """One Ethiopian calendar date. Immutable and orderable.

    ``month`` is 1..13, where 13 is Pagume. ``day`` is 1..30, or 1..5 (1..6 in
    a leap year) in Pagume.
    """

    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        _validate_ethiopian(self.year, self.month, self.day)

    @property
    def month_latin(self) -> str:
        return MONTHS_LATIN[self.month - 1]

    @property
    def month_amharic(self) -> str:
        return MONTHS_AMHARIC[self.month - 1]

    @property
    def is_pagume(self) -> bool:
        return self.month == PAGUME

    def __str__(self) -> str:  # "Hamle 1, 2017"
        return "%s %d, %d" % (self.month_latin, self.day, self.year)


def is_leap_year(year: int) -> bool:
    """True when Pagume has 6 days in Ethiopian year ``year``.

    Y mod 4 == 3, with no century exception — see the module docstring.
    """
    _require_int(year, "year")
    if year < 1:
        raise ValueError("Ethiopian year must be >= 1, got %r" % (year,))
    return year % 4 == 3


def days_in_month(year: int, month: int) -> int:
    """30 for months 1..12; 5 or 6 for Pagume."""
    _require_int(month, "month")
    if not 1 <= month <= 13:
        raise ValueError("Ethiopian month must be 1..13 (13 = Pagume), got %r" % (month,))
    if month < PAGUME:
        return 30
    return 6 if is_leap_year(year) else 5


def month_name(month: int, amharic: bool = False) -> str:
    """The month's name. Data, not a translation — see MONTHS."""
    _require_int(month, "month")
    if not 1 <= month <= 13:
        raise ValueError("Ethiopian month must be 1..13 (13 = Pagume), got %r" % (month,))
    return MONTHS_AMHARIC[month - 1] if amharic else MONTHS_LATIN[month - 1]


# ---------------------------------------------------------------------------
# Julian Day Number, the pivot both directions go through.
#
# One well-understood integer axis rather than two calendars talking to each
# other directly. The Gregorian conversion is Fliegel & Van Flandern's standard
# integer algorithm (Communications of the ACM 11:10, 1968), which is exact for
# all Gregorian dates and uses no floating point — a float here is how a
# calendar ends up off by one at a boundary.
# ---------------------------------------------------------------------------


def _gregorian_to_jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def _jdn_to_gregorian(jdn: int) -> tuple[int, int, int]:
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - 146097 * b // 4
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day


def _ethiopian_to_jdn(year: int, month: int, day: int) -> int:
    """Days elapsed since the epoch, as a Julian Day Number.

    Whole years before ``year`` contribute 365 days each plus one leap day for
    every past year with Y mod 4 == 3. The count of those in 1..Y-1 is exactly
    ``year // 4`` (leap years are 3, 7, 11, …), which is why no loop is needed.
    """
    return ETHIOPIC_EPOCH_JDN + 365 * (year - 1) + year // 4 + 30 * (month - 1) + (day - 1)


def _jdn_to_ethiopian(jdn: int) -> EthiopianDate:
    """Inverse of :func:`_ethiopian_to_jdn`.

    The cycle is 1461 days: years 4k+1 and 4k+2 have 365 days, 4k+3 is the leap
    year with 366, and 4k+4 has 365 again. The four spans within a cycle are
    written out rather than derived with ``remainder // 365``, because that
    division is wrong on exactly two days of every cycle — the last day of the
    leap year (remainder 1095, Pagume 6) and the last day of the cycle
    (remainder 1460, Pagume 5). A first draft here used the division with a
    patch for 1460 only; the round-trip property test found Pagume 6 within
    seconds, which is precisely the "wrong by one day" failure this module
    exists to prevent, and is why the boundaries are now explicit.
    """
    elapsed = jdn - ETHIOPIC_EPOCH_JDN
    if elapsed < 0:
        raise ValueError(
            "date precedes the Ethiopian epoch (Meskerem 1, 1 EC = 29 August 8 CE "
            "Julian); this library does not extrapolate backwards"
        )
    cycles, remainder = divmod(elapsed, 1461)
    if remainder < 365:
        offset = 0
    elif remainder < 730:
        offset = 1
    elif remainder < 1096:  # 366 days: the leap year, Y mod 4 == 3
        offset = 2
    else:
        offset = 3
    year = 4 * cycles + offset + 1
    day_of_year = elapsed - (365 * (year - 1) + year // 4)
    month = day_of_year // 30 + 1
    day = day_of_year % 30 + 1
    return EthiopianDate(year, month, day)


# ---------------------------------------------------------------------------
# The public conversions. Both TOTAL: every input either returns a correct
# date or raises. Nothing returns something plausible.
# ---------------------------------------------------------------------------


def gregorian_to_ethiopian(value: date) -> EthiopianDate:
    """Convert a ``datetime.date`` to its Ethiopian calendar date.

    Raises TypeError for anything that is not a date. A ``datetime`` is
    accepted because it IS a date subclass, and its time is discarded — the
    Ethiopian day starts at dawn rather than midnight, but every stored value
    in this system is a calendar date, so applying a dawn offset would invent
    precision the data does not have.
    """
    if not isinstance(value, date):
        raise TypeError("expected a datetime.date, got %r" % (type(value).__name__,))
    return _jdn_to_ethiopian(_gregorian_to_jdn(value.year, value.month, value.day))


def ethiopian_to_gregorian(year: int, month: int, day: int) -> date:
    """Convert an Ethiopian y/m/d to a ``datetime.date``.

    Raises ValueError on any date the Ethiopian calendar does not contain —
    month 14, day 31, or Pagume 6 in a common year. Returning a nearby date
    instead would be the "wrong by one day" failure this module exists to
    prevent.
    """
    _validate_ethiopian(year, month, day)
    return date(*_jdn_to_gregorian(_ethiopian_to_jdn(year, month, day)))


# ---------------------------------------------------------------------------


def _require_int(value: object, label: str) -> None:
    # bool is an int subclass and True would silently mean 1.
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("%s must be an int, got %r" % (label, type(value).__name__))


def _validate_ethiopian(year: int, month: int, day: int) -> None:
    for label, value in (("year", year), ("month", month), ("day", day)):
        _require_int(value, label)
    if year < 1:
        raise ValueError("Ethiopian year must be >= 1, got %r" % (year,))
    if not 1 <= month <= 13:
        raise ValueError("Ethiopian month must be 1..13 (13 = Pagume), got %r" % (month,))
    limit = days_in_month(year, month)
    if not 1 <= day <= limit:
        raise ValueError(
            "%s %d, %d does not exist: %s has %d days in %d EC"
            % (MONTHS_LATIN[month - 1], day, year, MONTHS_LATIN[month - 1], limit, year)
        )
