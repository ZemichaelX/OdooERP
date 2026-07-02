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
    cp .env.example .env          # set DB_PASSWORD etc.
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
Authoritative phased backlog: docs/01_CLAUDE_CODE_BUILD_SPEC.md (§8). Work it top to bottom.
Implemented so far: repo skeleton (S0), sapian_core starter (S0-4/S1-1/S1-2),
l10n_et_payroll PAYE + pension engine (S1-7/S1-8) with tests.

## Planning refresh (July 2026): docs/plan-2026/
docs/plan-2026/ is the v2 master-planning package (researched Jul 2026). Where it and the
older docs disagree, plan-2026 wins on: strategy/pricing/packaging (03), market facts and
CURRENT TAX RULES (02, 07 — e.g. WHT is now 3% with 20k/10k thresholds, TOT abolished,
ETB 30k cash cap, VAT threshold 2M), customization/white-label spec (06), delivery
methodology (09), and high-level epic ordering (10). The older 01_CLAUDE_CODE_BUILD_SPEC
remains the detailed task-level spec; map its tasks into plan-2026 epics as you go.
PAYE bands and pension rates in the built payroll engine already match Proc 1395/2025 —
no rework needed there. plan-2026/CLAUDE.md is a reference copy; THIS file is authoritative.
