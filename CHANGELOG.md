# Changelog

All notable changes to SapianERP. Epics per `docs/plan-2026/10-claude-code-roadmap.md`.

## [Unreleased]

### Ops hardening — backup/restore drilled end-to-end ✅ (2026-07-26)
Ops-layer-only session (no addons changes): the backup/restore path is now
drilled, not just written. All seven fixes verified by a real restore drill.
- `restore.sh`: the filestore phase used to `compose exec` into the odoo
  container the script had just STOPPED — impossible, and with `set -e` the
  abort landed after the DB was dropped/restored but before odoo restarted
  (tenant DB-only, filestore missing, Odoo down). Filestore now restores via
  throwaway `compose run --rm --no-deps` containers on the same `odoo-data`
  volume; all input validation happens before anything destructive; on any
  failure odoo deliberately stays STOPPED with an explicit known-state
  message (a half-restored tenant must never serve traffic). Also: the
  archive's top-level dir is renamed on extraction (`tar --transform`) so
  restoring under a different db name still gets its filestore.
- `provision_client.sh`: the generated `admin_passwd` was appended to the
  git-tracked `config/odoo.conf` (one `git add -A` away from committing a
  tenant master password, and compose mounted the same tracked file). Secrets
  now go to gitignored `config/odoo.runtime.conf` — created from the template
  if missing — which is what `docker-compose.yml` mounts; the tracked
  template stays clean (`git status` verified clean across a provision run).
  Deploy step documented in `docker/README.md`.
- `backup.sh`: `pg_dump` gets the same fail-guard + partial-file cleanup the
  filestore path already had (A9); every dump is verified restorable with
  `pg_restore --list` before success is reported; retention pruning matches
  the exact database (`NAME_[0-9]*`), so backing up `sapian` can no longer
  delete `sapian_prod_*` archives (regression-tested with aged files).
- `.env` location fixed everywhere: compose's project directory is `docker/`
  (it is invoked `-f docker/docker-compose.yml`), so the documented repo-root
  `.env` was never read and `${DB_PASSWORD:?}` aborted all scripts. The file
  now lives at `docker/.env`; CLAUDE.md, README.md and docker/README.md
  corrected.
- `dress_rehearsal.sh`: drops its target DB only after a typed-name
  confirmation (same guard as restore.sh), and exits non-zero when the
  reconciliation exam fails (`EXAM_VERDICT` sentinel — odoo shell always
  exits 0), so it can gate a release unattended.
- All four scripts resolve the repo root from their own location
  (`BASH_SOURCE`), so cron/Task Scheduler invocations work from any cwd, and
  all are executable (mode 100755) on a fresh clone.
- Restore drill (this session, containerized Odoo 19): `backup.sh` on the
  Selam demo tenant (dump passed `pg_restore --list`, filestore 2,372 files)
  → `restore.sh` onto `scratch_restore_drill` → on the restored DB all
  July-2026 goldens hold (VAT base 56,000 / output VAT 8,400; WHT 7,260;
  payroll gross 23,800 / PAYE 3,900 / net 18,374), the company logo reads
  back from the restored filestore and a payslip PDF renders. Fast goldens
  90/90 before and after.
- Known issue found while drilling (NOT fixed here — follow-up session):
  commit `66c21cc`'s catalog expansion broke unattended fresh-DB demo
  provisioning — `sapian_demo_trader._onboard_company` hands the wizard every
  catalog entry, the eight new optional apps are not in its manifest deps, so
  the wizard hits `button_immediate_install` during registry init and demo
  install fails (and with `website_sale` installed, archiving the placeholder
  company is blocked by the auto-created website). Fix: demo picks only the
  core/common tiers, or add the optional apps to the demo manifest.

### Onboarding catalog — offer the standard Odoo Community apps ✅ (2026-07-09)
`sapian.module.catalog` STANDARD_CATALOG grows from 7 to 15 entries. Added the
stock Odoo 19 Community apps that had no Ethiopian layer and were previously
reachable only via the raw Apps menu, as `optional`-tier entries: CRM (`crm`),
Manufacturing (`mrp`), Project (`project`), Email Marketing (`mass_mailing`),
Fleet (`fleet`), Repair (`repair`), Maintenance (`maintenance`), and
Website & eCommerce (`website_sale`). Tier drives pre-selection, so the
onboarding wizard still pre-ticks only the `core` tier — the optional apps are
offered but never auto-installed. No new Ethiopian customization for these yet.
Catalog-count tests updated 7 → 15.

### Ops scripts — Windows-safe backup, restore, et-chart provisioning ✅ (2026-07-07)
Two commits (`51f3456`, `85d5f05`) hardening the operations layer:
- `backup.sh`: disable Git Bash MSYS path conversion (it mangled the
  container-absolute filestore path on Windows and aborted the backup; no-op on
  Linux/CI). New optional `[offsite_dir]` + `[retention_days]` args: after a
  successful DB+filestore backup, both archives are copied to a synced folder
  (e.g. OneDrive) for an off-site copy, with retention pruning in both
  locations; off-site failure aborts loudly (A9). Machine-specific paths stay
  out of the repo (local Task Scheduler `.cmd` wrapper).
- `restore.sh`: new companion script — drops/recreates the DB from a `pg_dump`
  and restores the filestore, with a typed confirmation guard.
- `provision_client.sh`: two-phase provisioning (base → set company country →
  install modules) so new tenants land on the Ethiopian 'et' chart instead of
  `generic_coa`, which Odoo won't let you switch afterwards.
- `backups/.gitignore`: never commit tenant data dumps.

### Dress rehearsal — full-month simulation + independent exam ✅ (2026-07-07)
New `sapian_dress_rehearsal` module: a rerunnable pre-release ritual that
provisions a fresh tenant through the onboarding wizard, drives one realistic
month (August 2026) of business through the REAL flows, then proves the books
with an exam that recomputes every figure by a path independent of what it
checks.
- The month: 25 sales orders (3 partial deliveries → backorders, 1 return +
  credit note; invoiced on ordered qty so VAT is decoupled from delivery),
  12 purchases (10 goods POs feeding stock, mix above/below the 20,000 WHT
  threshold; 2 direct service bills — no-TIN domestic 30%, foreign digital
  15%), a 5-employee payroll run (incl. a transport allowance capped at 25%
  of 6,000 = 1,500 and a pension-exempt foreigner), several bank payments +
  one vendor CASH payment near the 50,000 cap, and one inventory adjustment.
- The exam (all green): trial balance (48 balanced moves, debits==credits
  2,814,155), VAT (15% × 397,000 base = output 59,550; input 186,090; ties to
  GL), WHT (per-bill recompute 34,950 @3% + 3,000 @15% + 12,000 @30% = 49,950;
  ties to WHT-payable GL), payroll (5 payslips recomputed from CONFIG-sourced
  bands/rates — PAYE 11,650, pension EE 2,905), stock (on-hand per product =
  received − delivered ± adjustment vs quant, incl. the −5 Teff shrinkage).
- 3 role walkthroughs over HTTP (HttpCase): warehouse receive, accountant
  bill-with-WHT (3% auto-applied), HR payroll confirm.
- `scripts/dress_rehearsal.sh` rebuilds `scratch_rehearsal` from empty, runs
  the month and prints the reconciliation table; the tenant is kept for
  manual click-through. 6 Odoo tests (TransactionCase + HttpCase); lint 10.00.

### Defensive-audit fixes — A1–A10 (2026-07-06)
Second, independent defensive audit (single-context, evidence-per-finding) over all six
modules + docker/config/scripts/CI. All confirmed findings fixed with regression tests;
A8 deferred to the deployment runbook. Findings table in HANDOFF.md.

- **A1 (high) — per-company PAYE/pension config.** PAYE bands + pension config used to be
  seeded (via XML `<record>`s) only for the company active at module install; every other
  company (a group's 2nd company, the demo tenants, a SaaS tenant) silently fell back to
  hard-coded rate constants in the compute helper. Now seeded PER COMPANY from the reference
  calculator — install `<function>`, `res.company.create` hook, and a pre-migration that
  detaches the legacy xmlid records so existing DBs keep them while every other company is
  filled in. The silent `DEFAULT_PAYE_BANDS`/`0.07`/`0.11` fallback is REMOVED: a company
  with no applicable config now raises a clear `UserError` naming the company and date.
  Regression tests prove new companies are seeded, missing config raises, and the 10,000
  golden (1,650/700/7,650) comes from the records (editing a band moves PAYE).
- **A2+A5 (medium) — pharma expiry digest.** The single `pharma_alerted` boolean meant a
  batch was digested once ever (no re-alert when it crossed nearing→expired) and shared,
  company-less lots were de-duplicated across all companies. Replaced with a
  `pharma.expiry.alert` model keyed (lot, company, state): re-alerts on state transition,
  per company. Digest takes an injectable `today` for testing. Test: a batch alerted while
  nearing gets a second digest entry when it later expires.
- **A3 — CI runs the Odoo integration suite.** New GitHub Actions job (odoo:19.0 container +
  postgres service) installs the demo tenants with demo data and runs the full
  `--test-enable` suite; CI is red on any test failure.
- **A4 (low) — VAT declaration no longer raises on read.** An off-chart company made the
  non-stored totals compute raise `UserError`, breaking list/form views. It now returns zero
  totals with an `off_chart` warning state surfaced as a form banner.
- **A6 (low) — cash-cap concurrency.** The daily-cap check was a TOCTOU fail-open under
  concurrent posts. Added a transaction advisory lock keyed on (company, party, day) so
  concurrent posts to the same party serialize; documented in the model.
- **A7 (low) — import-dossier least privilege.** Landed-cost financials were writable by any
  warehouse user. Warehouse users are now read-only; write/create is limited to purchase
  managers, full access to account managers (vertical_pharma now depends on purchase+account).
- **A9 (low) — backup.sh** exits non-zero and removes the partial archive if the filestore
  backup fails (no more silent "Backup written" on partial success).
- **A10 (low) — provision_client.sh** generates a strong per-tenant `admin_passwd`, writes it
  into the runtime `odoo.conf`, and prints it once for the vault (idempotent).
- **A8 (low, deferred)** — `proxy_mode=True` with the dev compose publishing 8069 directly and
  no TLS. Documented in `docker/README.md` as a go-live runbook step (nginx/TLS reverse proxy);
  no code change.

### Pre-release hardening — accountant corrections + adversarial review ✅ (2026-07-06)
Two phases; the exception to the no-multi-agent rule (final pre-release pass).

**Phase 1 — accountant-verified config corrections (Jul 2026 review):**
- Cash cap 30,000 → **50,000 ETB** (Art. 81, Proc 1395/2025, cross-verified vs KPMG's
  proclamation copy). Semantics: single transaction OR same-day aggregate per party,
  whichever hits first — the aggregate check covers the single-transaction case. Goldens
  updated; an upgrade hook corrects DBs still on the old 30k default (customized caps
  untouched); warning text reworded.
- **Allowance exemption engine** (`l10n.et.allowance.type`, seeded per company with source
  notes): transport exempt up to the LOWER of 2,200/month or 25% of basic (excess taxable,
  computed — golden salary 10,000 + transport 3,000 → exempt 2,200, taxable 800, PAYE 1,890);
  hardship + actual-cost medical exempt; housing + position taxable. Payslip input lines link
  to a type; the rule computes the split. Per-diem documented as an evidence-based input line.
- **Pension nationality rules**: mandatory for Ethiopian nationals, voluntary for foreign
  nationals of Ethiopian origin (opt-in flag on the employee), excluded for other foreigners.
- WHT defaults confirmed (either TIN or licence missing → 30%; thresholds gate all WHT);
  anti-avoidance note added to the reports README. Docs (plan-2026/07, CLAUDE.md tax-facts,
  HANDOFF) updated with VAT carry-forward default, Reg 570/2025 EFD+QR mandate, filing
  channels and MoR beneficiary accounts.

**Phase 2 — 3-reviewer adversarial pass (R1 calc, R2 security, R3 state-machine) over all
five modules; every finding confirmed by executed input or refuted; 18 fixed with regression
tests, 1 deferred (fail-safe). Full findings table in HANDOFF.md.** Highlights:
- critical: allowance-ceiling edit rewrote confirmed payslips (now frozen); each transport
  line got its own monthly ceiling → double exemption (now summed per type); confirmed
  run/payslip deletable → orphaned journal (ondelete guards).
- major: cash cap blind to same-batch siblings; HR Officer read wages/bank/TIN via the payslip
  (ACLs restricted to HR manager); no PAYE-band/pension overlap guard; un-flagging is_pharma or
  clearing a lot's expiry escaped the expiry gates (constraints added).
- minor: allowance half-cent rounding; payroll rounder aligned to Decimal half-up; pharma
  expiry UTC/local off-by-one; multi-company rules on paye.band/pension.config/module.catalog;
  CSV formula-injection neutralizer on all exports; digest re-arm on expiry relabel; bank file
  cleared on reset; reset blocked on a reconciled move; `list_db=False` default.
- deferred (fail-safe): recall report doesn't net customer returns (over-reports; a recall must
  contact everyone) — pharma session 2.
- Demo-data bugs fixed: sales invoices now ETB (were USD default pricelist); invoice due date
  no longer precedes the issue date; physical demo goods are storable. Asserted in e2e tests.
- Result: 90 fast goldens + 133 Odoo tests green; install/uninstall clean; lint 10.00; the
  live demo DB (`scratch_final`) upgraded in place (cash cap corrected, allowance types seeded).

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

### Project skill — Fable 5 prompting guide ✅ (2026-07-04)
`.claude/skills/fable5-prompting/SKILL.md` (`ad9cf37`): a project skill for
drafting/reviewing kickoff prompts, system prompts and agent instructions
tuned to Claude Fable 5 — token-conscious session design for this repo's
Claude Code workflow. Tooling only; no product code.

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
