# -*- coding: utf-8 -*-
"""Fast golden tests for the pharma reference calculator (no Odoo).

Loads the pure-Python module by file path so it runs standalone under
`pytest tests_fast/`. Every expected value is hand-computed from the GS1
General Specifications (AIs 01/17/10/21, day-00 = month end) and the DAT
proposal's 90-day ("3 months") expiry-alert horizon.
"""

import importlib.util
import os
import sys as _sys
from datetime import date

import pytest

_CALC = os.path.join(
    os.path.dirname(__file__), "..", "addons", "vertical_pharma", "reference", "pharma_calc.py"
)
_spec = importlib.util.spec_from_file_location("pharma_calc", _CALC)
calc = importlib.util.module_from_spec(_spec)
_sys.modules[_spec.name] = calc
_spec.loader.exec_module(calc)

GS = "\x1d"


# --------------------------------------------------------------------------------------
# Expiry-alert engine
# --------------------------------------------------------------------------------------
def test_alert_start_golden():
    """Kickoff golden: 2026-09-25 expiry, 90-day horizon → alerts from 2026-06-27."""
    assert calc.alert_start_date(date(2026, 9, 25), 90) == date(2026, 6, 27)


def test_state_fresh_before_horizon():
    """The day BEFORE the alert window the lot is still fresh."""
    assert calc.expiry_state(date(2026, 9, 25), date(2026, 6, 26), 90) == "fresh"


def test_state_nearing_from_horizon_start_inclusive():
    assert calc.expiry_state(date(2026, 9, 25), date(2026, 6, 27), 90) == "nearing_expiry"


def test_state_nearing_on_expiry_day():
    """The expiry date itself is the last usable day."""
    assert calc.expiry_state(date(2026, 9, 25), date(2026, 9, 25), 90) == "nearing_expiry"


def test_state_expired_day_after():
    assert calc.expiry_state(date(2026, 9, 25), date(2026, 9, 26), 90) == "expired"


def test_state_respects_custom_horizon():
    """A 30-day horizon must not alert at 89 days out."""
    assert calc.expiry_state(date(2026, 9, 25), date(2026, 6, 28), 30) == "fresh"
    assert calc.expiry_state(date(2026, 9, 25), date(2026, 8, 26), 30) == "nearing_expiry"


def test_state_none_expiry_is_fresh():
    """Discipline is enforced at receipt; the engine tolerates missing dates."""
    assert calc.expiry_state(None, date(2026, 7, 5), 90) == "fresh"


# --------------------------------------------------------------------------------------
# GS1 DataMatrix parsing
# --------------------------------------------------------------------------------------
def test_gs1_golden_gtin_expiry_batch():
    """Kickoff golden: 01<gtin>17<yymmdd>10<batch>."""
    result = calc.parse_gs1_datamatrix("0109501101530003172609251" + "0B-123")
    assert result.gtin == "09501101530003"
    assert result.expiry == date(2026, 9, 25)
    assert result.batch == "B-123"
    assert result.serial == ""


def test_gs1_with_serial_and_gs_separators():
    """Variable-length batch terminated by GS, then a serial."""
    scan = "010950110153000310B-123" + GS + "17260925" + "21SN0001"
    result = calc.parse_gs1_datamatrix(scan)
    assert result.gtin == "09501101530003"
    assert result.batch == "B-123"
    assert result.expiry == date(2026, 9, 25)
    assert result.serial == "SN0001"


def test_gs1_symbology_prefix_tolerated():
    result = calc.parse_gs1_datamatrix("]d20109501101530003" + "10B-9")
    assert result.gtin == "09501101530003"
    assert result.batch == "B-9"


def test_gs1_day_zero_means_month_end():
    """GS1 rule: expiry day '00' → last day of the month."""
    result = calc.parse_gs1_datamatrix("0109501101530003" + "17260200" + "10L1")
    assert result.expiry == date(2026, 2, 28)


def test_gs1_malformed_rejected():
    """Mis-scans must never silently create a wrong lot."""
    with pytest.raises(ValueError):
        calc.parse_gs1_datamatrix("990600123")  # unknown AI
    with pytest.raises(ValueError):
        calc.parse_gs1_datamatrix("01123")  # truncated GTIN
    with pytest.raises(ValueError):
        calc.parse_gs1_datamatrix("0109501101530003" + "17261325" + "10L1")  # month 13
    with pytest.raises(ValueError):
        calc.parse_gs1_datamatrix("")  # empty
    with pytest.raises(ValueError):
        calc.parse_gs1_datamatrix("01ABCDEFGHIJKLMN" + "10L1")  # non-digit GTIN
