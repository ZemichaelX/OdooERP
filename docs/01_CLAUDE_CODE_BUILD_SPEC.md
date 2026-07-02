# 01 — Claude Code Build Spec: SapianERP

**Version:** 1.0 · **Date:** July 2026
**Purpose:** A repo-ready brief so Claude Code can build the Ethiopian ERP product safely, consistently, and phase by phase. Hand the `CLAUDE.md` section to the repo; work the ticket backlog in order.

---

## 1. How to use this document

1. Create the repo, drop in the **`CLAUDE.md`** from §4 (copy verbatim into the repo root).
2. Stand up the environment from §5 (Docker + Odoo 19 + Postgres).
3. Work the **ticket backlog** in §8 top to bottom. Each ticket is scoped so Claude Code can complete it in one focused session with tests.
4. Enforce the **coding standards** (§6) and **Definition of Done** (§7) on every ticket.

> **Golden rule for Claude Code:** never modify Odoo core. All product logic lives in custom addon modules under `addons/`. Extend via inheritance, not edits.

---

## 2. What we're building (one paragraph for the agent)

A productized, configurable ERP for Ethiopian companies, built as a set of custom **Odoo 19 Community** addon modules on top of the stock Odoo apps. Two module families: `l10n_et_*` (reusable Ethiopian localization — tax, payroll, calendar, Amharic, compliance) and `sapian_*` (product features — onboarding wizard, branded theme, dashboards, integrations). Each client runs an isolated Dockerized instance now, with a path to multi-tenant SaaS later. Everything version-controlled, tested, and documented.

---

## 3. Tech stack (authoritative)

| Layer | Choice | Notes |
|-------|--------|-------|
| ERP framework | **Odoo 19 Community** | Pin the exact minor version per client. Never edit core. |
| Language | **Python 3.12+** | Odoo server & module logic. |
| Frontend | **OWL** (Odoo Web Library), JS (ES6+), XML QWeb, SCSS/Bootstrap | Odoo's native stack. Custom React/Vue only for a bespoke external portal if a client needs it. |
| Database | **PostgreSQL 16+** | Odoo's required DB. One DB per client (Phase A). |
| Packaging | **Docker + docker-compose** | Reproducible per-client stacks. |
| Proxy/TLS | **Nginx + Let's Encrypt** | HTTPS everywhere. |
| VCS/CI | **Git** + GitHub/GitLab Actions | Lint + tests on every push. |
| Testing | Odoo test framework (`TransactionCase`, tagged tests) + `pytest` for pure-Python helpers | |
| Lint/format | `ruff` + `black` (Python), `pylint-odoo`, `prettier` (JS/XML where practical) | |
| Docs | Markdown in-repo + per-module `README.md` + admin manual generator | |

---

## 4. `CLAUDE.md` (copy this into the repo root)

```markdown
# CLAUDE.md — SapianERP

## What this project is
A configurable ERP product for Ethiopian companies, built as custom Odoo 19 Community
addon modules. Two module families:
- `l10n_et_*` : reusable Ethiopian localization (tax, payroll, calendar, Amharic, compliance)
- `sapian_*`  : product features (onboarding, theme, dashboards, integrations)

Each client runs an isolated Dockerized Odoo instance. Design every module to also work
in a future multi-tenant SaaS (no hard-coded company assumptions; respect `company_id`).

## Absolute rules
1. NEVER modify Odoo core or files under the odoo/ submodule or the base image.
   Extend via Python inheritance (`_inherit`) and XML view inheritance only.
2. All product code lives in `addons/`. One responsibility per module.
3. Every model field, method, and view change ships with a test and a docstring.
4. Respect multi-company: filter by `company_id`; never leak data across companies.
5. Tax rates, PAYE bands, pension %, and thresholds are CONFIGURATION DATA in
   dedicated data files / config models — never hard-coded in business logic.
   They change by government proclamation and must be editable without code changes.
6. Money is computed with Odoo's `float_round`/currency utilities — never naive floats.
7. Secrets (SMTP, Telebirr keys, DB creds) come from environment variables, never committed.
8. All user-facing strings use Odoo translation (`_()`), so Amharic can be added.
9. Follow least privilege: define security groups + record rules for every new model.
10. Do not add a Python dependency without noting it in the module manifest and requirements.

## Repo layout
- `addons/`          custom modules (l10n_et_*, sapian_*)
- `docker/`          Dockerfile, docker-compose, entrypoint
- `config/`          odoo.conf templates (no secrets)
- `scripts/`         provisioning, backup, data-migration helpers
- `data-templates/`  spreadsheet import templates for client onboarding
- `docs/`            architecture, module docs, admin manual sources
- `tests/`           cross-module integration tests

## How to run locally
`docker compose up` then open http://localhost:8069.
Odoo modules install/update with `-u module_name -d dbname` via the odoo-bin entrypoint.

## Definition of Done (every task)
- Code + tests pass (`docker compose run --rm odoo odoo -i <module> --test-enable --stop-after-init`)
- Lint clean (ruff, black, pylint-odoo)
- Security groups/record rules defined for new models
- Strings translatable; Amharic .po updated if the module is user-facing
- Module README updated (purpose, models, config, dependencies)
- No changes to Odoo core

## When unsure
Prefer configuration over code. Prefer extending an existing Odoo app over building a new one.
Ask for the client's requirement rather than assuming an Ethiopian default that varies.
```

---

## 5. Environment setup

**`docker/docker-compose.yml` (shape, not final):**
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: [ "pgdata:/var/lib/postgresql/data" ]
  odoo:
    build: ./docker
    depends_on: [ db ]
    ports: [ "8069:8069" ]
    volumes:
      - ../addons:/mnt/extra-addons
      - ../config/odoo.conf:/etc/odoo/odoo.conf
      - odoo-data:/var/lib/odoo
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=${DB_PASSWORD}
volumes: { pgdata: {}, odoo-data: {} }
```

**`config/odoo.conf` essentials:** `addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons`; set `admin_passwd` from env; `list_db = False` in production; `proxy_mode = True` behind Nginx; `workers` sized to the server.

**First-run commands:**
- Install a module: `docker compose run --rm odoo odoo -d client_db -i sapian_core --stop-after-init`
- Run a module's tests: `... -u sapian_core --test-enable --stop-after-init`

---

## 6. Coding standards

- **Module structure (standard Odoo):** `__manifest__.py`, `models/`, `views/`, `security/ir.model.access.csv` + record rules, `data/`, `wizard/`, `report/`, `static/`, `i18n/`, `tests/`, `README.md`.
- **Naming:** modules `sapian_x` / `l10n_et_x`; models `sapian.x.y`; fields `snake_case`; XML ids `module.descriptive_id`.
- **Inheritance:** extend with `_inherit`; extend views with `xpath`. Never overwrite core views wholesale.
- **Config data pattern:** rate tables (VAT, PAYE, pension) live in `data/*.xml` records of dedicated config models with `effective_from`/`effective_to` dates, so historical payrolls stay correct and future rates can be added without code.
- **Money & dates:** currency rounding via Odoo utilities; store dates in UTC; present in the client's timezone; Ethiopian-calendar display is a formatting layer, not storage.
- **Security:** every model gets `ir.model.access.csv` entries and, where multi-company/portal-exposed, `ir.rule` record rules keyed on `company_id` / user. Portal-exposed data must be explicitly whitelisted.
- **Translations:** wrap user-facing strings in `_()`; maintain `i18n/am.po` for Amharic.
- **Performance:** avoid N+1 ORM calls in loops; use `read_group`, `search_read`, and batching; add DB indexes on heavy-filter fields.
- **No secrets in code**; use env vars + `ir.config_parameter` for non-secret settings.

---

## 7. Definition of Done (gate for every ticket)

A ticket is done only when: tests written and passing; lint clean; security rules present for any new model; user-facing strings translatable (Amharic updated for user-facing modules); module README updated; no Odoo-core edits; and — where relevant — a line item added to the client onboarding questionnaire/admin manual.

---

## 8. Ticket backlog (build order)

Tickets are grouped by the product roadmap stages from doc 00 §7. Each is written so Claude Code can execute it. `[C]` = mostly configuration/scaffolding, `[D]` = custom development.

### Stage S0 — Foundation
- **S0-1 [C]** Initialize repo with the layout in §4; add `CLAUDE.md`, `.gitignore`, `.editorconfig`, license.
- **S0-2 [C]** Add `docker/` (Dockerfile from `odoo:19`), `docker-compose.yml`, `config/odoo.conf` template. Verify Odoo boots at :8069.
- **S0-3 [C]** Add CI (lint: ruff/black/pylint-odoo; run module tests). Fail the build on lint/test errors.
- **S0-4 [D]** Create empty `sapian_core` module (manifest, security stub, README, empty test) that installs cleanly. This becomes the product's base dependency.
- **S0-5 [C]** Write `scripts/provision_client.sh` skeleton (create DB, install base module set, set admin password from env).

### Stage S1 — Core & localization
- **S1-1 [D]** `sapian_core`: **Company setup model & onboarding wizard** — captures company profile, fiscal year, base currency (ETB), language (en/am), and which modules to enable. Enabling a module installs/activates it.
- **S1-2 [D]** `sapian_core`: **Module catalog & feature toggles** — a settings screen listing available modules with on/off + per-module config, backed by `ir.config_parameter` / a config model.
- **S1-3 [D]** `sapian_theme`: branded theme (colors, logo slots, login page) + role-based **home dashboard** placeholder.
- **S1-4 [D]** `l10n_et_accounting`: **Ethiopian chart of accounts** template + fiscal positions; installable on `account`.
- **S1-5 [D]** `l10n_et_accounting`: **VAT (15%) + withholding tax** as configurable tax records with `effective_from` dates; ensure invoices apply correct VAT automatically.
- **S1-6 [D]** `l10n_et_accounting`: **VAT declaration** and **withholding** report templates (QWeb + exportable).
- **S1-7 [D]** `l10n_et_payroll`: **PAYE 2026 bands** as a versioned rate table (config model with brackets + effective dates); payroll rule computes PAYE from the active table. Seed: tax-free ≤ ETB 2,000, up to 35% above ETB 14,000.
- **S1-8 [D]** `l10n_et_payroll`: **Pension** rule — 7% employee / 11% employer, max insurable ETB 15,000, citizen flag on employee.
- **S1-9 [D]** `l10n_et_localization`: Ethiopian **calendar display** helper + Ethiopian **fiscal year** default + base **Amharic `am.po`** for core strings.
- **S1-10 [C]** Integration test: create a company via the wizard, run a sample payslip, assert PAYE + pension + net pay are correct against hand-computed values.

### Stage S2 — Inventory + Sales/CRM
- **S2-1 [D]** `sapian_inventory`: extend `stock` — **shelf/bin location** config helper + multi-warehouse onboarding defaults.
- **S2-2 [D]** `sapian_inventory`: **batch/lot & expiry** enforcement + **expiry alert** (configurable lead time, default 3 months) via scheduled action + activity/notification.
- **S2-3 [D]** `sapian_inventory`: **import-record log** model linking each received batch to shipment/supplier/clearance-doc metadata for traceability.
- **S2-4 [D]** `sapian_inventory`: **internal transfer approval** flow (optional, per-config) with audit trail.
- **S2-5 [D]** `sapian_sales`: extend `sale`/`crm` — **customer profile** fields (credit limit, contract terms) + credit-limit check on order confirm.
- **S2-6 [D]** `sapian_sales`: **Ethiopian invoice layout** (VAT breakdown, TIN, bilingual labels) QWeb report.
- **S2-7 [C]** Configure CRM pipeline stages (Inquiry→Proposal→Negotiation→Won/Lost) as installable data.
- **S2-8 [D]** Sales dashboard: by product line / region / rep, MoM & YoY.
- **S2-9** Integration test: quotation → order (reserves stock) → delivery → auto-invoice, with correct VAT and inventory decrement.

### Stage S3 — Procurement + Finance dashboards
- **S3-1 [C]** `sapian_purchase`: reordering **min/max rules** pack + PR→RFQ→PO flow defaults.
- **S3-2 [D]** `sapian_purchase`: **vendor scorecard** (on-time %, quality issues) on the vendor record.
- **S3-3 [D]** RFQ multi-supplier **price/lead-time comparison** helper view.
- **S3-4** Integration test: low stock triggers PR → RFQ → PO → receipt updates PO + inventory.
- **S3-5 [D]** Finance dashboards: **P&L, Balance Sheet**, filterable by branch/department; product profitability; revenue-vs-expense charts.
- **S3-6 [C]** `l10n_et_accounting`: **bank statement import + reconciliation** config and a sample import template.

### Stage S4 — HR/Payroll polish + Website/Portal
- **S4-1 [D]** `sapian_hr`: employee record extensions (org chart, document attachments, citizen/pension flags).
- **S4-2 [C]** Leave & attendance: leave workflow + balances; attendance via kiosk/portal; optional biometric import adapter interface.
- **S4-3 [D]** Payroll run: one-click **payslip batch**, payroll register, **bank/Telebirr salary export** file.
- **S4-4 [C]** Appraisals: KPI/goal templates + review workflow.
- **S4-5 [D]** `sapian_website`: branded public site theme + **request/inquiry form** feeding Sales/CRM.
- **S4-6 [D]** `sapian_portal`: customer/partner self-service (order status, documents) + **partner directory** listing.
- **S4-7** Test: payroll run posts salary-expense **accounting entries**; HR termination revokes system access.

### Stage S5 — Integrations
- **S5-1 [D]** `sapian_telebirr`: payment adapter (collect + reconcile), keys from env, sandbox + live modes, behind a clean interface.
- **S5-2 [D]** `sapian_sms`: SMS gateway / Ethio Telecom adapter for order/delivery notifications.
- **S5-3 [D]** `l10n_et_einvoice`: structured-invoice export + adapter interface for the Ministry of Revenue e-invoicing mandate (stub the transport until API confirmed per client).
- **S5-4 [C]** Email/SMTP config templates + notification templates.

### Stage S6 — Hardening & SaaS prep
- **S6-1 [D]** Ship standard **security-group templates** + **record rules** per module; enforce **2FA** for admin/remote.
- **S6-2 [C]** `scripts/backup.sh` (daily DB + filestore dump, off-site copy) + documented **restore** procedure; test a restore.
- **S6-3 [C]** Nginx + Let's Encrypt template; server-hardening checklist (firewall, fail2ban); production `odoo.conf` (list_db off, proxy_mode on).
- **S6-4 [D]** Monitoring/alerting hooks (uptime, error rate, disk).
- **S6-5 [D]** **Tenant provisioning** script hardening + audit of `company_id` isolation across all custom models (multi-tenant groundwork).
- **S6-6** Run `/security-review` on the full addon set; resolve findings before any go-live.

---

## 9. Per-client delivery checklist (operational, reuse every sale)

1. `provision_client.sh <client>` → fresh Dockerized instance + subdomain + TLS.
2. Install `sapian_core` + `l10n_et_*` + the client's chosen modules.
3. Run onboarding wizard; answer the module questionnaires (doc 02).
4. Import master data via `data-templates/` spreadsheets; validate.
5. Apply any client-specific `sapian_client_<name>` module for true customizations.
6. Configure backups, monitoring, 2FA; run `/security-review`.
7. Train, run UAT scripts, capture sign-off.
8. Go-live; start support SLA; hand over generated admin manual.

---

## 10. Testing strategy

- **Unit/functional:** Odoo `TransactionCase` per model/workflow; tag with module name.
- **Integration:** cross-module "day-in-the-life" tests (order→delivery→invoice→accounting; PR→PO→receipt; payroll→ledger) — mirrors the DAT final acceptance test.
- **Localization correctness:** golden-value tests for VAT, PAYE, pension against hand-calculated figures; re-run when rate tables change.
- **Security:** access-control tests (a warehouse user cannot read payroll; portal user sees only own records); `/security-review` before go-live.
- **Performance:** basic load test on the production instance (concurrent orders/deliveries), per the proposal.
- **CI gate:** lint + all module tests must pass before merge.
