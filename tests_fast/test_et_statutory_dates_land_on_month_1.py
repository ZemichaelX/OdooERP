# -*- coding: utf-8 -*-
"""Every Ethiopian statutory effective date this project ships must land on the
1st of an Ethiopian month.

WHY THIS IS A CHECKABLE PROPERTY AND NOT AN OPINION
---------------------------------------------------
Ethiopian tax law commences on Ethiopian calendar boundaries. Every effective
date this project has verified independently against a proclamation lands on
day 1 of an Ethiopian month:

    8 July 2025  = Hamle 1, 2017 EC   PAYE, Proc. 1395/2025
    8 July 2016  = Hamle 1, 2008 EC   PAYE, Proc. 979/2016
    8 July 2014  = Hamle 1, 2006 EC   pension 7%/11%
    7 August 2025 = Nehase 1, 2017 EC domestic WHT (knowledge base)

A seeded date that falls mid-Ethiopian-month is therefore strong evidence that
somebody wrote a Gregorian round number — the 1st of a Gregorian month — where a
proclamation gave an Ethiopian one. That is a transcription failure, and until
this file existed nothing checked for it.

It is not proof. A proclamation may commence mid-month, and this test does not
override a gazette. What it does is make the anomaly LOUD and DATED instead of
sitting in a comment nobody re-reads.

WHAT IT FOUND
-------------
Two seeds fail, and only one of them was known:

  * l10n_et_base WHT seed, date(2025, 8, 1) -> Hamle 25, 2017 EC. Already
    flagged in that module's comments as an open discrepancy against the
    knowledge base's 7 August 2025.

  * l10n_et_base CASH CAP seed, date(2025, 7, 1) -> Sene 24, 2017 EC. NOT
    previously flagged anywhere. Same proclamation as the PAYE bands
    (1395/2025), whose own commencement is 8 July 2025 = Hamle 1. Found by
    this test on its first run.

Both are marked xfail(strict=True), so:
  - the failure is visible in every run rather than silent;
  - if somebody corrects a seed, the xfail turns into an UNEXPECTED PASS and
    fails the build, forcing the marker to be removed with the fix. An xfail
    that quietly starts passing is how a resolved question gets forgotten.

NOTHING HERE CHANGES A SEED. The proclamation is the authority; a calendar
library agreeing with a knowledge base is corroboration, not a primary source.
"""

import importlib.util
import os
import re
import sys as _sys
from datetime import date

import pytest

_HERE = os.path.dirname(__file__)
_CAL = os.path.join(_HERE, "..", "addons", "l10n_et_calendar", "reference", "et_calendar.py")
_spec = importlib.util.spec_from_file_location("et_calendar", _CAL)
cal = importlib.util.module_from_spec(_spec)
_sys.modules[_spec.name] = cal
_spec.loader.exec_module(cal)


def _addon(*parts):
    return os.path.join(_HERE, "..", "addons", *parts)


# Every Ethiopian statutory effective date the project ships, enumerated
# explicitly. Adding a new effective-dated config means adding a row here — the
# next test asserts the literal is really in the file, so a row cannot rot into
# a date the code no longer uses.
#
# (label, gregorian date, source file, the literal as it appears in that file)
STATUTORY_DATES = [
    (
        "PAYE bands — Income Tax (Amendment) Proclamation 1395/2025",
        date(2025, 7, 8),
        _addon("l10n_et_payroll", "reference", "et_payroll_calc.py"),
        "date(2025, 7, 8)",
    ),
    (
        "PAYE bands — Federal Income Tax Proclamation 979/2016",
        date(2016, 7, 8),
        _addon("l10n_et_payroll", "reference", "et_payroll_calc.py"),
        "date(2016, 7, 8)",
    ),
    (
        "pension 7%/11% employee/employer split",
        date(2014, 7, 8),
        _addon("l10n_et_payroll", "models", "pension_config.py"),
        "date(2014, 7, 8)",
    ),
    (
        "cash cap Art. 81 — Proclamation 1395/2025",
        date(2025, 7, 1),
        _addon("l10n_et_base", "models", "l10n_et_cash_cap_config.py"),
        "date(2025, 7, 1)",
    ),
    (
        "domestic WHT rates — the seeded value",
        date(2025, 8, 1),
        _addon("l10n_et_base", "models", "l10n_et_wht_config.py"),
        "date(2025, 8, 1)",
    ),
    (
        "social welfare levy — Council of Ministers Regulation 519/2022",
        date(2022, 8, 6),
        _addon("l10n_et_base", "models", "l10n_et_social_welfare_levy_config.py"),
        "date(2022, 8, 6)",
    ),
]

# THE OPEN QUESTIONS, keyed by the seed literal. Kept separate from the data so
# the exemption applies ONLY to the day-1 assertion: the enumeration-still-
# matches-the-source check below must run unmarked for these rows too, or a
# silently corrected seed would keep its exemption and nobody would notice.
#
# strict=True on every one: when a seed is fixed, the xfail becomes an
# UNEXPECTED PASS and fails the build, which forces the marker to be deleted
# alongside the fix. An xfail that quietly starts passing is how a resolved
# question gets forgotten.
OPEN_DISCREPANCIES = {
    "date(2025, 7, 1)": (
        "1 July 2025 is Sene 24, 2017 EC — mid-Ethiopian-month. UNRESOLVED and "
        "NOT previously flagged anywhere: this is the same proclamation as the "
        "PAYE bands (1395/2025), whose own commencement is 8 July 2025 = "
        "Hamle 1. A Gregorian 1st where an Ethiopian 1st was expected. Needs "
        "the Negarit Gazeta, not arithmetic. Found 2026-08-14 by this test on "
        "its first run."
    ),
    "date(2022, 8, 6)": (
        "6 August 2022 is Hamle 30, 2014 EC — the LAST day of an Ethiopian "
        "month, one day before Nehase 1 (7 August 2022). Regulation 519/2022 "
        "states 6 August 2022 as the commencement date and it was gazetted on "
        "22 August 2022, so unlike the two seeds below this is not obviously a "
        "transcription error — a regulation may commence mid-month, and this "
        "test does not override a gazette. It is enumerated and left visible "
        "because the pattern is striking: this date and the WHT seed are both "
        "within a day of a Nehase 1. Needs the Negarit Gazeta text, which could "
        "not be retrieved in the environment this was written in. "
        "Flagged 2026-08-14 when the levy was implemented."
    ),
    "date(2025, 8, 1)": (
        "1 August 2025 is Hamle 25, 2017 EC — mid-Ethiopian-month. The "
        "knowledge base records the domestic WHT change as 7 August 2025 = "
        "Nehase 1, 2017 EC, which does land on day 1. Open since the "
        "l10n_et_base WHT work; see the OPEN DISCREPANCY comment in "
        "l10n_et_wht_config.py. Needs the Negarit Gazeta. Flagged 2026-08-14."
    ),
}

_DAY_1_CASES = [
    pytest.param(
        *row,
        marks=(
            pytest.mark.xfail(strict=True, reason=OPEN_DISCREPANCIES[row[3]])
            if row[3] in OPEN_DISCREPANCIES
            else ()
        ),
    )
    for row in STATUTORY_DATES
]


@pytest.mark.parametrize("label,gregorian,source_file,literal", _DAY_1_CASES)
def test_statutory_effective_date_lands_on_day_1(label, gregorian, source_file, literal):
    """The property. A mid-month date fails and says exactly what it is."""
    ethiopian = cal.gregorian_to_ethiopian(gregorian)
    assert ethiopian.day == 1, (
        "%s is seeded at %s, which is %s — day %d of an Ethiopian month, not the "
        "1st. Every Ethiopian effective date this project has verified against a "
        "proclamation lands on day 1, so this is probably a Gregorian round "
        "number written where an Ethiopian boundary belongs. Source: %s"
        % (
            label,
            gregorian,
            ethiopian,
            ethiopian.day,
            os.path.relpath(source_file, os.path.join(_HERE, "..")),
        )
    )


@pytest.mark.parametrize("label,gregorian,source_file,literal", STATUTORY_DATES)
def test_the_enumeration_still_matches_the_source(label, gregorian, source_file, literal):
    """A list of dates that has drifted from the code checks nothing.

    Runs for the xfail rows too — a seed that was silently CHANGED must not
    keep its exemption. This asserts the literal is still in the file; it is a
    text check on purpose, because tests_fast may not import Odoo.
    """
    with open(source_file, encoding="utf-8") as handle:
        text = handle.read()
    assert literal in text, (
        "%s: the literal %s is no longer in %s. Either the seed changed — in "
        "which case update this enumeration AND remove any xfail marker — or "
        "the file moved."
        % (label, literal, os.path.relpath(source_file, os.path.join(_HERE, "..")))
    )


def test_the_known_good_dates_are_all_hamle_1_or_nehase_1():
    """The positive side, spelled out: this is what a verified date looks like."""
    assert str(cal.gregorian_to_ethiopian(date(2025, 7, 8))) == "Hamle 1, 2017"
    assert str(cal.gregorian_to_ethiopian(date(2016, 7, 8))) == "Hamle 1, 2008"
    assert str(cal.gregorian_to_ethiopian(date(2014, 7, 8))) == "Hamle 1, 2006"
    assert str(cal.gregorian_to_ethiopian(date(2025, 8, 7))) == "Nehase 1, 2017"


def test_the_guard_discriminates():
    """Prove the check can go red, by handing it a date that should fail.

    Without this, a `day == 1` assertion that was accidentally always true —
    say because the converter returned day 1 for everything — would look
    identical to a working guard.
    """
    mid_month = cal.gregorian_to_ethiopian(date(2025, 8, 1))
    assert mid_month.day != 1, "the converter is returning day 1 for a mid-month date"
    assert str(mid_month) == "Hamle 25, 2017"
    # and the two ends of a month, so "day 1" is not simply the common case
    assert cal.gregorian_to_ethiopian(date(2025, 8, 6)).day == 30
    assert cal.gregorian_to_ethiopian(date(2025, 8, 7)).day == 1


def test_no_shipped_effective_date_escapes_this_file():
    """The enumeration must keep up with the code.

    Greps the addons for `effective_from` seed literals and asserts every one
    is accounted for here. Without this, the next effective-dated config gets
    added, is never listed above, and this whole file quietly stops covering
    anything — the same shape as a guard that runs in the one mode where it
    cannot fire.
    """
    addons = os.path.join(_HERE, "..", "addons")
    listed = {literal for _label, _gregorian, _path, literal in STATUTORY_DATES}
    pattern = re.compile(r'"effective_from":\s*(date\(\s*\d{4},\s*\d{1,2},\s*\d{1,2}\s*\))')
    found = {}
    for root, _dirs, files in os.walk(addons):
        if os.sep + "tests" in root or os.sep + "migrations" in root:
            continue
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as handle:
                for literal in pattern.findall(handle.read()):
                    found[literal] = os.path.relpath(path, os.path.join(_HERE, ".."))
    missing = {lit: where for lit, where in found.items() if lit not in listed}
    assert not missing, (
        "These seeded effective_from dates are not enumerated in "
        "STATUTORY_DATES, so nothing checks whether they land on an Ethiopian "
        "month boundary: %s" % missing
    )
