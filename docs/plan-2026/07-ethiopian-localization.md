# 07 — Ethiopian Localization Specification

The moat. Exact functional specs for the `l10n_et_*` modules. All rates/brackets below were verified against July 2026 sources (see 02 §B) but **must be re-confirmed against gazetted proclamation text before each go-live** — hence the design rule: *rates are effective-dated config data, never hardcoded*.

## 1. `l10n_et_base` — Chart of accounts & taxes

- **Chart of accounts:** IFRS-aligned Ethiopian CoA template (assets/liabilities/equity/revenue/expense with local conventions: VAT receivable/payable, WHT receivable/payable, pension payable, PAYE payable, customs duty clearing). Support IFRS for SMEs statement layout (AABE mandate).
- **VAT (Proc 1341/2024, Reg 570/2025):** 15% standard sale/purchase taxes; zero-rated and exempt tax codes; monthly VAT period; registration-threshold awareness (warn if unregistered client config sells > ETB 2M/yr). Tax on invoices auto-applied by fiscal position. **Excess input VAT: carry-forward is the confirmed default treatment (accountant, Jul 2026) — cash refunds are exporter/priority-investor processes, not the ordinary path; the VAT declaration models a credit as carry-forward.** **Reg 570/2025 requires REAL-TIME EFD + QR-coded invoices for VAT-registered traders (simplified invoice allowed ≤ ETB 10,000) — this RAISES the priority of fiscal-device integration (`l10n_et_einvoice` §6) for any retail client.**
- **Withholding tax (accountant-CONFIRMED Jul 2026):** 3% WHT on goods > ETB 20,000 and services > ETB 10,000 per transaction — implemented as automatic WHT lines on vendor bills above thresholds; 30% punitive when EITHER the TIN or the business licence is missing (partner compliance fields: TIN, licence no., expiry); 15% WHT code for foreign digital services; thresholds gate ALL WHT including punitive. WHT certificates printable; remittance-within-30-days reminder. **Anti-avoidance: the authority may aggregate deliberately split invoices — never split a supply to duck the threshold.**
  **Corroborated (Aug 2026):** PwC's Ethiopia withholding-tax summary independently confirms the domestic rate at 3% with ETB 20,000 goods / ETB 10,000 services thresholds, and the no-TIN rate at 30% — matching the seeded config. Corroboration of existing data, not a new source of truth; the proclamations remain the authority.
  **Core rates DEACTIVATED (Aug 2026):** core `l10n_et` ships 2% WH (`id_tax02`/`id_tax05`) and 35% WH (`id_tax13`/`id_tax12`). The domestic rate has been 3% since Aug 2025 and **no 35% Ethiopian withholding rate exists** — the punitive no-TIN rate is 30%. `l10n_et_base` sets `active = False` on all four for companies on chart 'et' (never deletes: posted bills must stay reportable). Guarded by `test_supported_wht_rates.py`, which asserts the invariant — no active withholding tax offers a rate `l10n.et.wht.config` does not serve — rather than a list of four xml ids.
  **NOT implemented, and not to be added from a summary table:** dividends, royalties, interest, management/technical fees, social welfare levy. Each needs rate, base, threshold, effective date and a proclamation citation established first.
  **OPEN — effective-date discrepancy:** the seeded config uses `effective_from = 2025-08-01`, while this knowledge base records the change as effective **7 August 2025 (Nehase 1, 2017 EC)**. Both cannot be right: 1 Aug 2025 is Hamle 24, mid-Ethiopian-month, which no verified Ethiopian effective date has been. Neither artefact has been changed; the date is being established from a primary source. Treat any WHT decision dated 1–6 Aug 2025 as unverified.
- **Other 1395/2025 mechanics:** cash-payment cap warning (block/warn) — **ETB 50,000 per party: single transaction OR same-day aggregate, whichever hits first (Art. 81, Proc 1395/2025 — accountant-verified Jul 2026 against KPMG's proclamation copy; supersedes the 30,000 figure in earlier drafts)**; MAT (2.5% of turnover) informational computation in annual closing report; taxpayer category A/B field on company.
- **Partner fields:** TIN (checksum-validated format), VAT reg no., business licence, Amharic name.
- **Multi-currency:** USD/EUR purchase flows with NBE reference-rate import; FX gain/loss accounts.

## 2. `l10n_et_payroll` — PAYE & pension engine (started in earlier repo — 22/22 tests passing)

- **PAYE bands (Proc 1395/2025, effective 1 Jul 2025)** as effective-dated records:
  0–2,000: 0% · 2,001–4,000: 15% · 4,001–7,000: 20% · 7,001–10,000: 25% · 10,001–14,000: 30% · >14,000: 35%.
  Reference check: basic ETB 10,000 → PAYE 1,650; pension 700; net 7,650.
  **Corroborated (Aug 2026):** a Chambers summary of the 2026 PAYE brackets gives
  0/15/20/25/30/35% at the same 2,000 / 4,000 / 7,000 / 10,000 / 14,000
  boundaries — an independent match for the band table already seeded under Proc
  1395/2025. Corroboration only: the proclamation remains the authority and the
  §10 protocol still applies before any go-live.
- **Pension (Proc 1268/2022, accountant-verified Jul 2026):** employee 7% / employer 11% of basic salary; eligibility from 45 days of employment. **Nationality rules: MANDATORY for Ethiopian nationals; VOLUNTARY (opt-in flag on the employee) for foreign nationals of Ethiopian origin; other foreign nationals EXCLUDED entirely.** Remittance via POESSA declaration + bank slip within 30 days of month-end.
- **Salary structure (allowance rules accountant-verified Jul 2026):** basic + configurable allowance types — **transport exempt up to the LOWER of ETB 2,200/month or 25% of basic salary (excess taxable, computed by the engine); hardship exempt; medical actual-cost exempt; housing and position allowances TAXABLE by default; per-diems handled as evidence-based input lines (no monthly formula)** — deductions (loans, advances, court orders), overtime pay classes fed by attendance (1.5×/1.75×/2×/2.5× per labor law), absence deductions.
- **Outputs:** payslips (branded, EN/AM, optional Ethiopian-calendar date), payroll register, bank transfer file (CBE/other formats), PAYE + pension remittance reports, payroll journal auto-posting (salary expense, payables per tax/pension).
- **Historical correctness:** payslips computed with the bands effective on their period — a rate change never rewrites history.

## 3. HR policy defaults (Labor Proclamation 1156/2019)

- Leave: annual 16 working days (year 1) + 1 day per additional 2 years; sick/maternity/paternity/mourning types per proclamation; accrual engine.
- Probation ≤ 60 working days; standard week 48h; overtime classes as above.
- Severance calculator: 30× average daily wage (year 1) + ⅓ per additional year, cap 12 months — used in termination settlements.

## 4. `l10n_et_calendar` — Ethiopian calendar

- EC↔GC conversion utilities (build on pycalcal/OCA ethiopic_calendar; validate against Andegna test vectors, incl. Pagume and leap years).
- Display preference per user/company: show EC dates alongside GC in key documents; EC date in report headers and document numbering (`2017EC`).
- **Ethiopian fiscal year support:** July 8–July 7 (Hamle–Sene) fiscal periods for companies that report that way; EC month-based payroll periods option.
- Ethiopian public holidays seed data (fixed + movable), feeding leave/overtime calculations.

## 5. `l10n_et_reports` — statutory outputs (premium)

- Monthly VAT declaration (aligned to MoR form), input/output VAT registers.
- WHT summary + certificates.
- PAYE monthly declaration; pension remittance schedule.
- Financial statements (IFRS for SMEs layout): P&L, balance sheet, cash flow — filterable by branch; optional EC-period columns.
- Audit-ready exports: GL, trial balance, stock ledger with lot detail.

## 6. `l10n_et_einvoice` — receipts & e-invoicing

- **Now:** QR-coded invoice/receipt layouts satisfying Directive 188/2024 expectations; sequential fiscal numbering; credit/debit note compliance per VAT proclamation.
- **POS:** integration path for certified fiscal devices (until ITAS supersedes); receipt content rules.
- **Next:** ITAS e-invoice API connector — build the abstraction now (invoice → canonical payload → provider), implement transport when MoR publishes specs/dates. ⚠ Track MoR directives quarterly.

## 7. `sapian_payments` & `sapian_sms`

- Payment providers: **Telebirr** (H5/web + USSD C2B), **Chapa** (fastest to certify — hosted checkout + webhooks), **M-PESA ET** (STK push), **ArifPay**; CBE Birr via aggregator. Portal invoice payment + POS + payment-link on invoices. Webhook signature verification, idempotent reconciliation to invoices.
- SMS: provider abstraction (Ethio Telecom SMS API / gateway); use cases: order status, delivery notification, expiry-alert digest, payslip notice, OTP for portal. Amharic SMS encoding (UCS-2) handled.

## 8. `vertical_pharma` compliance specifics (EFDA)

- GS1 2D DataMatrix capture on receipt (GTIN + serial + batch + expiry) — scanner-first UX.
- EFDA data exchange: API/XML export of receipts/dispatches per traceability mandate; eRIS reference numbers on import files.
- Import dossier: certificate of competence, product registration, PO approval, clearance docs attached to shipment record; recall report (find every customer who received a batch in minutes).
- FEFO enforcement + configurable expiry alert horizon (DAT default: 3 months) with escalation (email → SMS digest → dashboard flag).

## 9. Filing channels & remittance facts (accountant-verified Jul 2026)

- **Tax filing:** Category A taxpayers file via **etax.mor.gov.et**; other categories file at regional revenue bureaus. The statutory report exports (VAT declaration, WHT summary, PAYE declaration) are designed to transcribe onto either channel.
- **Pension:** POESSA declaration + bank payment slip, within 30 days of month-end.
- **MoR bank beneficiary accounts** (for a future payment-instruction printout feature —
  keep as config data, verify per filing): pension `1000140034057`; VAT & profit tax
  `1000140046047`.

## 10. Verification protocol (applies to everything above)

Before any client go-live: re-verify current rates/thresholds against (1) gazetted proclamations/regulations, (2) MoR practice notes, (3) a local accountant's sign-off. Log verification date in the client manifest. The system displays the effective-date source on every tax/payroll config screen.
