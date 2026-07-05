# Changelog

All notable changes to SapianERP. Epics per `docs/plan-2026/10-claude-code-roadmap.md`.

## [Unreleased]

### Pharma vertical, session 1 — vertical_pharma + sapian_demo_pharma ✅ (2026-07-05)
The DAT International pitch module (docs/plan-2026/07 §8, 05; behavior per the
client's own requirements in docs/01-proposal-extraction.md §8.1).
- **vertical_pharma** (13 Odoo tests incl. an HttpCase web-dispatch test; 12 new
  fast goldens → 79 total):
  - Batch discipline: `is_pharma` flag forces lot tracking + expiry + the FEFO
    "Pharmaceuticals" category (constraint-guarded); receipts without an
    expiration date on a pharma batch cannot validate.
  - Expiry engine (`reference/pharma_calc.py`): fresh → nearing expiry →
    expired against a per-company horizon (default 90 days; golden: expiry
    2026-09-25 alerts FROM 2026-06-27, not before; expiry date = last usable
    day). Daily cron posts ONE digest activity per company (anchored on the
    most urgent batch, assigned to a stock manager), each batch reported once.
  - Expired-lot delivery policy per company: block (default, UserError with
    batch details — verified through web RPC dispatch) or warn + audit note.
  - GS1 DataMatrix capture on receipt lines: AIs 01/17/10/21, day-00 = month
    end, serials parsed not persisted (v1); mis-scans warn and fill nothing.
  - Import shipment dossiers (`IMP/...` sequence): supplier, ETA, status,
    clearance notes + chatter docs, landed-cost fields with computed total;
    linked to receipts, batches derived; menu under Inventory; multi-company
    record rule + stock-group ACLs.
  - Batch recall report (button on the lot, `web.external_layout`): every done
    customer delivery of the batch with date, quantity and the customer's
    PHONE + CITY (a recall means calling people); import-dossier traceability
    printed; golden: B-123 → exactly two customers with different dates/
    quantities, third customer excluded (received B-124 only).
  - EFDA traceability export: deliberately a stub pending official specs.
- **sapian_demo_pharma** (7 Odoo tests): "Tena Pharma Import PLC" — six
  medicines (Amharic+English, realistic 730-day shelf lives so a live pitch
  receive can't create an instantly-expired lot), batches at all three expiry
  stages, digest PRE-FIRED (the pitch shows the alert, not a description),
  dossier IMP/2026/0001 landed-cost golden 2,511,500 ETB, and the recall-ready
  flow (Hiwot 120 + Kadisco 80 exhaust B-123 so Bethel's 60 FEFO-reserves
  B-124). Installed on `scratch_final` alongside Selam.
- Odoo 19 gotchas learned (tests now encode them): product_expiry AUTO-FILLS
  missing expiry from `product.expiration_time`; expired quants are
  unreservable (forcing a lot on a manual move line is the only path our
  delivery gate must catch); receipt-created lots carry NO company_id unless
  the product does; `res.groups.users` → `all_user_ids`; stock.warehouse has
  no activity mixin; HttpCase needs `--workers=0` (odoo.conf ships workers=2);
  Git Bash mangles `--test-tags /module` (use MSYS_NO_PATHCONV=1).

### Cleanup — demo polish, catalog truth, CI, samples ✅ (2026-07-04)
- Demo login: provisioning archives ALL Odoo placeholder companies (incl. the
  original main company) and points admin (and every stranded user) at the real
  companies — a fresh login on the demo DB lands in Selam with a clean company
  switcher. Wizard shows a prominent "You are onboarding: <company>" banner
  (users had onboarded a placeholder by accident).
- Module catalog: Enabled is now explicitly a STATUS mirror of the installed
  modules — re-synced by a data <function> on every sapian_core upgrade and on
  demand via a list-header button; the misleading enable/disable toggle is
  gone (module installation happens via the onboarding wizard; managed
  per-company uninstall stays deferred). Sync counts 'to upgrade'/'to install'
  as installed — the upgrade-graph race was exactly the reported drift. List
  defaults to the current company; search/group-by added.
- CI: GitHub Actions workflow (lint: ruff/black/pylint-odoo; fast reference
  goldens; XML/CSV/manifest validation). The Odoo integration suite stays
  local per CLAUDE.md (documented in the workflow).
- samples/: seven accountant-review PDFs rendered from the live Selam tenant
  (payslip, PAYE declaration, pension schedule with the MISSING-POESSA banner,
  customer VAT invoice, WHT certificate, VAT declaration, WHT summary). Docker
  image now bundles the Abyssinica SIL font so Amharic renders in PDFs
  (bilingual names printed as boxes before).
- Housekeeping: disposable scratch DBs dropped; `scratch_final` documented as
  THE demo DB (README: login flow, rebuild command).

### Bug fix — onboarding wizard web path ✅ (2026-07-04)
Found by manual browser testing (container tests never exercised web dispatch);
reproduced and verified over XML-RPC against a live server.
- Root cause #1: applying to a company with existing accounting crashed on the
  ETB currency write ("cannot change the currency … journal items exist") and
  rolled the whole onboarding back → "lost" name/TIN/logo/color. Currency and
  chart-'et' loading are now guarded (skip + warning on the company partner's
  chatter); chart 'et' is only loaded on companies WITHOUT a chart.
- Root cause #2: the wizard dialog stayed the web client's restorable URL
  action → reopened on refresh/company switch, blank screen on close. Apply and
  Cancel now both redirect to the apps home (`/odoo`), which also reloads the
  new company identity (name/logo/color) immediately.
- Post-install writes are committed explicitly after the mid-install registry
  swap (module installation already committed once; a later failure can no
  longer take the post-install writes down).
- `res.company.sapian_onboarding_done` completion flag; the onboarding menu is
  now a router: wizard while not onboarded, module catalog afterwards (admin-
  only menu). Reopening prefills all values from the company — re-applying can
  never silently erase branding.
- Logo validated at the wizard with Odoo's own image pipeline (exactly what
  `res.company.logo` accepts) — bad files fail early with a clear message.
- Demo cleanliness: provisioning archives the core demo companies ("My US
  Company", "My Company (Chicago)"); the switcher shows only real companies.
- 4 new HttpCase browser-path tests (apply persistence + redirect, prefill,
  cancel, menu router); full suite now 90 integration + 67 fast.

### Epic C — onboarding wizard + demo trader tenant ✅ (2026-07-04) — BUILD PHASE COMPLETE
- `sapian_core` v2: `sapian.onboarding.wizard` — company profile (name, TIN,
  address, fiscal year calendar/Ethiopian, ETB), light branding (logo + one
  primary color; external-layout reports and login pick them up natively),
  module picks from a self-seeding standard catalog (7 sellable entries),
  installs the picked modules and applies Ethiopian defaults via the existing
  loaders. Proven unattended on a fresh sapian_core-only DB; idempotent re-run.
  Registry-replacement mid-install handled explicitly (capture → install →
  fresh env).
- `sapian_demo_trader` (new, demo-only): "Selam General Trading PLC" provisioned
  THROUGH the wizard, one July-2026 month of transactions via the real flows —
  quotation → delivery → 15% VAT invoices (56,000 base / 8,400 VAT); PO →
  receipt → bill with 3% WHT (52,000 → 1,560); punitive 30% no-TIN bill
  (4,500, red MISSING row) and 15% foreign digital bill (1,200, "N/A (foreign)");
  posted payroll (23,800 gross / 3,900 PAYE / 18,374 net, one employee missing
  a POESSA ID for the banner) + bank file; July VAT declaration (net −2,850
  credit) and WHT summary (7,260) pre-created, all GL tie-outs green.
- 14 new integration tests: the golden E2E re-runs the exact provisioning code
  and pins every hand-computed number. Fixed en route: stock only auto-creates
  warehouses for new companies in test mode — provisioning creates it
  explicitly.
- **The sellable Payroll+HR wedge and the Essential/Business ERP now exist,
  demo-able end to end. Next: sales, not code.**

### Epic B — `l10n_et_reports` statutory reports slice ✅ (2026-07-04)
- New addon (depends `l10n_et_base`; core l10n_et tax codes + WHT kind markers
  reused, nothing duplicated): monthly VAT declaration (output 15%/zero-rated/
  exempt, input VAT, net payable or credit carried forward) and WHT summary
  (per-bill rows with supplier TIN, totals by rate, grand total).
- Reports are LIVE period windows over posted journal items (reprint after a
  correction → current numbers; refunds net out). Both carry GL tie-out rows
  against the accounts the taxes post to (300700/221200/300600); a manual
  posting that bypasses the tax engine renders a visible MISMATCH warning —
  tested with a rogue-entry regression test.
- Branded PDFs via web.external_layout + CSV exports for both; MISSING-TIN
  markers and fix-before-filing banners (Epic A pattern); 30-day remittance
  note; foreign digital providers excluded from the missing-TIN warning with
  an on-report note ("foreign providers: no local TIN required").
- Golden-verified against the Epic 3 demo docs: output 1,500 / input 10,950 /
  net −9,450 credit; WHT {3%: 1,500, 30%: 4,500, 15%: 1,200} = 7,200, all
  tie-outs green. 18 integration tests; install/uninstall/reinstall verified.
- Layout caveat: computations exact; verify row layout against the current MoR
  forms before filing (README).

### Epic A — `l10n_et_payroll` payroll workflow completion ✅ (2026-07-02)
- Monthly payroll runs on core `hr` (Odoo 19 has no hr_contract/hr_payroll:
  own light models; wages from `hr.version`): payslip generation, manual input
  lines (taxable/exempt earnings, post-tax deductions), freeze-on-confirm.
- Aggregated payroll journal posting to an auto-created `PAY` journal with
  per-company account config auto-resolved from the Ethiopian chart (golden:
  10,000 basic → expenses 11,100; payables 1,650 PAYE + 1,800 pension + 7,650
  net; balanced). Idempotent confirm/reset with chatter audit trail.
- Employee statutory identifiers: TIN (validated via the l10n_et_base reference
  calculator) + POESSA pension ID; statutory reports warn on missing ones.
- Generic bank salary transfer CSV (name/bank/account/net + totals row).
- QWeb reports (EN, `web.external_layout`): payslip PDF, PAYE monthly
  declaration (TIN per row), pension remittance schedule (POESSA ID per row).
- Fixed en route: pension config now effective-date filtered in the compute
  helper (was latest-record); Odoo 19 `_sql_constraints` → `models.Constraint`
  (payroll + sapian_core); sapian_core deprecated `name_get` removed; manifests
  cleaned. 21 integration tests; demo payroll (3 employees, one missing pension
  ID for the warning path) on the ET demo company; install/uninstall/reinstall
  verified.

### Epic 3 — `l10n_et_base` Ethiopian accounting localization ✅ (2026-07-02)
- Reference calculators (`addons/l10n_et_base/reference/et_tax_calc.py`, pure Python,
  no Odoo): WHT applicability + amount (3% goods > 20k / services > 10k, punitive 30%,
  foreign digital 15%, `punitive_respects_thresholds` config flag), Proc 1395/2025
  daily cash-payment cap check, Ethiopian TIN format validation. 45 golden tests in
  `tests_fast/`, adversarially verified (mutation-tested coverage).
- Odoo module extending the core `l10n_et` chart template `'et'`:
  - CoA additions (PAYE Payable 300900, Customs Duty Clearing 230200) and
    account-type fixes for the mistyped core VAT/WHT accounts (3006/3007/3008 →
    liabilities, 2212/2213/2214 → assets) — core files untouched.
  - Automatic WHT lines on vendor bills at post time, driven by the effective-dated
    `l10n.et.wht.config` (rates/thresholds/punitive-gating flag, source notes) and
    the reference calculator; idempotent on re-post; chatter audit trail.
  - Zero-rated + VAT-exempt fiscal positions mapped onto the core 15% VAT taxes.
  - `l10n.et.cash.cap.config` (warn/block/off) enforcing the ETB 30,000/party/day
    cash cap on outbound cash payments.
  - Partner compliance fields (TIN validated + normalized via the reference calc,
    VAT reg. no., business licence no./expiry, foreign-digital flag, Amharic name);
    commercial-field propagation; finance-only partner tab.
  - Printable WHT certificate and Ethiopian VAT invoice (QWeb, EN).
  - Security: access rules + multi-company record rules for both config models.
  - Demo data: 3 partners + posted documents exercising every tax path.
  - 33 Odoo integration tests (golden postings, effective dating, cash cap,
    reports); verified install → uninstall → reinstall on a scratch DB with demo;
    trial balance clean.
- Tooling: `ruff.toml`, `pyproject.toml` (black, line-length 96), `.pylintrc`
  (pylint-odoo 10/10); fixed `config/odoo.conf` inline comments that broke the
  Odoo 19 config parser; payroll import-order lint fixes.

### Revised build order (July 2026, token-conscious — supersedes docs epic order)
Next: Epic A payroll workflow completion → Epic B statutory reports slice →
Epic C thin onboarding + demo tenant. Verticals, payments/SMS, e-invoice,
Ethiopian calendar, full theme, BI deferred until a client signs.

## Baseline (Epics 0–2, ported from the starter repo)

- Repo skeleton: `docker/`, `config/`, `scripts/`, `data-templates/`, `docs/`
  (incl. the July-2026 `docs/plan-2026/` master-planning package).
- `sapian_core`: module catalog model + company defaults (S0-4/S1-1/S1-2).
- `l10n_et_payroll`: PAYE (Proc 1395/2025) + pension (Proc 1268/2022) engine with
  effective-dated rate models and a pure-Python reference calculator — 22 golden
  tests (basic 10,000 → PAYE 1,650 / pension 700 / net 7,650).
