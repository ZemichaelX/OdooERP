# l10n_et_reports — Ethiopian Compliance (SapianERP)

Ships as the top-level app **Ethiopian Compliance** (menu renamed from
"Ethiopian Statutory Reports" and unparented from Accounting > Reporting when
it was promoted): compliance is the obligation the client is buying, the
reports are how it is discharged.

Thin statutory-reports slice (Epic B of the revised backlog, CLAUDE.md; spec
`docs/plan-2026/07-ethiopian-localization.md` §5 — everything else in §5 stays
deferred). Depends on `l10n_et_base` and reuses its tax records/WHT kind
markers — nothing re-declared here.

## Reports
- **Monthly VAT Declaration** (`l10n.et.vat.declaration`): output VAT (15% /
  zero-rated / exempt sales, base + tax per row), input VAT (purchases), net
  payable or credit carried forward (Proc 1341/2024, monthly period).
- **WHT Summary** (`l10n.et.wht.summary`): one row per vendor bill per WHT rate
  (3% / 30% / 15%) with supplier, TIN, base and amount; totals by rate; grand
  total. Missing supplier TINs get the MISSING marker + fix-before-filing
  warning (MoR rejects filings without identifiers). Remit within 30 days of
  month end.

## Design
- Reports read LIVE from posted journal items — a record is a period window
  over the GL, not a snapshot; reprinting after corrections shows current
  numbers. Refunds net out.
- **Tie-out guarantee**: every report carries reconciliation rows comparing its
  totals against the FULL GL movement of the accounts the underlying taxes post
  to (VAT payable 300700, VAT receivable 221200, WHT payable 300600). A manual
  journal entry that bypasses the tax engine renders a visible warning — a
  mismatch never passes silently.
- Tax records are resolved per company from the chart-template xmlids
  (`id_tax03/04/06/07/08/10`, WHT via the `l10n_et_wht_kind` marker), so the
  module is inert on companies not on the Ethiopian chart.

## ⚠ WHT anti-avoidance (accountant note, Jul 2026)
The 20,000/10,000 WHT thresholds are PER TRANSACTION, but the authority may
AGGREGATE deliberately split invoices (one supply invoiced as several
sub-threshold pieces) and assess the WHT that was avoided. The WHT summary
reports what was actually withheld per posted bill — it does not detect
splitting. Advise clients: never split a supply to duck the threshold; when
in doubt, withhold.

## ⚠ Verify against current MoR forms
The computations are exact and golden-tested; the ROW LAYOUT of the printed
declaration is a simple section-level rendering. Before filing with the
Ministry of Revenue, verify the current official VAT return / WHT schedule
layout and map these sections onto it.

## Tests
Golden values hand-computed from the Epic 3 demo document set (README of
`tests/common.py`): output 1,500 / input 10,950 / net −9,450 credit; WHT
{3%: 1,500, 30%: 4,500, 15%: 1,200} = 7,200 tied to GL.
