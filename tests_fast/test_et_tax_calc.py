# -*- coding: utf-8 -*-
"""Fast golden-value tests for the Ethiopian transaction-tax calculators (no Odoo).

Loads the pure-Python calculator by file path so it runs standalone under
`pytest tests_fast/`. Every expected number is hand-computed from the Aug-2025 WHT
rules (3% goods > 20,000 / services > 10,000; 30% punitive when TIN/licence missing;
15% foreign digital) and the Proc 1395/2025 daily cash cap (ETB 30,000 per party).
"""

import importlib.util
import os
import sys as _sys

import pytest

_CALC = os.path.join(
    os.path.dirname(__file__), "..", "addons", "l10n_et_base", "reference", "et_tax_calc.py"
)
_spec = importlib.util.spec_from_file_location("et_tax_calc", _CALC)
calc = importlib.util.module_from_spec(_spec)
_sys.modules[_spec.name] = calc
_spec.loader.exec_module(calc)


# --------------------------------------------------------------------------------------
# Withholding tax — standard 3% domestic path
# --------------------------------------------------------------------------------------
def test_wht_goods_50000_with_tin_is_1500():
    """Spec worked example: goods, ETB 50,000, compliant supplier → 3% = 1,500."""
    r = calc.compute_wht(50000, kind="goods", has_tin=True, has_licence=True)
    assert r.applicable is True
    assert r.rate == 0.03
    assert r.amount == 1500.0


def test_wht_goods_25000_with_tin_is_750():
    r = calc.compute_wht(25000, kind="goods", has_tin=True, has_licence=True)
    assert (r.applicable, r.amount) == (True, 750.0)


def test_wht_goods_exactly_20000_is_not_applicable():
    """Threshold is exclusive: exactly 20,000 attracts no WHT."""
    r = calc.compute_wht(20000, kind="goods", has_tin=True, has_licence=True)
    assert r.applicable is False and r.amount == 0.0


def test_wht_goods_just_over_threshold_applies():
    r = calc.compute_wht(20000.01, kind="goods", has_tin=True, has_licence=True)
    assert r.applicable is True and r.amount == 600.0  # 20000.01 * 0.03 = 600.0003 → 600.00


def test_wht_service_15000_with_tin_is_450():
    r = calc.compute_wht(15000, kind="service", has_tin=True, has_licence=True)
    assert (r.applicable, r.amount) == (True, 450.0)


def test_wht_service_exactly_10000_is_not_applicable():
    r = calc.compute_wht(10000, kind="service", has_tin=True, has_licence=True)
    assert r.applicable is False and r.amount == 0.0


def test_wht_service_just_over_threshold_applies():
    r = calc.compute_wht(10000.01, kind="service", has_tin=True, has_licence=True)
    assert r.applicable is True and r.amount == 300.0  # 10000.01 * 0.03 = 300.0003 → 300.00


# --------------------------------------------------------------------------------------
# Withholding tax — punitive 30% (missing TIN and/or licence)
# --------------------------------------------------------------------------------------
def test_wht_goods_50000_no_tin_is_punitive_15000():
    r = calc.compute_wht(50000, kind="goods", has_tin=False, has_licence=True)
    assert (r.applicable, r.rate, r.amount) == (True, 0.30, 15000.0)


def test_wht_goods_50000_no_tin_no_licence_is_punitive_15000():
    """Spec headline case: supplier lacks BOTH TIN and licence → 30% of 50,000 = 15,000."""
    r = calc.compute_wht(50000, kind="goods", has_tin=False, has_licence=False)
    assert (r.applicable, r.rate, r.amount) == (True, 0.30, 15000.0)


def test_wht_service_15000_no_licence_is_punitive_4500():
    """Missing a valid business licence alone also triggers the punitive rate."""
    r = calc.compute_wht(15000, kind="service", has_tin=True, has_licence=False)
    assert (r.applicable, r.rate, r.amount) == (True, 0.30, 4500.0)


def test_wht_goods_below_threshold_no_tin_still_not_applicable():
    """Punitive rate is gated by the same threshold BY DEFAULT: 5,000 goods → no WHT
    even with no TIN (punitive_respects_thresholds defaults to True)."""
    r = calc.compute_wht(5000, kind="goods", has_tin=False, has_licence=False)
    assert r.applicable is False and r.amount == 0.0


def test_wht_punitive_gating_flag_true_below_threshold_no_wht():
    """Explicit flag=True: 5,000 goods, no TIN → exempt (current Aug-2025 reading)."""
    r = calc.compute_wht(5000, kind="goods", has_tin=False, punitive_respects_thresholds=True)
    assert r.applicable is False and r.amount == 0.0


def test_wht_punitive_gating_flag_false_below_threshold_is_30pct():
    """Ungated reading (Proc 979/2016 art. 92 predecessor rule): flag=False →
    punitive 30% applies below the threshold: 5,000 goods, no TIN → 1,500."""
    r = calc.compute_wht(5000, kind="goods", has_tin=False, punitive_respects_thresholds=False)
    assert (r.applicable, r.rate, r.amount) == (True, 0.30, 1500.0)


def test_wht_punitive_gating_flag_false_service_no_licence_is_30pct():
    """Ungated reading also applies per-kind: 8,000 service, no licence → 2,400."""
    r = calc.compute_wht(
        8000, kind="service", has_licence=False, punitive_respects_thresholds=False
    )
    assert (r.applicable, r.rate, r.amount) == (True, 0.30, 2400.0)


def test_wht_punitive_gating_flag_false_never_lifts_threshold_for_compliant():
    """flag=False only affects NON-compliant suppliers: 5,000 goods with TIN and
    licence stays exempt."""
    r = calc.compute_wht(
        5000,
        kind="goods",
        has_tin=True,
        has_licence=True,
        punitive_respects_thresholds=False,
    )
    assert r.applicable is False and r.amount == 0.0


# --------------------------------------------------------------------------------------
# Withholding tax — foreign digital services (15%, no domestic threshold)
# --------------------------------------------------------------------------------------
def test_wht_foreign_digital_8000_applies_below_service_threshold():
    r = calc.compute_wht(8000, kind="foreign_digital", has_tin=False, has_licence=False)
    assert (r.applicable, r.rate, r.amount) == (True, 0.15, 1200.0)


def test_wht_foreign_digital_100000_is_15000():
    r = calc.compute_wht(100000, kind="foreign_digital")
    assert r.amount == 15000.0


# --------------------------------------------------------------------------------------
# Withholding tax — edge cases
# --------------------------------------------------------------------------------------
def test_wht_zero_base_not_applicable():
    assert calc.compute_wht(0, kind="goods").applicable is False


def test_wht_negative_base_not_applicable():
    assert calc.compute_wht(-100, kind="service").applicable is False


def test_wht_unknown_kind_raises():
    with pytest.raises(ValueError):
        calc.compute_wht(50000, kind="banana")


def test_wht_float_dust_sum_at_threshold_not_applicable():
    """Line subtotals summing decimally to exactly 20,000.00 accumulate float dust
    (e.g. sum([2342.01, 640.91, 17017.08]) == 20000.000000000004 on Python 3.12).
    The dusty literal is pinned directly so the test is summation-order independent."""
    base = 20000.000000000004
    assert base > 20000.0  # the dust is real, this input exercises the rounding guard
    r = calc.compute_wht(base, kind="goods")
    assert r.applicable is False and r.amount == 0.0


def test_wht_non_finite_base_raises():
    """NaN compares False everywhere and would silently produce a NaN move line."""
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            calc.compute_wht(bad, kind="goods")


def test_wht_large_amount_rounds_half_up():
    """999,999,999.50 × 3% = 29,999,999.985 → half-up 29,999,999.99 (Odoo HALF-UP
    semantics; a naive float round() gives .98 at this magnitude)."""
    r = calc.compute_wht(999999999.50, kind="goods")
    assert r.amount == 29999999.99


def test_wht_respects_overridden_config():
    """Odoo passes effective-dated config; a future 2%/25,000 rule must be honoured."""
    r = calc.compute_wht(30000, kind="goods", rate_standard=0.02, threshold_goods=25000)
    assert (r.applicable, r.rate, r.amount) == (True, 0.02, 600.0)


def test_wht_goods_threshold_override_pins_below_new_threshold():
    """22,000 is above the default 20,000 but below an overridden 25,000 threshold →
    NOT applicable. Kills a mutant that ignores threshold_goods and keeps the default
    (mutation-testing finding: the test above alone cannot distinguish them)."""
    r = calc.compute_wht(22000, kind="goods", threshold_goods=25000)
    assert r.applicable is False and r.amount == 0.0


def test_wht_service_threshold_override_honoured():
    """12,000 service with the threshold raised to 15,000 → not applicable."""
    r = calc.compute_wht(12000, kind="service", threshold_service=15000)
    assert r.applicable is False and r.amount == 0.0


def test_wht_foreign_digital_rate_override_honoured():
    """A future foreign-digital rate change must flow through config: 10% of 10,000 = 1,000."""
    r = calc.compute_wht(10000, kind="foreign_digital", rate_foreign_digital=0.10)
    assert (r.applicable, r.rate, r.amount) == (True, 0.10, 1000.0)


def test_wht_punitive_rate_override_honoured():
    """A future punitive-rate change must flow through config, not code."""
    r = calc.compute_wht(50000, kind="goods", has_tin=False, rate_punitive=0.35)
    assert (r.rate, r.amount) == (0.35, 17500.0)


def test_wht_service_200000_with_tin_is_6000():
    """Larger golden value: services, ETB 200,000, compliant supplier → 3% = 6,000."""
    r = calc.compute_wht(200000, kind="service", has_tin=True, has_licence=True)
    assert (r.applicable, r.rate, r.amount) == (True, 0.03, 6000.0)


# --------------------------------------------------------------------------------------
# Cash-payment cap (Art. 81, Proc 1395/2025 — 50,000 ETB, verified Jul 2026)
# --------------------------------------------------------------------------------------
def test_cash_cap_exactly_50000_allowed():
    r = calc.check_cash_cap(50000, prior_cash_today=0)
    assert r.exceeded is False and r.total_day == 50000.0 and r.excess == 0.0


def test_cash_cap_just_over_flags():
    r = calc.check_cash_cap(50000.01, prior_cash_today=0)
    assert r.exceeded is True and r.excess == 0.01


def test_cash_cap_single_transaction_over_cap_flags():
    """Art. 81 caps the SINGLE transaction too — covered by the aggregate check
    with zero prior payments: one 60,000 cash payment → flagged, 10,000 over."""
    r = calc.check_cash_cap(60000, prior_cash_today=0)
    assert r.exceeded is True and r.total_day == 60000.0 and r.excess == 10000.0


def test_cash_cap_accumulates_across_day():
    """30,000 already paid today + a new 25,000 → 55,000 total → flagged, 5,000 over."""
    r = calc.check_cash_cap(25000, prior_cash_today=30000)
    assert r.exceeded is True and r.total_day == 55000.0 and r.excess == 5000.0


def test_cash_cap_small_payment_ok():
    r = calc.check_cash_cap(10000, prior_cash_today=0)
    assert r.exceeded is False and r.excess == 0.0


def test_cash_cap_respects_overridden_cap():
    r = calc.check_cash_cap(60000, prior_cash_today=0, cap=100000)
    assert r.exceeded is False and r.total_day == 60000.0


def test_cash_cap_accumulated_exactly_at_cap_allowed():
    """30,000 earlier + 20,000 now = exactly 50,000 → still allowed."""
    r = calc.check_cash_cap(20000, prior_cash_today=30000)
    assert r.exceeded is False and r.total_day == 50000.0 and r.excess == 0.0


def test_cash_cap_non_finite_raises():
    """A NaN amount must fail loudly, not report as within-cap (fail-open)."""
    with pytest.raises(ValueError):
        calc.check_cash_cap(float("nan"))
    with pytest.raises(ValueError):
        calc.check_cash_cap(1000, prior_cash_today=float("inf"))


# --------------------------------------------------------------------------------------
# TIN format validation (10-digit MoR format; no public checksum — format-only)
# --------------------------------------------------------------------------------------
def test_tin_plain_10_digits_valid():
    r = calc.validate_tin("0012345678")
    assert r.valid is True and r.normalized == "0012345678"


def test_tin_with_hyphens_normalized():
    """Display format XXXX-XXXX-XX must normalize to bare digits."""
    r = calc.validate_tin("0012-3456-78")
    assert r.valid is True and r.normalized == "0012345678"


def test_tin_with_spaces_normalized():
    r = calc.validate_tin(" 00 1234 5678 ")
    assert r.valid is True and r.normalized == "0012345678"


def test_tin_nine_digits_invalid():
    assert calc.validate_tin("123456789").valid is False


def test_tin_eleven_digits_invalid():
    assert calc.validate_tin("12345678901").valid is False


def test_tin_with_letters_invalid():
    assert calc.validate_tin("00123A5678").valid is False


def test_tin_empty_and_none_invalid():
    assert calc.validate_tin("").valid is False
    assert calc.validate_tin(None).valid is False
    assert calc.validate_tin("   ").valid is False


def test_tin_all_same_digit_placeholder_invalid():
    """0000000000 (and friends) are dirty-import placeholders, not real TINs."""
    assert calc.validate_tin("0000000000").valid is False
    assert calc.validate_tin("9999999999").valid is False


def test_tin_unicode_digits_rejected():
    """str.isdigit() alone accepts Arabic-Indic / superscript / Ethiopic numerals;
    those must NOT validate — MoR records use ASCII 0-9 only."""
    arabic_indic = "١٢٣٤٥٦٧٨٩٠"  # Arabic-Indic 1234567890
    assert calc.validate_tin(arabic_indic).valid is False
    assert calc.validate_tin("12345678²³").valid is False  # 8 digits + ²³


# --------------------------------------------------------------------------------------
# CSV formula-injection neutralization (R2#4)
# --------------------------------------------------------------------------------------
def test_csv_safe_cell_neutralizes_formula_prefixes():
    for danger in ("=WEBSERVICE(1)", "+SUM(A1)", "-2+3", "@SUM(A1)", "\ttab", "\rcr"):
        out = calc.csv_safe_cell(danger)
        assert out.startswith("'"), danger
        assert out[1:] == danger


def test_csv_safe_cell_leaves_numbers_and_text():
    # Legitimate negative numbers must NOT be quoted (they are not formulas).
    assert calc.csv_safe_cell("-9450.00") == "-9450.00"
    assert calc.csv_safe_cell("-2,850.00") == "-2,850.00"
    assert calc.csv_safe_cell("Awash Agro Industry PLC") == "Awash Agro Industry PLC"
    assert calc.csv_safe_cell("0011223344") == "0011223344"
    assert calc.csv_safe_cell(None) == ""
    assert calc.csv_safe_cell(1234.5) == "1234.5"
