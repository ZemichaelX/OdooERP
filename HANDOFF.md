# HANDOFF — SapianERP project (from Fable 5 → Opus 4.8)

Read this fully before doing anything. You are continuing a well-advanced project with established
working rules. Match the discipline described here — it is why the project has zero failed epics.

## Who / what

- User: Zemichael Muluken (Sapian Technologies PLC, Addis Ababa). Building **SapianERP**: a
  productized, Ethiopia-localized ERP on **Odoo 19 Community** (NOT Enterprise, NOT 18), sold to
  Ethiopian companies with per-client customization. Origin: a real Aug-2025 proposal to DAT
  International Trading PLC (pharma importer) — generalized into a product.
- Repo: `C:\Users\Dell\Desktop\OdooERP\sapianerp` (git; remote: https://github.com/ZemichaelX/OdooERP.git — private, keep it private; verify the push happened: `git log origin/main` vs local).
- Two workstreams: **Claude Code** (desktop app, working dir = the repo) does the building;
  **Cowork chat** does planning, research, reviews of Claude Code checkpoints, documents, and
  drafting the next kickoff prompts. Keep that split.

## Documentation map (precedence matters)

- `sapianerp/CLAUDE.md` — THE operating rules. Non-negotiable. Read first in every Claude Code session.
- `sapianerp/docs/plan-2026/` — v2 master plan (12 files, researched Jul 2026). **Wins on:** strategy,
  pricing, current tax rules (02, 07), customization spec (06), delivery methodology (09), epic order (10).
- `sapianerp/docs/00–06_*.md` — older v1 package. Still valid for task-level detail
  (01_CLAUDE_CODE_BUILD_SPEC, 02_MODULE_REQUIREMENT_SPECS, 03_ARCHITECTURE).
- `OdooERP/` top level: duplicate old docs (ignore), `Tax-Questions-For-You.docx` (accountant
  questionnaire, in review with user's accountant friend), this file.

## Repo state (all verified green as of handoff)

Commits: `74f7910` baseline (Epics 0–2) → `06301cc` Epic 3 → `697595b` Epic A → `e0ba23f` Epic B
→ Epic C (onboarding wizard + sapian_demo_trader) → web-path bug fixes + cleanup/CI/samples
→ pharma vertical session 1 (see CHANGELOG). **BUILD PHASE COMPLETE except client-pitch work.**

Built and container-verified on real Odoo 19 scratch/demo DBs:
- **sapian_core** — module catalog + company Ethiopian fields (TIN etc.), branding hooks.
- **l10n_et_base** (Epic 3) — extends core `l10n_et` chart template ('et', per-xmlid merge; core ships
  some accounts with WRONG types — our overrides fix them, tested). 15% VAT + fiscal positions;
  WHT as negative purchase taxes: 3% goods >20,000 / services >10,000, 30% punitive (no TIN+licence),
  15% foreign digital; effective-dated `l10n.et.wht.config` (incl. `punitive_respects_thresholds`,
  keyword-only, default True — awaiting accountant confirmation) and `l10n.et.cash.cap.config`
  (30,000 ETB, warn/block/off, default warn); partner TIN validation via reference calculator;
  WHT auto-lines on bill posting (idempotent, chatter audit); WHT certificate + branded Ethiopian
  invoice PDF (both via web.external_layout).
- **l10n_et_payroll** (Epics 2+A) — pure-Python reference calculator (PAYE Proc 1395/2025 bands,
  pension 7%/11% Proc 1268/2022, effective-dated configs); `l10n.et.payroll.run` monthly batch
  (generate → confirm & post → reset), payslip input lines (taxable/exempt earnings, post-tax
  deductions), aggregated journal posting (auto-resolved ET accounts, PAY journal), bank CSV
  (name, bank, account, net + TOTAL row), branded payslip PDF, PAYE monthly declaration (employee
  TIN per row) + pension remittance schedule (POESSA ID per row) with red MISSING markers and
  "fix before filing" banners. NOTE: Odoo 19 has no hr_contract — wage lives on
  `employee.current_version_id.wage` (hr.version). We use our own light models, no OCA/Enterprise.

- **vertical_pharma + sapian_demo_pharma** (pharma session 1, Jul 2026 — the DAT pitch module):
  batch discipline (is_pharma ⇒ lot+expiry+FEFO, receipt gate), expiry escalation states +
  one-digest-per-company cron (reference/pharma_calc.py), expired-delivery block/warn,
  GS1 DataMatrix capture (01/17/10/21, day-00 = month end), import dossiers `IMP/...` with
  landed costs, branded batch recall report with customer PHONE + CITY, EFDA export stub.
  Demo tenant "Tena Pharma Import PLC" on scratch_final: 730-day shelf lives, three-stage
  batches, digest pre-fired, recall golden B-123 (Hiwot 120 + Kadisco 80; Bethel got B-124
  only — precision by exclusion), dossier landed-cost golden 2,511,500 ETB.

Quality state (after the 2026-07-06 pre-release review): 90/90 fast pytest goldens
(`pytest tests_fast/`), 133 Odoo tests green in container (l10n_et_base 44, l10n_et_payroll
45, l10n_et_reports 24, sapian_core 14, vertical_pharma 25, sapian_demo_trader 12,
sapian_demo_pharma 9); ruff/black clean, whole-addons pylint-odoo 10.00/10; install AND
uninstall clean on a fresh DB. Accountant config corrections applied (cash cap 50k Art. 81,
allowance exemption engine, pension nationality opt-in) + 19 adversarial-review findings
resolved (18 fixed, 1 deferred fail-safe — see the findings table below).
Odoo 19 test-infra gotchas: HttpCase needs `--workers=0` (odoo.conf ships workers=2); Git Bash
mangles `--test-tags /module` into a Windows path — silent no-op, exit 0 (use MSYS_NO_PATHCONV=1
and check the test-count line); product_expiry auto-fills missing expiry from
`product.expiration_time`, expired quants are unreservable, and receipt-created lots carry no
company_id unless the product does.

**Golden numbers (never change; tests enforce):** basic 10,000 → PAYE 1,650, pension 700/1,100,
net 7,650 · +2,000 taxable OT → PAYE 2,250 on 12,000, pension on basic only, net 9,050 ·
basic 1,800 → PAYE 0, pension 126/198 · 50,000 goods bill (TIN ok) → WHT 1,500 · 15,000 services
no-TIN → 4,500 · 8,000 foreign digital → 1,200 (no threshold) · 10,000 sale → VAT 1,500.

## Working rules that made this project succeed (keep ALL of them)

1. Reference-calculator-first: all tax math in pure Python `reference/` + golden tests in
   `tests_fast/`; Odoo models only call it. Rates/thresholds are effective-dated CONFIG DATA, never code.
2. Container verification before "done": install AND uninstall on scratch DB, demo-flow numbers
   checked against hand-computed goldens, trial balance tie-out.
3. **Checkpoints:** Claude Code pauses at agreed points (e.g., "show test cases before the Odoo
   layer") and the user relays checkpoints to Cowork for review. Cowork reviews critically —
   it has caught real spec risks (punitive-WHT threshold gating) and added requirements
   (employee TIN/POESSA on statutory reports).
4. **NO multi-agent/adversarial review passes** — user is token-constrained. Reserve for pre-release.
   One epic per session, tightly scoped kickoff prompts.
5. Decision ladder for any client-ish request: standardize → configure → extend → custom (rare).
6. Never modify Odoo core/OCA; stable external IDs forever; least privilege on every model.

## Immediate next steps

1. ~~Epic B — l10n_et_reports~~ **DONE (`e0ba23f`)**: VAT declaration + WHT summary, live from
   posted moves, GL tie-out with visible MISMATCH warnings, PDF + CSV, MISSING-TIN markers,
   foreign-provider TIN note, 18 tests, golden-verified vs Epic 3 demo docs (output 1,500 /
   input 10,950 / net −9,450 credit; WHT 7,200 = 1,500+4,500+1,200).
2. ~~Epic C — thin onboarding + demo tenant~~ **DONE**: `sapian.onboarding.wizard` in sapian_core
   (profile/TIN/fiscal year/ETB/logo/primary color/module picks; unattended fresh-DB proof;
   NOTE: module install replaces the registry mid-method — the wizard captures values first,
   installs, finishes on a fresh env) + `sapian_demo_trader` ("Selam General Trading PLC",
   provisioned THROUGH the wizard; July-2026 month exercising every compliance path: 15% VAT
   56,000/8,400, WHT 1,560+4,500+1,200=7,260 with MISSING + N/A(foreign) rows, payroll
   23,800/3,900/18,374 with missing-POESSA banner; all tie-outs green; golden E2E tests re-run
   the exact provisioning code). Gotcha for future work: stock auto-creates warehouses for new
   companies ONLY in test mode — provision explicitly.
3. ~~Pharma vertical session 1~~ **DONE (2026-07-05)**: `vertical_pharma` (compliance core +
   dossiers + recall report; EFDA export stub pending official specs) and `sapian_demo_pharma`
   ("Tena Pharma Import PLC" on scratch_final). This module IS the DAT pitch.
4. **STOP building — sales motion.** Demo the trader tenant AND the pharma tenant (both live on
   `scratch_final`); proposal from the DAT template in docs/plan-2026/01. Build resumes only when
   a client signs.

**Deferred — do NOT build even though specs exist:** pharma session 2 (medicine-request portal,
delivery runs, partner directory, SMS, EFDA live API), other verticals (trading/retail),
payments/SMS (Telebirr/Chapa), e-invoice ITAS, Ethiopian calendar, full white-label/debrand, BI,
biometrics, severance, Amharic payslips.

## Pre-release adversarial review (2026-07-06) — findings table

Three fresh-context reviewer subagents (R1 calculation, R2 security, R3 state-machine)
over all five modules. Every finding confirmed by executed input or refuted; confirmed
findings fixed with regression tests (all green). Two criticals were independently
reported by two reviewers each.

| # | Sev | Finding | Verdict | Resolution |
|---|-----|---------|---------|------------|
| R1#1/R3#1 | critical | Editing an allowance type's ceiling recomputed CONFIRMED (posted) payslips | confirmed | `_compute_amounts` skips `state=='done'` slips; posted month frozen. Test. |
| R1#2 | critical | Each transport line got its own 2,200 ceiling → double exemption, PAYE understated | confirmed (4,400 exempt vs 2,200) | Lines of the same type summed before the split. Test. |
| R3#2 | critical | A confirmed run/payslip could be deleted, orphaning the posted journal entry | confirmed | `@api.ondelete` guards on run + payslip block delete while `done`. Test. |
| R1#3/R3#3 | major | Cash cap blind to sibling payments posted in one batch (two 30k slipped a 50k cap) | confirmed | Check now counts same-batch siblings. Test. |
| R2#1 | major | HR Officer read wage/bank/TIN via the payslip's plain fields (sudo laundering) | confirmed (`hr.version.wage` is manager-restricted) | Payroll run/payslip/input ACLs restricted to `hr.group_hr_manager`. |
| R1#4 | major | No overlap guard on PAYE bands / pension config → order-dependent rate | confirmed | `_check_no_overlap` constraints added to both. Test. |
| R3#4 | major | Un-flagging `is_pharma` dropped existing lots out of every expiry gate | confirmed | `write` blocks clearing the flag while lots exist. Test. |
| R3#5 | major | Clearing a pharma lot's `expiration_date` escaped the delivery gate + digest | confirmed | `@api.constrains` forbids a null expiry on a pharma lot. Test. |
| R1#5 | minor | `split_allowance` could invent a cent on a half-cent 25% ceiling | confirmed (3,000.01 ≠ 3,000) | Round exempt first, remainder is taxable. Fast test. |
| R1#6 | minor | Payroll `_round2` used the broken `+1e-9` nudge (fails at magnitude/negatives) | confirmed | Aligned with the base Decimal half-up rounder. Fast test. |
| R1#7 | minor | Pharma expiry compared UTC date vs local "today" → off-by-one at UTC+3 | confirmed | `_pharma_expiry_local_date` via `context_timestamp`. Test. |
| R2#2 | minor | No multi-company rule on `paye.band` / `pension.config` | confirmed | `ir.rule` added for both. |
| R2#3 | minor | No multi-company rule on `sapian.module.catalog` | confirmed | New `sapian_core` security XML with the rule. |
| R2#4 | minor | CSV formula injection in bank/VAT/WHT exports (supplier/employee names) | confirmed | `csv_safe_cell` neutralizer (pure, numbers exempt). Fast + Odoo tests. |
| R3#6 | minor | `pharma_alerted` never reset, so a relabelled batch was never re-digested | confirmed | Lot `write` re-arms the digest on any expiry change. Test. |
| R3#7 | minor | Stale bank CSV survived a reset-to-draft | confirmed | Reset clears `bank_export_file`. Test. |
| R3#8 | minor | Reset drafted+unlinked a reconciled payroll move | confirmed | Reset blocks when the entry has reconciled lines. Test. |
| R2#5 | minor | `list_db=True` shipped in odoo.conf | confirmed (`.env` is gitignored, not a committed-secret leak) | Default flipped to `list_db=False`. |
| R3#9 | minor | Recall report over-reports because customer RETURNS are not netted | confirmed | **DEFERRED**: over-reporting is fail-safe (a recall must contact everyone); netting returns is a v2 refinement. Documented, not fixed. |

Demo-data bugs (also fixed): sales invoices used the USD default pricelist (→ ETB
pricelist assigned); invoice due date sat before the issue date (→ due date set
explicitly); physical demo goods were not storable (→ `is_storable=True`). All three
now asserted in `sapian_demo_trader` e2e tests.

## Second defensive audit (2026-07-06) — A1–A10 findings table

Independent single-context audit (evidence per finding, reproduced on scratch DBs) of
what the adversarial pass missed: every module + docker/config/scripts/CI. All confirmed
findings fixed this session with regression tests, except A8 (deferred to the deployment
runbook). Fix details in CHANGELOG.

| ID | Sev | Finding | Status |
|----|-----|---------|--------|
| A1 | high | PAYE bands + pension config seeded only for the install-time company; every other company silently used hard-coded rate constants (rule #4 violation; affected both demo tenants + multi-company clients) | **FIXED**: per-company seeding (install `<function>` + `res.company.create` hook + pre-migration for existing DBs); silent fallback removed — missing config now raises naming the company. Regression tests + scratch_final verified (Selam/Tena have real records). |
| A2 | medium | Expiry digest fired once ever per lot — no re-alert when a batch crossed nearing→expired | **FIXED**: `pharma.expiry.alert` markers keyed (lot, company, state); re-alerts on transition. Test. |
| A3 | medium | 133 Odoo integration tests never ran in CI (lint + fast goldens only) | **FIXED**: CI `integration-tests` job (odoo:19.0 + postgres) runs the full suite; red on any failure. |
| A5 | low | Digest de-duplicated shared (company-less) lots across companies via one shared flag | **FIXED**: markers are per company (same model as A2). |
| A4 | low | VAT declaration non-stored compute raised `UserError` off-chart → record unreadable | **FIXED**: returns zero totals + `off_chart` warning banner; never raises on read. Test. |
| A6 | low | Cash-cap check TOCTOU fail-open under concurrent posts | **FIXED**: transaction advisory lock on (company, party, day). Test asserts the lock is held. |
| A7 | low | Import-dossier landed-cost financials writable by any warehouse user | **FIXED**: stock users read-only; write/create → purchase/account managers (new deps). Test. |
| A9 | low | `backup.sh` swallowed filestore-archive failures (`\|\| true`) → false "Backup written" | **FIXED**: aborts non-zero and removes the partial archive on failure. |
| A10 | low | `provision_client.sh` never set a per-tenant `admin_passwd` | **FIXED**: generates a strong secret, writes it to the runtime odoo.conf, prints once. |
| A8 | low | `proxy_mode=True` + dev compose publishes 8069 directly, no TLS | **DEFERRED**: documented in `docker/README.md` (nginx/TLS reverse proxy is a go-live runbook step). |

Refuted during the audit (not reported): `account.payment` state filter (correct Odoo 19
post-states); multi-company `ir.rule` domains (correct global-rule pattern); `docker/.env`
(gitignored, untracked — no committed secret); sudo usage (narrow, documented, manager-gated);
no controllers/public routes/`t-raw`/raw SQL anywhere.

## Open loops (track these)

- ~~Accountant review Q5 (punitive threshold gating, either/both TIN+licence) + cash cap~~
  **ANSWERED & APPLIED (2026-07-06)**: punitive 30% when EITHER TIN or licence missing;
  thresholds gate ALL WHT (config default confirmed, kept); cash cap 50,000 Art. 81
  (single or same-day aggregate); allowance exemption engine + pension nationality opt-in.
  Still open: Q10 — real filed MoR form samples to match report ROW LAYOUTS (report tweak,
  not rework).
- Print 5 demo PDFs for the accountant — DONE earlier (samples/, 7 PDFs). Re-render after the
  Q10 layout match if the forms differ.
- `scripts/provision_client.sh` must write a real `admin_passwd` into odoo.conf at deploy (known
  gap). Related: odoo.conf now ships `list_db = False` (R2#5); the provision script should keep
  it False and set a per-tenant `admin_passwd`.
- Old `Accountant-Review-Questions.docx` at OdooERP top level can be deleted (superseded).
- ~~One adversarial review pass of l10n_et_base + payroll (deferred)~~ **DONE (2026-07-06)** —
  3-reviewer pass over all five modules; findings table above; all fixed but the fail-safe
  recall-returns netting (R3#9, deferred to pharma session 2). Re-verify rates vs gazetted
  proclamations remains a per-go-live step.
- VAT on imported services is modeled as ordinary input VAT in demo data; real treatment is
  likely reverse-charge — confirm with accountant before first client with foreign service
  purchases. No code change now.
- Selam demo tenant lives on local DBs `scratch_final` (primary, manually UI-tested) and
  `scratch_bugfix`/`scratch_epicC3` (regression copies). Onboarding wizard web-path bugs
  fixed 2026-07-04 (see CHANGELOG): container tests don't exercise web dispatch — for
  wizard-like flows, verify over HttpCase AND live XML-RPC before calling it done.
- Pharma demo tenant "Tena Pharma Import PLC" installed on `scratch_final` (and `scratch_base`).
  Admin can company-switch into it; the expiry digest activity is pre-fired. If the tenant sits
  unused for months, the "nearing" batch (CO-88, +45 days at provisioning) will drift into
  "expired" — rebuild by dropping the Tena company + reinstalling sapian_demo_pharma, or accept
  the drift (states recompute live).
- EFDA traceability export is a stub by design; GS1 capture side is done, so the export becomes
  an adapter once EFDA publishes transport specs — quote it as a small paid change order.

## Tone with the user

Direct and concise (his stated preference). He relays Claude Code checkpoints into chat — review
them substantively, approve/correct with paste-ready reply blocks. He values being told what NOT
to build as much as what to build.
