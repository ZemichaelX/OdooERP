# -*- coding: utf-8 -*-
"""Pure-Python Ethiopian transaction-tax calculators (no Odoo dependency).

Single source of truth for three pieces of Ethiopian accounting logic that the Odoo
`l10n_et_base` models call:

1. Withholding tax (WHT) applicability + amount on vendor bills / purchases.
2. The Proc 1395/2025 daily cash-payment cap check.
3. Ethiopian TIN format validation for partner compliance fields.

Keeping the math here means it is covered by fast pytest golden tests (`tests_fast/`)
with no running Odoo instance. The Odoo layer passes *effective-dated configuration*
(rates/thresholds read from data records) into these functions — the defaults below
are only the July-2026-verified fallbacks and MUST be re-confirmed against gazetted
proclamation text before any client go-live.

Sources (re-verify before go-live):
- WHT 3% on goods > ETB 20,000 / services > ETB 10,000 per transaction; 30% punitive
  where the supplier lacks a TIN + valid business licence; 15% on foreign digital
  services (Aug 2025 rules; MoR practice notes).
- Cash cap: cash payments to one party may not exceed ETB 50,000 — as a single
  transaction OR as the aggregate of payments to that party in one day, whichever
  hits first (Art. 81, Proc 1395/2025; accountant-verified Jul 2026 against KPMG's
  copy of the proclamation). A single payment over the cap is just the aggregate
  check with zero prior payments.
- TIN: Ministry of Revenue TINs are 10-digit numbers (often displayed XXXX-XXXX-XX).
  No public check-digit algorithm is gazetted, so validation is format-only; if MoR
  publishes a checksum, extend ``validate_tin`` here (single source of truth).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# --- WHT configuration defaults (fallbacks; the Odoo layer overrides from data) -------
DEFAULT_WHT_RATE_STANDARD = 0.03  # domestic 3%
DEFAULT_WHT_RATE_PUNITIVE = 0.30  # 30% when supplier lacks TIN + licence
DEFAULT_WHT_RATE_FOREIGN_DIGITAL = 0.15  # 15% on foreign digital services
DEFAULT_WHT_THRESHOLD_GOODS = 20000.0  # per-transaction threshold, goods (exclusive)
DEFAULT_WHT_THRESHOLD_SERVICE = 10000.0  # per-transaction threshold, services (exclusive)

# --- Cash-payment cap default ---------------------------------------------------------
# Art. 81, Proc 1395/2025 — verified Jul 2026 (accountant + KPMG proclamation copy).
DEFAULT_CASH_CAP = 50000.0  # ETB per party: single transaction or same-day aggregate

# --- TIN format -----------------------------------------------------------------------
TIN_LENGTH = 10  # MoR TINs are 10 digits
_TIN_SEPARATORS = " -/."  # characters tolerated in user input

# Supply kinds understood by the WHT calculator.
KIND_GOODS = "goods"
KIND_SERVICE = "service"
KIND_FOREIGN_DIGITAL = "foreign_digital"


def _round2(value: float) -> float:
    """Round half-up to 2 decimals (cents) in exact decimal arithmetic.

    Mirrors Odoo's default HALF-UP currency rounding (the Odoo layer still re-rounds
    with the currency's own utilities). ``Decimal(repr(...))`` sees the float's
    shortest decimal form, so accumulated float dust (e.g. line subtotals summing to
    20000.000000000004) rounds away instead of leaking into threshold comparisons,
    and half-up survives at any magnitude (a fixed ``+1e-9`` nudge is lost to float
    ULP above ~ETB 600M and silently reverts to banker's rounding).
    """
    return float(Decimal(repr(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _times_rate(amount: float, rate: float) -> float:
    """``amount × rate`` carried out in exact decimal, rounded half-up to cents."""
    product = Decimal(repr(amount)) * Decimal(repr(rate))
    return float(product.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@dataclass
class WhtResult:
    """Outcome of a withholding-tax evaluation for one transaction/base amount."""

    applicable: bool
    rate: float
    amount: float
    reason: str
    threshold: float = 0.0


def compute_wht(
    base_amount: float,
    kind: str = KIND_GOODS,
    *,
    has_tin: bool = True,
    has_licence: bool = True,
    punitive_respects_thresholds: bool = True,
    rate_standard: float = DEFAULT_WHT_RATE_STANDARD,
    rate_punitive: float = DEFAULT_WHT_RATE_PUNITIVE,
    rate_foreign_digital: float = DEFAULT_WHT_RATE_FOREIGN_DIGITAL,
    threshold_goods: float = DEFAULT_WHT_THRESHOLD_GOODS,
    threshold_service: float = DEFAULT_WHT_THRESHOLD_SERVICE,
) -> WhtResult:
    """Return the WHT decision + amount for one purchase/expense line base.

    ``base_amount`` is the taxable base BEFORE VAT (WHT is computed on the net amount).
    ``kind`` is one of ``goods`` / ``service`` / ``foreign_digital``.

    Rules (Aug 2025):
    - Foreign digital services: flat 15%, no domestic threshold (applies to any amount).
    - Domestic goods: 3% only when base > 20,000; services: 3% only when base > 10,000.
    - Punitive 30% (instead of 3%) when the supplier lacks a TIN OR a valid business
      licence. Whether the punitive rate respects the same thresholds is itself
      effective-dated configuration (``punitive_respects_thresholds``, default True):
      the predecessor rule (Proc 979/2016 art. 92) was arguably ungated, so the Odoo
      layer must be able to flip this without a code release. The flag never lifts
      the threshold for COMPLIANT suppliers.

    The comparison is strictly greater-than: a base exactly on the threshold does NOT
    attract WHT (spec: "goods > ETB 20,000", "services > ETB 10,000"). The base is
    rounded to cents first, so float dust from summing line subtotals (e.g.
    20000.000000000004) cannot push an exactly-at-threshold invoice over.

    Everything after ``kind`` is keyword-only: config values passed positionally
    would otherwise land in the boolean compliance flags and be silently swallowed.
    Non-finite bases (NaN/inf) raise ``ValueError`` — compliance code must fail
    loudly, never fail open.
    """
    if not math.isfinite(base_amount):
        raise ValueError(f"base_amount must be finite, got {base_amount!r}")
    base_amount = _round2(base_amount)
    if base_amount <= 0:
        return WhtResult(False, 0.0, 0.0, "Non-positive base — no WHT.")

    if kind == KIND_FOREIGN_DIGITAL:
        amount = _times_rate(base_amount, rate_foreign_digital)
        return WhtResult(
            True,
            rate_foreign_digital,
            amount,
            "Foreign digital services WHT (15%).",
            threshold=0.0,
        )

    if kind == KIND_SERVICE:
        threshold = threshold_service
    elif kind == KIND_GOODS:
        threshold = threshold_goods
    else:
        raise ValueError(f"Unknown WHT supply kind: {kind!r}")

    compliant = has_tin and has_licence
    threshold_gated = compliant or punitive_respects_thresholds
    if threshold_gated and base_amount <= threshold:
        return WhtResult(
            False,
            0.0,
            0.0,
            f"Base {base_amount:,.2f} at/under {kind} threshold {threshold:,.0f} — no WHT.",
            threshold=threshold,
        )

    rate = rate_standard if compliant else rate_punitive
    amount = _times_rate(base_amount, rate)
    reason = (
        f"Standard {rate * 100:.0f}% WHT on {kind}."
        if compliant
        else f"Punitive {rate * 100:.0f}% WHT — supplier lacks TIN and/or business licence."
    )
    return WhtResult(True, rate, amount, reason, threshold=threshold)


@dataclass
class CashCapResult:
    """Outcome of a daily cash-payment cap check for one party."""

    total_day: float  # cumulative cash to this party today, including the new payment
    cap: float
    exceeded: bool
    excess: float = 0.0  # amount over the cap (0.0 when within cap)


def check_cash_cap(
    payment_amount: float,
    prior_cash_today: float = 0.0,
    *,
    cap: float = DEFAULT_CASH_CAP,
) -> CashCapResult:
    """Check the Art. 81 (Proc 1395/2025) cash cap for one party.

    ``prior_cash_today`` is the sum of cash already paid to this party earlier the same
    day; ``payment_amount`` is the new cash payment being validated. The cap applies to
    a SINGLE transaction and to the same-day AGGREGATE per party, whichever hits first —
    both are covered by this one check, since a single over-cap payment is the aggregate
    case with ``prior_cash_today == 0``. Comparison is strictly greater-than: a running
    total of exactly the cap is allowed; anything above it is flagged.

    The Odoo layer decides whether "flagged" means warn or block (a company setting).
    Non-finite amounts raise ``ValueError``: NaN compares False against the cap, so a
    corrupted amount would otherwise report as compliant (fail-open) — the wrong
    failure direction for a blocking control.
    """
    if not math.isfinite(payment_amount) or not math.isfinite(prior_cash_today):
        raise ValueError(
            f"payment_amount and prior_cash_today must be finite, "
            f"got {payment_amount!r} / {prior_cash_today!r}"
        )
    total = _round2(max(prior_cash_today, 0.0) + max(payment_amount, 0.0))
    exceeded = total > cap
    excess = _round2(total - cap) if exceeded else 0.0
    return CashCapResult(total_day=total, cap=cap, exceeded=exceeded, excess=excess)


_CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _looks_numeric(text: str) -> bool:
    """True when ``text`` is a plain number (optionally signed, with thousands
    separators) — such a value is never a spreadsheet formula."""
    try:
        float(text.replace(",", ""))
        return True
    except ValueError:
        return False


def csv_safe_cell(value) -> str:
    """Neutralize spreadsheet formula injection in an exported CSV cell.

    A cell whose text begins with ``= + - @`` (or a tab/CR) is interpreted as a
    formula by Excel/LibreOffice when the file is opened — a supplier or
    employee name like ``=WEBSERVICE(...)`` would then execute. Prefixing such
    a value with a single quote defuses it while remaining human-readable. The
    exports (bank salary file, VAT/WHT CSVs) are opened in exactly those tools,
    so every user-influenced cell must pass through here.
    """
    text = "" if value is None else str(value)
    if not text or _looks_numeric(text):
        # A pure number (incl. a leading minus/plus and thousands separators)
        # is never a formula — quoting it would corrupt numeric columns.
        return text
    if text[0] in _CSV_INJECTION_PREFIXES:
        return "'" + text
    return text


@dataclass
class TinResult:
    """Outcome of an Ethiopian TIN format validation."""

    valid: bool
    normalized: str  # bare digits when valid, "" when invalid
    reason: str


def validate_tin(tin: str | None) -> TinResult:
    """Format-validate an Ethiopian Ministry of Revenue TIN.

    Accepts the 10 digits with optional spaces / hyphens / slashes / dots as users
    type them (e.g. ``0012-3456-78``) and normalizes to the bare digit string the
    database stores. Rejects anything that is not exactly ``TIN_LENGTH`` digits, and
    the all-same-digit placeholders (``0000000000``) that show up in dirty imports.

    This is FORMAT validation only — MoR has published no check-digit algorithm.
    The Odoo partner constraint calls this function; do not re-implement it there.
    """
    if not tin or not tin.strip():
        return TinResult(False, "", "TIN is empty.")

    normalized = tin.strip()
    for sep in _TIN_SEPARATORS:
        normalized = normalized.replace(sep, "")

    # isascii() guard: str.isdigit() alone accepts Arabic-Indic/Bengali/Ethiopic
    # numerals, which would persist un-matchable TINs in a compliance field.
    if not (normalized.isascii() and normalized.isdigit()):
        return TinResult(False, "", f"TIN {tin!r} contains non-digit characters.")
    if len(normalized) != TIN_LENGTH:
        return TinResult(
            False,
            "",
            f"TIN must be exactly {TIN_LENGTH} digits; got {len(normalized)}.",
        )
    if len(set(normalized)) == 1:
        return TinResult(False, "", f"TIN {normalized} is a placeholder value.")
    return TinResult(True, normalized, "Valid TIN format.")


# =============================================================================
# SOCIAL WELFARE LEVY — Council of Ministers Regulation No. 519/2022
# =============================================================================
#
# THE FOUR THINGS THAT ARE ESTABLISHED
#   rate        3% (0.03)
#   base        the aggregate CIF value of the imported goods
#   instrument  Council of Ministers Regulation No. 519/2022, "Social Welfare
#               Levy on Imported Goods"
#   effective   6 August 2022 (gazetted 22 August 2022)
#
# HOW IT BEHAVES — the part that is easy to get exactly backwards
#
#   IN ADDITION.  It is levied on top of customs duty, excise, VAT and surtax,
#   not instead of any of them.
#
#   A COST, NOT A RECEIVABLE.  It is NOT creditable against income tax. This is
#   the single most important line in this file. A competitor's published tax
#   guide describes an "Import Advance Income Tax, 3% of CIF, offset against
#   income tax"; no authority for such a tax was found — it is absent from
#   PwC's Ethiopian import-tax page and from the Art. 92 withholding
#   categories. Implementing it that way books 3% of every consignment an
#   importer brings in as a recoverable ASSET that will never be recovered,
#   overstating assets and understating cost of goods on every import. The
#   result object therefore carries an explicit ``creditable`` field which is
#   hard-wired False, so a caller cannot get this wrong by omission.
#
#   IT IS NOT IN ANYBODY ELSE'S BASE.  The levy does not form part of the base
#   for computing any other import tax. The Odoo layer expresses this with
#   include_base_amount = False on the tax record; here it means the base
#   passed in is the CIF value and nothing downstream should add this result to
#   another tax's base.
#
#   NO THRESHOLD.  Stated out loud because the neighbouring WHT rules in this
#   same file DO have thresholds (20,000 goods / 10,000 services) and the
#   symmetry invites inventing one. Regulation 519/2022 sets none: a CIF of
#   ETB 1 attracts ETB 0.03. ``test_there_is_no_threshold`` pins this.
#
# CORROBORATION, NOT AUTHORITY. Published summaries of the regulation agree on
# the rate, the CIF base and the three exemptions. The regulation text itself
# could not be retrieved in the environment this was written in, so it is not
# quoted here and the figures still need checking against the gazetted text
# before a client go-live — the same standing rule as every other rate in this
# file.

DEFAULT_SWL_RATE = 0.03  # 3% of CIF, Reg. 519/2022

#: First date the levy applies. Gazetted 22 Aug 2022, effective 6 Aug 2022.
#: In the Ethiopian calendar that is HAMLE 30, 2014 EC — day 30, the last day of
#: the month, NOT a month boundary. Every Ethiopian effective date this project
#: has verified against a proclamation lands on day 1, so this is enumerated in
#: tests_fast/test_et_statutory_dates_land_on_month_1.py and left FAILING
#: (xfail, strict) until the gazette settles it. It is not "fixed" here.
DEFAULT_SWL_EFFECTIVE_FROM = (2022, 8, 6)

#: The three exemptions in Reg. 519/2022. Modelled as a closed set rather than a
#: boolean so a bill records WHY it was exempt — an exemption with no reason is
#: indistinguishable from a bug, and the auditor asks which one.
SWL_EXEMPT_DIPLOMATIC = "diplomatic"
SWL_EXEMPT_SURTAX_133_2007 = "surtax_133_2007"
SWL_EXEMPT_MOF_DIRECTIVE = "mof_directive"
SWL_EXEMPTIONS = {
    SWL_EXEMPT_DIPLOMATIC: "Goods imported by persons/organisations with diplomatic privilege.",
    SWL_EXEMPT_SURTAX_133_2007: "Goods already subject to import surtax under Regulation 133/2007.",
    SWL_EXEMPT_MOF_DIRECTIVE: "Goods excluded by a Ministry of Finance directive.",
}


@dataclass
class SocialWelfareLevyResult:
    """Outcome of a social welfare levy evaluation for one import.

    ``creditable`` is part of the RESULT, not a parameter, and is always False.
    It exists so that the treatment is carried to every call site rather than
    living only in a comment: a caller that posts ``amount`` has the answer to
    "is this an asset?" in its hand.
    """

    applicable: bool
    rate: float
    base: float
    amount: float
    reason: str
    #: NEVER True. The levy is a cost of the import, not a recoverable tax.
    creditable: bool = False


def compute_social_welfare_levy(
    cif_value: float,
    *,
    on_date=None,
    exemption: str | None = None,
    rate: float = DEFAULT_SWL_RATE,
    effective_from=None,
) -> SocialWelfareLevyResult:
    """Return the social welfare levy on one import (Reg. 519/2022).

    ``cif_value`` is the aggregate cost-insurance-freight value of the goods, in
    ETB, and is the WHOLE base: no duty, no excise, no VAT is added to it, and
    the levy itself is added to nobody else's base.

    ``on_date`` is the date the levy is assessed on (the customs declaration
    date in practice). When given together with ``effective_from``, an import
    before the commencement date attracts nothing — historical documents keep
    their historical treatment, which is the whole reason the date is a
    parameter and not a constant baked into the arithmetic.

    ``exemption`` is one of :data:`SWL_EXEMPTIONS` or None. An unknown value
    raises rather than being treated as "not exempt": a typo'd exemption code
    that silently charges the levy is a wrong invoice, and one that silently
    waives it is an underpayment.

    ``rate`` and ``effective_from`` are parameters because they are
    CONFIGURATION (CLAUDE.md rule 4). The Odoo layer passes them from
    effective-dated records; the defaults here are the Reg. 519/2022 values.

    Non-finite CIF values raise ``ValueError`` — a NaN base would compute a NaN
    levy and post it, and tax code must fail loudly rather than fail open.
    """
    if not math.isfinite(cif_value):
        raise ValueError(f"cif_value must be finite, got {cif_value!r}")
    if exemption is not None and exemption not in SWL_EXEMPTIONS:
        raise ValueError(
            f"Unknown social welfare levy exemption: {exemption!r}. "
            f"Known: {sorted(SWL_EXEMPTIONS)}"
        )

    base = _round2(cif_value)
    if base <= 0:
        return SocialWelfareLevyResult(False, 0.0, base, 0.0, "Non-positive CIF — no levy.")

    if exemption is not None:
        return SocialWelfareLevyResult(
            False, 0.0, base, 0.0, f"Exempt: {SWL_EXEMPTIONS[exemption]}"
        )

    if on_date is not None and effective_from is not None and on_date < effective_from:
        return SocialWelfareLevyResult(
            False,
            0.0,
            base,
            0.0,
            f"Import dated {on_date} predates the levy's commencement ({effective_from}).",
        )

    amount = _times_rate(base, rate)
    return SocialWelfareLevyResult(
        True,
        rate,
        base,
        amount,
        f"Social welfare levy {rate * 100:.0f}% of CIF (Reg. 519/2022). "
        f"A COST of the import — not creditable against income tax.",
    )
