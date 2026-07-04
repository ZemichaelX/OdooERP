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
→ Epic C (onboarding wizard + sapian_demo_trader; see CHANGELOG). **BUILD PHASE COMPLETE.**

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

Quality state: 67/67 fast pytest goldens (`pytest tests_fast/`), 33 Odoo tests (l10n_et_base) +
21 (payroll) green in container, ruff/black clean, whole-addons pylint-odoo 10.00/10.

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
3. **BUILD PHASE COMPLETE — STOP building.** The sellable Payroll+HR wedge and Essential/Business
   core exist and are demo-able (install `sapian_demo_trader` with demo data). Sales motion next
   (demo the trader tenant, proposal from the DAT template in docs/plan-2026/01). Deferred list
   unchanged; build resumes only when a client signs.

**Deferred — do NOT build even though specs exist:** verticals (pharma/trading/retail), payments/SMS
(Telebirr/Chapa), e-invoice ITAS, Ethiopian calendar, full white-label/debrand, BI, biometrics,
severance, Amharic payslips.

## Open loops (track these)

- Accountant review out with a friend (`Tax-Questions-For-You.docx`). Critical answers: Q5 —
  does punitive 30% apply below 20k/10k thresholds (config flag ready to flip) and either-or-both
  TIN/licence; Q10 — real filed form samples to match report layouts. Answers arrive as CONFIG
  changes + report-layout tweaks, not rework.
- Print 5 demo PDFs for the accountant (payslip, PAYE declaration, pension schedule, invoice,
  WHT certificate) — one small Claude Code task: "render demo documents to samples/".
- Verify GitHub push completed (user was given the PowerShell commands).
- `scripts/provision_client.sh` must write a real `admin_passwd` into odoo.conf at deploy (known gap).
- Old `Accountant-Review-Questions.docx` at OdooERP top level can be deleted (superseded).
- Pre-first-client: re-verify all rates vs gazetted proclamations + accountant sign-off; one
  adversarial review pass of l10n_et_base + payroll (deliberately deferred).
- VAT on imported services is modeled as ordinary input VAT in demo data; real treatment is
  likely reverse-charge — confirm with accountant before first client with foreign service
  purchases. No code change now.
- Selam demo tenant lives on local DBs `scratch_final` (primary, manually UI-tested) and
  `scratch_bugfix`/`scratch_epicC3` (regression copies). Onboarding wizard web-path bugs
  fixed 2026-07-04 (see CHANGELOG): container tests don't exercise web dispatch — for
  wizard-like flows, verify over HttpCase AND live XML-RPC before calling it done.

## Tone with the user

Direct and concise (his stated preference). He relays Claude Code checkpoints into chat — review
them substantively, approve/correct with paste-ready reply blocks. He values being told what NOT
to build as much as what to build.
