# CLAUDE.md — SapianERP

## What this project is
A configurable ERP product for Ethiopian companies, built as custom Odoo 19 Community
addon modules. Two module families:
- `l10n_et_*` : reusable Ethiopian localization (tax, payroll, calendar, Amharic, compliance)
- `sapian_*`  : product features (onboarding, theme, dashboards, integrations)

Each client runs an isolated Dockerized Odoo instance. Design every module to also work
in a future multi-tenant SaaS (no hard-coded company assumptions; respect `company_id`).

## Absolute rules
1. NEVER modify Odoo core. Extend via Python inheritance (`_inherit`) and XML view
   inheritance (`xpath`) only. All product code lives in `addons/`.
2. One responsibility per module. Every model field, method, and view ships with a
   test and a docstring.
3. Respect multi-company: filter by `company_id`; never leak data across companies.
4. Tax rates, PAYE bands, pension %, thresholds are CONFIGURATION DATA in dedicated
   config models / data files with effective dates — NEVER hard-coded in business logic.
   Changing a future rate must never alter historical payslips/entries.
5. Money uses Odoo currency rounding utilities, never naive floats.
6. Secrets (SMTP, Telebirr keys, DB creds) come from environment variables, never committed.
7. All user-facing strings use Odoo translation (`_()`), so Amharic can be added.
8. Least privilege: define security groups + `ir.model.access.csv` (+ record rules where
   multi-company/portal-exposed) for every new model.
9. Do not add a Python dependency without noting it in the module manifest.
10. Business logic testable without a running Odoo (e.g. tax math) lives in a plain-Python
    `reference/` file with pytest tests, and the Odoo model calls it.

## Repo layout
- addons/          custom modules (l10n_et_*, sapian_*)
- docker/          Dockerfile, docker-compose
- config/          odoo.conf template (no secrets)
- scripts/         provisioning, backup helpers
- data-templates/  spreadsheet import templates for onboarding
- docs/            architecture & module docs (the master planning package)

## How to run locally
    cp .env.example docker/.env   # set DB_PASSWORD etc. (compose's project dir
                                  # is docker/, so it reads docker/.env)
    cp config/odoo.conf config/odoo.runtime.conf   # runtime config compose mounts
                                  # (gitignored; provision_client.sh adds admin_passwd)
    docker compose -f docker/docker-compose.yml up -d
    # open http://localhost:8069

Install / update modules:
    docker compose -f docker/docker-compose.yml run --rm odoo \
      odoo -d sapianerp -i sapian_core,l10n_et_payroll --stop-after-init

Run Odoo module tests:
    docker compose -f docker/docker-compose.yml run --rm odoo \
      odoo -d sapianerp -u l10n_et_payroll --test-enable --stop-after-init

Run the fast pure-Python payroll tests (no Odoo needed):
    pytest addons/l10n_et_payroll/reference/

## Definition of Done (every task)
- Tests pass (pytest reference tests + Odoo module tests where relevant)
- Lint clean (ruff, black, pylint-odoo)
- Security/access rules defined for new models
- Strings translatable; Amharic .po updated if user-facing
- Module README updated; no changes to Odoo core

## When unsure
Prefer configuration over code. Prefer extending an existing Odoo app over a new one.
Re-verify tax/PAYE/pension figures against the Ministry of Revenue before a payroll go-live.

## Build backlog
Implemented so far: repo skeleton (S0), sapian_core starter (S0-4/S1-1/S1-2),
l10n_et_payroll PAYE + pension engine (S1-7/S1-8) with tests, l10n_et_base
Ethiopian accounting (Epic 3: extends core l10n_et chart 'et'; WHT automation
3%/30%/15% with effective-dated config incl. punitive_respects_thresholds flag;
cash cap warn/block; partner TIN/licence compliance; WHT certificate + ET VAT
invoice reports; 33 Odoo tests + 45 fast goldens), Epic A payroll workflow
(l10n_et_payroll v2: batch runs on hr.version wages — no hr_contract in Odoo 19;
input lines; aggregated PAY-journal posting; bank CSV; payslip PDF; PAYE
declaration + pension remittance with missing-TIN/POESSA-ID warnings; employee
TIN + pension ID fields; 21 Odoo tests), Epic B statutory reports
(l10n_et_reports: monthly VAT declaration + WHT summary, live from posted moves,
GL tie-out with visible MISMATCH warnings, PDF + CSV, MISSING-TIN markers;
18 Odoo tests; verify layouts vs current MoR forms before filing), and Epic C
onboarding + demo tenant (sapian_core wizard: profile/TIN/fiscal year/ETB/logo/
primary color/module picks, unattended fresh-DB proof; sapian_demo_trader:
"Selam General Trading PLC" provisioned via the wizard with a golden-tested
July-2026 month exercising every compliance path; 14 Odoo tests), and pharma
vertical session 1 (vertical_pharma: is_pharma batch discipline w/ mandatory
expiry + FEFO, expiry escalation states + one-digest-per-company cron,
expired-delivery block/warn policy, GS1 DataMatrix capture in
reference/pharma_calc.py, import dossiers IMP/..., branded batch recall report
with customer phone/city, EFDA export stub pending specs; 13 Odoo tests + 12
fast goldens; sapian_demo_pharma: "Tena Pharma Import PLC" pitch tenant with
730-day shelf lives, three-stage batches, pre-fired digest and the B-123
recall golden incl. precision-by-exclusion; 7 Odoo tests; both installed on
scratch_final).

BUILD PHASE COMPLETE except client-pitch work — next: sales (demo the trader
and pharma tenants, proposal from the DAT template in docs/plan-2026/01).
Pharma session 2 (medicine-request portal, delivery runs, partner directory,
SMS, EFDA live API) and everything in the DEFERRED list stay unbuilt until a
client signs.

REVISED ORDER (July 2026, token-conscious — supersedes the epic ordering in
docs/10-claude-code-roadmap.md and 01_CLAUDE_CODE_BUILD_SPEC §8 for now; those
remain the task-level detail):
- Epic A — Payroll workflow completion (l10n_et_payroll): payslip batch run,
  payroll journal posting (salary expense, PAYE/pension payables), bank salary
  transfer export, branded payslip PDF (EN), PAYE monthly declaration + pension
  remittance reports. Overtime = manual payslip input line in v1 (no attendance
  engine). Skip: severance calculator, Amharic payslip, Telebirr payout.
- Epic B — Statutory reports slice (l10n_et_reports): monthly VAT declaration
  export + WHT summary (certificate exists from Epic 3). Skip: EC-period columns,
  IFRS statement engine (use Odoo/OCA reports).
- Epic C — Thin onboarding + demo tenant: minimal company-profile wizard (TIN,
  fiscal year, ETB, module picks from sapian_core catalog), light branding only
  (logo + primary color), one demo tenant (stock, sale, purchase, account, hr +
  our modules) with realistic Ethiopian demo data.
- DEFERRED until a client signs (do NOT start even though specs exist):
  verticals other than pharma session 1 (built Jul 2026 as the DAT pitch),
  pharma session 2, payments/SMS, e-invoice, Ethiopian calendar, full
  theme/debrand, BI.
Goal: a sellable standalone Payroll+HR product and a sellable Essential/Business
ERP for a generic trader, with minimal token spend.

## Planning refresh (July 2026): docs/plan-2026/
docs/plan-2026/ is the v2 master-planning package (researched Jul 2026). Where it and the
older docs disagree, plan-2026 wins on: strategy/pricing/packaging (03), market facts and
CURRENT TAX RULES (02, 07 — e.g. WHT is now 3% with 20k/10k thresholds, TOT abolished,
VAT threshold 2M), customization/white-label spec (06), delivery methodology (09), and
high-level epic ordering (10). The older 01_CLAUDE_CODE_BUILD_SPEC remains the detailed
task-level spec; map its tasks into plan-2026 epics as you go. PAYE bands and pension
rates in the built payroll engine already match Proc 1395/2025 — no rework needed there.
plan-2026/CLAUDE.md is a reference copy; THIS file is authoritative.

## Accountant-verified tax facts (Jul 2026 review — seeded as config; supersede older figures)
- Cash cap: ETB 50,000 per party — single transaction OR same-day aggregate, whichever
  hits first (Art. 81, Proc 1395/2025; cross-verified vs KPMG's proclamation copy).
  The 30,000 figure in older docs is superseded.
- Allowances: transport exempt up to LOWER of 2,200/month or 25% of basic (excess
  taxable, engine-computed); hardship exempt; medical actual-cost exempt; housing and
  position TAXABLE. Per-diem = evidence-based input line, no monthly formula.
- Pension (Proc 1268/2022): mandatory for Ethiopian nationals; foreign nationals of
  Ethiopian origin voluntary (opt-in flag on employee); other foreigners excluded.
- WHT defaults CONFIRMED: either TIN or licence missing → 30% punitive; thresholds gate
  all WHT including punitive. Authority may aggregate deliberately split invoices.
- VAT: excess input VAT carries forward by default (refunds = exporter/investor
  processes). Reg 570/2025: real-time EFD + QR invoices for VAT-registered traders
  (simplified invoice ≤ 10,000) — fiscal-device integration is high priority for retail.
- Filing: Category A via etax.mor.gov.et, others via regional bureaus; pension via
  POESSA declaration + bank slip within 30 days. MoR beneficiary accounts (future
  payment-instruction printout): pension 1000140034057, VAT/profit tax 1000140046047.
