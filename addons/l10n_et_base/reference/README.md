# `l10n_et_base` reference calculators

Pure-Python, Odoo-free tax math — the single source of truth the Odoo models import.
Fast-tested by `tests_fast/test_et_tax_calc.py` (run `pytest tests_fast/` from repo root).

## `et_tax_calc.py`

### `compute_wht(base_amount, kind, *, has_tin, has_licence, **rates)` → `WhtResult`
Withholding-tax decision + amount for one purchase base (amount **before VAT**).
Everything after `kind` is keyword-only (a rate passed positionally would silently
land in a boolean flag). The base is rounded to cents before the threshold check
(float dust from summed line subtotals cannot breach an exact threshold); amounts
are computed in exact decimal with **half-up** rounding (Odoo HALF-UP semantics).
NaN/inf raise `ValueError` — compliance math fails loudly, never open.

- `kind`: `"goods"` (threshold ETB 20,000), `"service"` (ETB 10,000), or
  `"foreign_digital"` (no threshold).
- Standard rate **3%** on amounts *strictly above* the threshold.
- **30% punitive** rate (instead of 3%) when `has_tin` **or** `has_licence` is false.
  Whether the punitive rate respects the thresholds is itself config
  (`punitive_respects_thresholds`, default True — the Proc 979/2016 art. 92
  predecessor rule was arguably ungated; flippable without a code release, never
  lifts the threshold for compliant suppliers).
- Foreign digital services: flat **15%**, any amount.
- All rates/thresholds are keyword-overridable so the Odoo layer can feed effective-dated
  configuration (see `l10n.et.wht.rate`).

### `check_cash_cap(payment_amount, prior_cash_today, cap)` → `CashCapResult`
Proc 1395/2025 daily cash cap for one party. Flags when the **daily total** to a party
exceeds the cap (default ETB 30,000). Comparison is strictly greater-than: a running total
of exactly the cap is allowed. The Odoo layer decides warn vs. block.

### `validate_tin(tin)` → `TinResult`
Format validation for Ethiopian MoR TINs: exactly **10 ASCII digits**, tolerating
spaces/hyphens/slashes/dots in input (normalizes to bare digits); rejects
all-same-digit placeholders and non-ASCII Unicode numerals (Arabic-Indic, Ethiopic
etc. pass `str.isdigit()` but are not valid TINs). Format-only — MoR has published
no check-digit algorithm; extend here (not in the Odoo constraint) if one is gazetted.

## Rules are configuration, not constants
The module-level `DEFAULT_*` values are July-2026-verified fallbacks only. Real deployments
read effective-dated records so historical documents never change when a future rate is
gazetted. **Re-verify every rate against the Ministry of Revenue before go-live.**
