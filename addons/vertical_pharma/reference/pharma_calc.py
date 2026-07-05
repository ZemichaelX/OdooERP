# -*- coding: utf-8 -*-
"""Pure-Python pharma compliance logic (no Odoo dependency).

Single source of truth for two pieces of vertical_pharma logic, fast-tested in
``tests_fast/`` (CLAUDE.md rule #10):

1. GS1 DataMatrix scan-string parsing (EFDA traceability: GTIN + expiry +
   batch + serial via application identifiers 01/17/10/21).
2. The expiry-alert engine: alert window start and lot escalation state
   (fresh → nearing_expiry → expired) for a configurable horizon (default 90
   days — the DAT proposal's "automatic alerts 3 months before expiry").

Conventions (documented decisions):
- A lot is 'nearing_expiry' from exactly ``expiry − horizon`` (inclusive): a
  2026-09-25 expiry with a 90-day horizon starts alerting on 2026-06-27.
- The expiry date itself is the LAST usable day: 'expired' starts the day
  after (industry "EXP" convention).
- GS1 expiry day "00" means end-of-month (GS1 General Specifications §3.4.2).
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta

DEFAULT_ALERT_HORIZON_DAYS = 90  # "3 months" per the DAT proposal

STATE_FRESH = "fresh"
STATE_NEARING = "nearing_expiry"
STATE_EXPIRED = "expired"

# Group separator: terminates variable-length GS1 fields.
GS = "\x1d"
# Symbology identifier some scanners prefix to DataMatrix payloads.
SYMBOLOGY_PREFIX = "]d2"

# Application identifiers we understand: AI -> (length, fixed?)
_AI_FIXED = {"01": 14, "17": 6}
_AI_VARIABLE_MAX = {"10": 20, "21": 20}


def alert_start_date(expiry: date, horizon_days: int = DEFAULT_ALERT_HORIZON_DAYS) -> date:
    """First day (inclusive) on which a lot counts as nearing expiry."""
    return expiry - timedelta(days=horizon_days)


def expiry_state(
    expiry: date | None,
    on_date: date,
    horizon_days: int = DEFAULT_ALERT_HORIZON_DAYS,
) -> str:
    """Escalation state of a lot on ``on_date``.

    ``None`` expiry returns 'fresh' — batch discipline (expiry mandatory on
    pharma receipts) is enforced at the document level, not here.
    """
    if expiry is None:
        return STATE_FRESH
    if on_date > expiry:
        return STATE_EXPIRED
    if on_date >= alert_start_date(expiry, horizon_days):
        return STATE_NEARING
    return STATE_FRESH


@dataclass
class Gs1Result:
    """Parsed GS1 DataMatrix payload for a pharma trade item."""

    gtin: str
    expiry: date | None
    batch: str
    serial: str


def _parse_gs1_date(value: str) -> date:
    """YYMMDD per GS1: century 20xx; day '00' means last day of the month."""
    year = 2000 + int(value[0:2])
    month = int(value[2:4])
    day = int(value[4:6])
    if not 1 <= month <= 12:
        raise ValueError(f"invalid GS1 date {value!r}: month {month}")
    if day == 0:
        day = calendar.monthrange(year, month)[1]
    return datetime.strptime(f"{year:04d}{month:02d}{day:02d}", "%Y%m%d").date()


def parse_gs1_datamatrix(scan: str) -> Gs1Result:
    """Parse a GS1 DataMatrix scan string into its pharma fields.

    Understands AIs 01 (GTIN-14), 17 (expiry YYMMDD), 10 (batch/lot) and
    21 (serial); variable-length fields end at a GS separator or end of
    string. Raises ``ValueError`` on anything malformed — a mis-scan must
    never silently create a wrong lot.
    """
    if not scan:
        raise ValueError("empty GS1 scan")
    data = scan.strip()
    if data.startswith(SYMBOLOGY_PREFIX):
        data = data[len(SYMBOLOGY_PREFIX) :]
    data = data.lstrip(GS)

    gtin, expiry, batch, serial = "", None, "", ""
    position = 0
    while position < len(data):
        ai = data[position : position + 2]
        position += 2
        if ai in _AI_FIXED:
            length = _AI_FIXED[ai]
            value = data[position : position + length]
            if len(value) != length:
                raise ValueError(f"GS1 AI {ai}: expected {length} chars, got {value!r}")
            position += length
            if ai == "01":
                if not value.isdigit():
                    raise ValueError(f"GS1 GTIN must be 14 digits, got {value!r}")
                gtin = value
            else:
                if not value.isdigit():
                    raise ValueError(f"GS1 expiry must be YYMMDD digits, got {value!r}")
                expiry = _parse_gs1_date(value)
        elif ai in _AI_VARIABLE_MAX:
            end = data.find(GS, position)
            if end == -1:
                end = len(data)
            value = data[position:end]
            if not value or len(value) > _AI_VARIABLE_MAX[ai]:
                raise ValueError(f"GS1 AI {ai}: invalid length for {value!r}")
            position = end + 1 if end < len(data) else end
            if ai == "10":
                batch = value
            else:
                serial = value
        else:
            raise ValueError(f"unsupported GS1 application identifier {ai!r} in {scan!r}")

    if not gtin and not batch:
        raise ValueError(f"GS1 scan carries neither GTIN nor batch: {scan!r}")
    return Gs1Result(gtin=gtin, expiry=expiry, batch=batch, serial=serial)
