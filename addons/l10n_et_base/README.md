# l10n_et_base — Ethiopia Accounting Base (SapianERP)

Extends the **core `l10n_et`** chart template (code `'et'`, auto-installed for
Ethiopian companies) with the SapianERP Ethiopian accounting localization.
Epic 3 of `docs/plan-2026/10-claude-code-roadmap.md`; functional spec
`docs/plan-2026/07-ethiopian-localization.md` §1.

## What it adds

### Chart of accounts (template merge — core files untouched)
- New accounts: `3009` PAYE (Employment Income Tax) Payable,
  `2302` Customs Duty Clearing.
- Account-type corrections for mistyped core accounts (shipped by core as
  assets/liabilities on the wrong side): `2212` VAT Receivable → asset,
  `2213`/`2214` WHT receivables → asset, `3006` → *Withholding Tax Payable*
  (liability, name typo fixed), `3007` VAT Payable → liability,
  `3008` Federal Income Tax → liability.
- Core already provides 15% VAT (sale + purchase), 0% and exempt codes;
  this module adds the **Zero-Rated** and **VAT Exempt** fiscal positions and
  maps the core taxes onto them (Proc 1341/2024).

### Withholding tax automation (Aug 2025 rules)
- New effective-dated config model `l10n.et.wht.config` (rates, thresholds,
  `punitive_respects_thresholds` flag, mandatory `source_note`), seeded at chart
  load with 3% / 30% / 15%, thresholds 20,000 / 10,000, effective 2025-08-01.
- On posting a **vendor bill**, the engine groups lines by supply kind
  (product type `service` → services, otherwise goods; a partner flagged
  *Foreign Digital Service Provider* makes the whole bill foreign-digital),
  computes applicability via the reference calculator, and links the matching
  negative purchase tax (credits *Withholding Tax Payable*). Idempotent on
  re-post; decision logged in the chatter with the source note.
- Printable **WHT Certificate** (`Print` menu on the bill).
- A 3% sale-side WHT code is included for sales where the customer withholds.

### Cash payment cap (Proc 1395/2025)
- Effective-dated `l10n.et.cash.cap.config` (default cap ETB 30,000/party/day,
  enforcement `warn`, seeded effective 2025-07-01). Outbound **cash** payments
  breaching the daily per-party total either warn (audit message on the payment)
  or block (`ValidationError`) — configurable, no code release needed.

### Partner compliance fields
TIN (10-digit format-validated + normalized via the reference calculator), VAT
registration no., business licence no. + expiry (expired ⇒ punitive WHT),
foreign-digital flag, Amharic name. TIN/licence propagate from the commercial
entity to its contacts (`_commercial_fields`). Shown on a finance-only partner
tab.

## Design decisions
- **WHT on the bill, not at payment.** Odoo 19 ships a payment-time framework
  (`l10n_account_withholding_tax`); spec 07 §1 and the epic DoD require the WHT
  line and certificate at bill level, and the core `l10n_et` module models ET
  withholding the same way (negative-percent taxes). Revisit if MoR practice
  moves to payment-time withholding.
- **All math in `reference/et_tax_calc.py`** (pure Python, golden-tested in
  `tests_fast/`); the Odoo layer never re-implements it (CLAUDE.md rule #10).
- **Interpretation defaults pending accountant sign-off** (record in the client
  manifest before go-live): punitive rate fires when either TIN *or* licence is
  missing; punitive gated by thresholds (config-flippable); foreign digital 15%
  has no threshold and ignores compliance flags; TIN validation is format-only
  (no public MoR checksum); thresholds/cap are strictly exclusive.

## Tests
- Fast (no Odoo): `pytest tests_fast/` — reference calculator golden values.
- Integration: `--test-enable -i l10n_et_base` on a scratch DB — WHT postings,
  cash cap, partner compliance, effective dating, trial balance.

## Follow-ups (out of this epic)
MAT 2.5% informational computation · VAT registration-threshold (2M) warning ·
NBE FX reference-rate import · WHT remittance-30-day reminder · tax-report tags
for the new WHT codes (Epic 5 `l10n_et_reports`) · Amharic `.po`.

**Re-verify every rate/threshold against the Ministry of Revenue before each
client go-live.**
