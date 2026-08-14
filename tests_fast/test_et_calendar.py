# -*- coding: utf-8 -*-
"""Golden tests for the Ethiopian calendar conversion (no Odoo needed).

A CALENDAR THAT IS WRONG BY ONE DAY IS WORSE THAN NO CALENDAR, so this file is
deliberately larger than the library it tests.

WHAT THE GOLDENS ARE VALIDATED AGAINST
--------------------------------------
Three authorities, in decreasing order of how much weight they carry:

1. **The three project anchors.** Every Ethiopian legal effective date this
   project has verified independently against a proclamation lands on the 1st
   of an Ethiopian month, and those dates are already shipping in migrated
   data. They are the strongest evidence available here because they were
   established without reference to any calendar library.

2. **The Julian-calendar invariant**, asserted below over 2,300 Ethiopian
   years. The Ethiopic new year is FIXED against the Julian calendar: Meskerem
   1 falls on 29 August Julian, or 30 August in the year following a leap year.
   That is the defining property of the calendar, it needs no third-party
   package, and it is what makes the century drift checkable rather than
   assumed.

3. **A one-off cross-check against an independent implementation**, recorded
   here rather than executed: the `ethiopian-date` PyPI package
   (`EthiopianDateConverter`) was run against every Ethiopian date from EC 1893
   to EC 2100 — 75,972 dates, 1,092 of them in Pagume. It agrees with this
   library on all but 14 Ethiopian years: EC 1893–1899 and EC 2093–2099.

   THOSE 14 YEARS ARE THE PACKAGE'S BUG, NOT OURS, and the invariant above is
   how that was settled. The package derives the Gregorian century correction
   from the ETHIOPIAN year (`(year // 100) - (year // 400) - 4`), so it steps
   at EC 1900 — which is Gregorian 1907, seven years after the Gregorian leap
   day that was actually skipped in February 1900. Its Meskerem 1, 1893 EC =
   10 September 1900 is 28 August 1900 Julian, which is not a valid Ethiopic
   new year at all. Ours is 11 September 1900 = 29 August Julian. The package
   is not a test dependency; it is not in CI and this file does not import it.

Run: pytest tests_fast/
"""

import importlib.util
import os
import sys as _sys
from datetime import date, datetime

import pytest

# Same standalone loader the other fast tests use: no Odoo, no package imports.
_CAL = os.path.join(
    os.path.dirname(__file__),
    "..",
    "addons",
    "l10n_et_calendar",
    "reference",
    "et_calendar.py",
)
_spec = importlib.util.spec_from_file_location("et_calendar", _CAL)
cal = importlib.util.module_from_spec(_spec)
_sys.modules[_spec.name] = cal
_spec.loader.exec_module(cal)


# ===========================================================================
# 1. THE THREE ANCHORS. Non-negotiable: if the library disagrees with any of
#    these, the library is wrong. Each was verified against its proclamation
#    independently of any calendar code and is already in migrated data.
# ===========================================================================


@pytest.mark.parametrize(
    "gregorian,ethiopian,provenance",
    [
        (
            date(2025, 7, 8),
            (2017, 11, 1),
            "PAYE Proclamation 1395/2025 commencement — l10n_et_payroll/reference"
            "/et_payroll_calc.py PAYE_1395_2025_EFFECTIVE_FROM",
        ),
        (
            date(2014, 7, 8),
            (2006, 11, 1),
            "pension 7%/11% coincidence — l10n_et_payroll/models/pension_config.py",
        ),
        (
            date(2025, 8, 7),
            (2017, 12, 1),
            "domestic WHT change — l10n_et_base knowledge base, Nehase 1 2017 EC",
        ),
    ],
)
def test_project_anchor_dates(gregorian, ethiopian, provenance):
    """Each anchor is the 1st of an Ethiopian month. That is the point."""
    result = cal.gregorian_to_ethiopian(gregorian)
    assert (result.year, result.month, result.day) == ethiopian, provenance
    assert result.day == 1, "%s should be the 1st of an Ethiopian month (%s), got day %d" % (
        gregorian,
        provenance,
        result.day,
    )
    assert cal.ethiopian_to_gregorian(*ethiopian) == gregorian


def test_anchor_month_names_are_the_ones_the_proclamations_use():
    """Hamle and Nehase, spelled as Ethiopian practice spells them."""
    assert cal.gregorian_to_ethiopian(date(2025, 7, 8)).month_latin == "Hamle"
    assert cal.gregorian_to_ethiopian(date(2025, 7, 8)).month_amharic == "ሐምሌ"
    assert cal.gregorian_to_ethiopian(date(2025, 8, 7)).month_latin == "Nehase"
    assert cal.gregorian_to_ethiopian(date(2025, 8, 7)).month_amharic == "ነሐሴ"


# ===========================================================================
# 2. THE LEAP RULE
# ===========================================================================


@pytest.mark.parametrize(
    "year,leap",
    [
        (2011, True),  # 2011 % 4 == 3
        (2012, False),
        (2013, False),
        (2014, False),
        (2015, True),
        (2016, False),
        (2017, False),
        (2018, False),
        (2019, True),
        (1999, True),  # the year before the Ethiopian millennium
        (2000, False),
        (1900, False),  # NO century exception, unlike the Gregorian calendar
        (1903, True),
        (2100, False),
        (2103, True),
    ],
)
def test_leap_years(year, leap):
    assert cal.is_leap_year(year) is leap


def test_pagume_length_follows_the_leap_rule():
    assert cal.days_in_month(2015, 13) == 6
    assert cal.days_in_month(2016, 13) == 5
    assert cal.days_in_month(2017, 13) == 5
    assert cal.days_in_month(2019, 13) == 6


@pytest.mark.parametrize("month", range(1, 13))
def test_every_month_but_pagume_has_thirty_days(month):
    assert cal.days_in_month(2015, month) == 30
    assert cal.days_in_month(2016, month) == 30


def test_year_length_is_365_or_366():
    """The whole calendar in one property: 12*30 + Pagume."""
    for year in (2014, 2015, 2016, 2017):
        total = sum(cal.days_in_month(year, m) for m in range(1, 14))
        assert total == (366 if cal.is_leap_year(year) else 365)


# ===========================================================================
# 3. THE INDEPENDENT AUTHORITY: the Julian-calendar invariant.
#
#    Meskerem 1 is 29 August Julian, or 30 August in the year AFTER a leap
#    year. Nothing about this comes from our own conversion output — it is the
#    calendar's defining relationship, and it is what proves the century drift
#    lands where the Gregorian calendar actually skips a leap day.
# ===========================================================================


def _julian_from_jdn(jdn):
    """Julian-calendar y/m/d for a Julian Day Number.

    The same integer algorithm as the Gregorian one in the library, minus the
    146097-day century term — which is exactly what "the Julian calendar has no
    century rule" means arithmetically. Richards, *Explanatory Supplement to
    the Astronomical Almanac*.

    Sanity-checked below against the Gregorian reform: JDN 2299161 is
    15 October 1582 Gregorian and 5 October 1582 Julian.
    """
    c = jdn + 32082
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = d - 4800 + m // 10
    return year, month, day


def test_the_julian_helper_is_itself_correct():
    """The authority has to be right before it can be an authority.

    A first draft of this helper was wrong and reported every Meskerem 1 as
    month -5100, which would have looked like a library bug.
    """
    assert _julian_from_jdn(2299161) == (1582, 10, 5)  # the Gregorian reform
    assert _julian_from_jdn(2299160) == (1582, 10, 4)


def _julian_of(ethiopian_year, month, day):
    gregorian = cal.ethiopian_to_gregorian(ethiopian_year, month, day)
    jdn = cal._gregorian_to_jdn(gregorian.year, gregorian.month, gregorian.day)
    return _julian_from_jdn(jdn)


def test_meskerem_1_is_always_29_or_30_august_julian():
    """2,300 years, zero exceptions. This is the strongest structural check
    available without a third-party package, and it is what settles the
    century-drift question the cross-check disagreed on."""
    offenders = []
    for ethiopian_year in range(1, 2301):
        _jy, jmonth, jday = _julian_of(ethiopian_year, 1, 1)
        if (jmonth, jday) not in ((8, 29), (8, 30)):
            offenders.append((ethiopian_year, jmonth, jday))
    assert not offenders, "Meskerem 1 off the Julian anchor: %s" % offenders[:5]


def test_meskerem_1_takes_30_august_julian_exactly_after_a_leap_year():
    for ethiopian_year in range(1, 601):
        _jy, _jm, jday = _julian_of(ethiopian_year, 1, 1)
        follows_leap = cal.is_leap_year(ethiopian_year - 1) if ethiopian_year > 1 else False
        assert (
            jday == 30
        ) is follows_leap, "EC %d: Julian %d August, follows a leap year: %s" % (
            ethiopian_year,
            jday,
            follows_leap,
        )


def test_the_1900_century_step_lands_where_gregorian_skips_a_leap_day():
    """The 14 years the third-party package gets wrong, pinned.

    Gregorian 1900 was not a leap year; the Ethiopian calendar has no century
    rule, so the drift takes effect for the first Ethiopian year that STARTS
    after February 1900 — EC 1893, which begins in September 1900. A converter
    that steps at Ethiopian year 1900 applies it seven years late.
    """
    assert cal.ethiopian_to_gregorian(1892, 1, 1) == date(1899, 9, 11)
    assert cal.ethiopian_to_gregorian(1893, 1, 1) == date(1900, 9, 11)
    assert _julian_of(1893, 1, 1)[1:] == (8, 29)
    assert cal.ethiopian_to_gregorian(1900, 1, 1) == date(1907, 9, 12)
    assert _julian_of(1900, 1, 1)[1:] == (8, 30)


# ===========================================================================
# 4. MONTH BOUNDARIES, both directions — every one of the 13.
# ===========================================================================


@pytest.mark.parametrize("month", range(1, 14))
def test_month_first_and_last_day_round_trip(month):
    """First and last day of every month, in a common and a leap year."""
    for year in (2016, 2015):  # common, leap
        last = cal.days_in_month(year, month)
        for day in (1, last):
            gregorian = cal.ethiopian_to_gregorian(year, month, day)
            back = cal.gregorian_to_ethiopian(gregorian)
            assert (back.year, back.month, back.day) == (year, month, day)


@pytest.mark.parametrize("month", range(1, 13))
def test_day_30_rolls_into_the_next_month(month):
    """The day after the 30th is the 1st of the next month, never the 31st."""
    end = cal.ethiopian_to_gregorian(2016, month, 30)
    following = cal.gregorian_to_ethiopian(date.fromordinal(end.toordinal() + 1))
    assert (following.month, following.day) == (month + 1, 1)


# ===========================================================================
# 5. PAGUME AND THE YEAR BOUNDARY
# ===========================================================================


def test_pagume_5_is_the_last_day_of_a_common_year():
    assert cal.ethiopian_to_gregorian(2016, 13, 5) == date(2024, 9, 10)
    assert cal.gregorian_to_ethiopian(date(2024, 9, 11)) == cal.EthiopianDate(2017, 1, 1)


def test_pagume_6_exists_only_in_a_leap_year_and_is_its_last_day():
    assert cal.ethiopian_to_gregorian(2015, 13, 6) == date(2023, 9, 11)
    assert cal.gregorian_to_ethiopian(date(2023, 9, 12)) == cal.EthiopianDate(2016, 1, 1)
    with pytest.raises(ValueError, match="Pagume has 5 days"):
        cal.ethiopian_to_gregorian(2016, 13, 6)


def test_pagume_6_round_trips_in_every_leap_year_of_a_century():
    """The bug this file caught during development.

    A first draft derived the Ethiopian year from the day count with
    `remainder // 365`, which is wrong on exactly two days of every 4-year
    cycle — Pagume 6 of the leap year, and Pagume 5 of the last year. It
    produced month 0. This asserts both, in every cycle of a century.
    """
    for year in range(1999, 2100):
        if not cal.is_leap_year(year):
            continue
        for month, day in ((13, 6), (13, 5)):
            gregorian = cal.ethiopian_to_gregorian(year, month, day)
            back = cal.gregorian_to_ethiopian(gregorian)
            assert (back.year, back.month, back.day) == (year, month, day)
        # and the last day of the FOLLOWING (common) year
        after = cal.ethiopian_to_gregorian(year + 1, 13, 5)
        assert cal.gregorian_to_ethiopian(after) == cal.EthiopianDate(year + 1, 13, 5)


@pytest.mark.parametrize(
    "gregorian,expected",
    [
        (date(2023, 9, 10), (2015, 13, 5)),
        (date(2023, 9, 11), (2015, 13, 6)),  # leap year: Pagume 6
        (date(2023, 9, 12), (2016, 1, 1)),  # new year
        (date(2024, 9, 9), (2016, 13, 4)),
        (date(2024, 9, 10), (2016, 13, 5)),  # common year: no Pagume 6
        (date(2024, 9, 11), (2017, 1, 1)),
        (date(2025, 9, 10), (2017, 13, 5)),
        (date(2025, 9, 11), (2018, 1, 1)),
    ],
)
def test_new_year_boundary(gregorian, expected):
    result = cal.gregorian_to_ethiopian(gregorian)
    assert (result.year, result.month, result.day) == expected


# ===========================================================================
# 6. THE TWO TRAPS THE BRIEF NAMED
# ===========================================================================


def test_hamle_1_is_8_july_for_the_whole_of_the_20th_and_21st_centuries():
    """MEASURED, and it refines the premise it was set to test.

    Hamle 1 DOES fall on 7 July — but in the 19th century, and not because of
    Pagume 6. Its Gregorian date is a step function of the GREGORIAN CENTURY
    RULE: the Ethiopian calendar has no century exception, so every Gregorian
    century that skips a leap day moves Hamle 1 one day later, permanently.

        Gregorian 1708–1799   ->  6 July
        Gregorian 1800–1899   ->  7 July     <- the 7-July years, all of them
        Gregorian 1900–2099   ->  8 July     <- every date this ERP will see
        Gregorian 2100–2199   ->  9 July
        Gregorian 2200–2299   -> 10 July

    So across EC 1892–2091 — 200 consecutive years — it is 8 July every single
    time, with no exceptions and no Pagume-driven wobble. Within a 4-year cycle
    it cannot move at all; the next test shows why.

    An earlier draft of this test asserted "never 7 July" over six centuries
    and failed immediately on EC 1792. Left recorded because the failure is the
    useful part: the trap is real, it is just in a different century and has a
    different cause than expected.
    """
    non_eighth = [
        (year, cal.ethiopian_to_gregorian(year, 11, 1))
        for year in range(1892, 2092)
        if (
            cal.ethiopian_to_gregorian(year, 11, 1).month,
            cal.ethiopian_to_gregorian(year, 11, 1).day,
        )
        != (7, 8)
    ]
    assert not non_eighth, "Hamle 1 off 8 July: %s" % non_eighth[:5]


@pytest.mark.parametrize(
    "ethiopian_year,expected",
    [
        (1791, date(1799, 7, 6)),  # last of the 6-July run
        (1792, date(1800, 7, 7)),  # 1800 is not a Gregorian leap year
        (1891, date(1899, 7, 7)),  # last of the 7-July run
        (1892, date(1900, 7, 8)),  # 1900 is not a Gregorian leap year
        (2091, date(2099, 7, 8)),  # last of the 8-July run
        (2092, date(2100, 7, 9)),  # 2100 is not a Gregorian leap year
        (2192, date(2200, 7, 10)),
    ],
)
def test_hamle_1_steps_one_day_at_every_skipped_gregorian_leap_day(ethiopian_year, expected):
    """The step lands on the century, and only on the century. Note 2000 is
    absent: it WAS a Gregorian leap year, so nothing moved."""
    assert cal.ethiopian_to_gregorian(ethiopian_year, 11, 1) == expected


def test_no_step_at_the_year_2000_because_it_was_a_leap_year():
    for ethiopian_year in (1991, 1992, 1993):
        assert cal.ethiopian_to_gregorian(ethiopian_year, 11, 1).day == 8


def test_pagume_6_moves_meskerem_1_but_the_next_february_gives_it_back():
    """Why Hamle 1 is steady while Meskerem 1 is not.

    Pagume 6 pushes the new year from 11 to 12 September. By Hamle — ten
    months later — the following Gregorian February has already absorbed the
    extra day with its own 29th, so the two calendars are back in step.
    """
    # EC 2015 is a leap year, so EC 2016 starts a day later in September …
    assert cal.ethiopian_to_gregorian(2015, 1, 1) == date(2022, 9, 11)
    assert cal.ethiopian_to_gregorian(2016, 1, 1) == date(2023, 9, 12)
    # … and February 2024 has 29 days, so Hamle 1 is 8 July in both.
    assert cal.ethiopian_to_gregorian(2015, 11, 1) == date(2023, 7, 8)
    assert cal.ethiopian_to_gregorian(2016, 11, 1) == date(2024, 7, 8)


@pytest.mark.parametrize(
    "gregorian,offset",
    [
        (date(2025, 1, 1), 8),
        (date(2025, 9, 10), 8),  # last day of EC 2017
        (date(2025, 9, 11), 7),  # Meskerem 1, EC 2018 — the flip
        (date(2025, 12, 31), 7),
        (date(2024, 9, 10), 8),
        (date(2024, 9, 11), 7),
        (date(2023, 9, 11), 8),  # Pagume 6 year: the flip is a day later
        (date(2023, 9, 12), 7),
    ],
)
def test_gregorian_year_offset_flips_at_the_new_year(gregorian, offset):
    """The Ethiopian year runs 7 behind for part of the Gregorian year and 8
    behind for the rest. Getting this wrong is a whole-year error."""
    result = cal.gregorian_to_ethiopian(gregorian)
    assert gregorian.year - result.year == offset


# ===========================================================================
# 7. ONE DATE IN EACH OF A LEAP AND A NON-LEAP YEAR, both directions
# ===========================================================================


@pytest.mark.parametrize(
    "gregorian,ethiopian",
    [
        # EC 2015 — a leap year (2015 % 4 == 3)
        (date(2022, 9, 11), (2015, 1, 1)),
        (date(2023, 1, 9), (2015, 5, 1)),
        (date(2023, 5, 9), (2015, 9, 1)),
        (date(2023, 9, 11), (2015, 13, 6)),
        # EC 2017 — a common year
        (date(2024, 9, 11), (2017, 1, 1)),
        (date(2025, 1, 9), (2017, 5, 1)),
        (date(2025, 5, 9), (2017, 9, 1)),
        (date(2025, 9, 10), (2017, 13, 5)),
    ],
)
def test_both_directions(gregorian, ethiopian):
    result = cal.gregorian_to_ethiopian(gregorian)
    assert (result.year, result.month, result.day) == ethiopian
    assert cal.ethiopian_to_gregorian(*ethiopian) == gregorian


def test_round_trip_over_a_century_of_every_single_day():
    """The property, not a sample: every day of EC 1990–2090 survives a round
    trip. 36,900-odd days, which is where the Pagume-6 bug was actually
    caught — no hand-written golden would have found it."""
    checked = 0
    for year in range(1990, 2091):
        for month in range(1, 14):
            for day in range(1, cal.days_in_month(year, month) + 1):
                gregorian = cal.ethiopian_to_gregorian(year, month, day)
                back = cal.gregorian_to_ethiopian(gregorian)
                assert (back.year, back.month, back.day) == (year, month, day)
                checked += 1
    assert checked > 36_000, "only %d days checked — the loop is not running" % checked


def test_consecutive_gregorian_days_map_to_consecutive_ethiopian_days():
    """No gaps and no repeats across a leap boundary — the other way a
    conversion goes wrong by one."""
    day = date(2023, 8, 1)
    previous = cal.gregorian_to_ethiopian(day)
    for _ in range(400):
        day = date.fromordinal(day.toordinal() + 1)
        current = cal.gregorian_to_ethiopian(day)
        assert current > previous, "%s -> %s did not advance" % (day, current)
        previous = current


# ===========================================================================
# 8. TOTAL FUNCTIONS: invalid input RAISES, never returns something plausible
# ===========================================================================


@pytest.mark.parametrize(
    "args",
    [
        (2017, 0, 1),  # month 0
        (2017, 14, 1),  # month 14
        (2017, 1, 0),  # day 0
        (2017, 1, 31),  # no month has 31 days
        (2017, 13, 6),  # Pagume 6 in a common year
        (2017, 13, 7),  # Pagume 7 never
        (0, 1, 1),  # year 0
        (-5, 1, 1),
    ],
)
def test_invalid_ethiopian_dates_raise(args):
    with pytest.raises(ValueError):
        cal.ethiopian_to_gregorian(*args)


@pytest.mark.parametrize("bad", ["2025-07-08", 20250708, None, 3.5])
def test_non_date_input_raises_type_error(bad):
    with pytest.raises(TypeError):
        cal.gregorian_to_ethiopian(bad)


@pytest.mark.parametrize("args", [(2017, True, 1), (2017, 1, True), (True, 1, 1)])
def test_bool_is_not_an_int_here(args):
    """True would silently mean 1. A calendar must not accept that."""
    with pytest.raises(TypeError):
        cal.ethiopian_to_gregorian(*args)


def test_datetime_is_accepted_and_its_time_discarded():
    """A datetime IS a date; the Ethiopian day boundary is not midnight, but
    every value this system stores is a calendar date, so inventing a dawn
    offset would invent precision."""
    assert cal.gregorian_to_ethiopian(datetime(2025, 7, 8, 23, 59, 59)) == cal.EthiopianDate(
        2017, 11, 1
    )


def test_dates_before_the_epoch_raise_rather_than_extrapolate():
    with pytest.raises(ValueError, match="precedes the Ethiopian epoch"):
        cal.gregorian_to_ethiopian(date(1, 1, 1))


def test_error_messages_name_the_actual_problem():
    """An error a user can act on, not 'invalid date'."""
    with pytest.raises(ValueError) as caught:
        cal.ethiopian_to_gregorian(2017, 13, 6)
    message = str(caught.value)
    assert "Pagume" in message and "5 days" in message and "2017" in message


# ===========================================================================
# 9. MONTH NAMES AS DATA
# ===========================================================================


def test_thirteen_months_in_both_scripts():
    assert len(cal.MONTHS) == 13
    assert len(cal.MONTHS_LATIN) == 13
    assert len(cal.MONTHS_AMHARIC) == 13
    assert cal.MONTHS_LATIN[0] == "Meskerem"
    assert cal.MONTHS_LATIN[12] == "Pagume"
    assert cal.MONTHS_AMHARIC[0] == "መስከረም"
    assert cal.MONTHS_AMHARIC[12] == "ጳጉሜን"


def test_every_amharic_name_is_actually_ethiopic_script():
    """A Latin string left in the Amharic column would render as English on an
    Amharic invoice and nobody would notice until a client did."""
    for latin, amharic in cal.MONTHS:
        assert all("ሀ" <= ch <= "፿" for ch in amharic), "%s: %r is not Ethiopic script" % (
            latin,
            amharic,
        )
        assert amharic != latin


def test_month_name_lookup_and_its_bounds():
    assert cal.month_name(11) == "Hamle"
    assert cal.month_name(11, amharic=True) == "ሐምሌ"
    assert cal.month_name(13) == "Pagume"
    for bad in (0, 14, -1):
        with pytest.raises(ValueError):
            cal.month_name(bad)


def test_the_library_ships_no_english_month_names():
    """Data in two scripts, translated at the Odoo layer. A hardcoded English
    name in a localisation library is a translation that can never be fixed."""
    joined = " ".join(cal.MONTHS_LATIN)
    for english in ("January", "February", "September", "July"):
        assert english not in joined


# ===========================================================================
# 10. THE VALUE OBJECT
# ===========================================================================


def test_ethiopian_date_is_immutable_ordered_and_readable():
    value = cal.EthiopianDate(2017, 11, 1)
    assert str(value) == "Hamle 1, 2017"
    assert value.month_latin == "Hamle"
    assert value.month_amharic == "ሐምሌ"
    assert value.is_pagume is False
    assert cal.EthiopianDate(2017, 13, 5).is_pagume is True
    assert cal.EthiopianDate(2017, 1, 1) < cal.EthiopianDate(2017, 1, 2)
    assert cal.EthiopianDate(2016, 13, 5) < cal.EthiopianDate(2017, 1, 1)
    with pytest.raises(Exception):
        value.day = 2


def test_constructing_an_impossible_value_object_raises():
    with pytest.raises(ValueError):
        cal.EthiopianDate(2016, 13, 6)
