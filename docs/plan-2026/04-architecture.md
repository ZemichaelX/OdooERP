# 04 — Technical Architecture

## 1. Stack

| Layer | Choice | Rationale |
|---|---|---|
| ERP core | **Odoo 19 Community** (LTS-ish stable; plan 19 via OpenUpgrade) | Free, full OCA compatibility, proven |
| Community gap-fillers | **OCA modules** (accounting reports, partner tooling, web UX) | 1000+ maintained modules; upgrade-safe patterns |
| Proprietary layer | `sapian_*` and `l10n_et_*` addons (this product) | The moat: localization + customization system |
| Database | PostgreSQL 16 | Odoo standard |
| Frontend | Odoo web client (OWL), website builder; Bootstrap | Standard; theme layer for branding |
| Deployment | Docker Compose per node (Odoo + Postgres + nginx) | Reproducible; simple ops |
| Reverse proxy / TLS | nginx + Let's Encrypt | HTTPS everywhere |
| Hosting | Hetzner/DigitalOcean (primary), AWS or local DC when client requires; Linux | Cost + client preference |
| Monitoring | Uptime Kuma + node exporter + log alerts (start simple) | Fleet visibility |
| CI | GitHub Actions: lint (ruff, pylint-odoo), tests, XML validation | Quality gate per commit |

## 2. Tenancy model

**One Odoo database per client, shared or dedicated infrastructure by tier:**

- **Shared node (default):** one server runs several small tenants (separate DBs, separate filestores, `dbfilter` per domain). Cheapest; fine for Essential/Business tiers.
- **Dedicated node:** one server per client (Enterprise tier, regulated clients, heavy load).
- **Client-owned ("you manage, they own"):** deployment in the client's cloud account; we hold ops access. Clean exit story for big/regulated clients.

Rules:
- Never multi-company-in-one-DB for separate client companies (data isolation, backup isolation, exit portability).
- Multi-company *within* one client (branches/sister companies) uses Odoo multi-company in that client's DB.
- Each tenant: own subdomain (`client.sapianerp.com` or client's own domain), own TLS cert, own backup schedule, own SMTP identity.

## 3. Repository & module architecture

```
sapianerp/
├── CLAUDE.md                  # operating rules for Claude Code
├── docs/                      # this planning package
├── docker/                    # Dockerfile, docker-compose.yml (odoo+pg+nginx)
├── config/odoo.conf           # hardened defaults (workers, limits, list_db=False)
├── scripts/
│   ├── provision_client.sh    # one-command new-tenant setup
│   ├── backup.sh / restore.sh
│   └── upgrade_tenant.sh
├── addons/
│   ├── sapian_core/           # module catalog, client config, branding hooks
│   ├── sapian_theme/          # white-label: colors, logo, fonts, login, debrand
│   ├── sapian_onboarding/     # setup wizard: pick modules, brand, company data
│   ├── l10n_et_base/          # ET chart of accounts, VAT 15%, WHT 3%, fiscal positions
│   ├── l10n_et_payroll/       # PAYE 1395/2025 engine, pension 7/11, payslips
│   ├── l10n_et_reports/       # VAT declaration, WHT summary, pension file, ET-calendar reports
│   ├── l10n_et_calendar/      # Ethiopian (Ge'ez) calendar display & conversion
│   ├── l10n_et_einvoice/      # QR receipts now; ITAS e-invoice connector when mandated
│   ├── sapian_payments/       # Telebirr, Chapa, M-PESA, ArifPay providers
│   ├── sapian_sms/            # Ethio Telecom SMS / gateway abstraction
│   ├── vertical_pharma/       # batch/expiry alerts, EFDA GS1, import records, medicine request portal
│   ├── vertical_trading/      # landed costs, LC/import documentation
│   └── vertical_retail/       # POS + fiscal device/QR receipt flow
├── reference/                 # pure-Python calculators (tax math source of truth)
├── tests_fast/                # pytest suite for reference calculators (no Odoo needed)
└── .github/workflows/ci.yml
```

Design rules:
- **Pure-Python reference calculators** for all tax/payroll math in `reference/`, imported by Odoo models. Testable in milliseconds without an Odoo instance; the single source of truth. (Already built & tested for payroll in the earlier starter repo: 22/22 tests.)
- **Rates are data, not code:** PAYE bands, pension %, VAT/WHT rates live in effective-dated config records seeded by XML/CSV. A 2027 tax reform = a data update, not a code release; historical payslips stay correct.
- **Never modify Odoo core or OCA source.** Extend via inheritance only. Keeps upgrades sane.
- Stable external IDs and field names forever (OpenUpgrade survival).
- Every addon: `security/ir.model.access.csv`, record rules, demo data, and tests.

## 4. Environments & lifecycle

| Env | Purpose |
|---|---|
| Dev (local Docker) | Claude Code builds here; demo data loaded |
| Demo fleet | Permanent per-vertical sales demo tenants, reset nightly |
| Staging (per client during implementation) | UAT happens here; client data migrated here first |
| Production (per client) | Go-live target; backups + monitoring mandatory before cutover |

**Provisioning flow:** `provision_client.sh <name> <package> <vertical>` → creates DB, installs module set from catalog, applies branding defaults, creates admin, registers backup + monitoring. Target: new tenant in under 15 minutes.

**Upgrade policy:** pin Odoo minor version fleet-wide; monthly patch window; major version upgrade once/year via OpenUpgrade, rehearsed on staging clones of each tenant.

## 5. Performance & sizing

- Odoo workers = 2×CPU+1; proxy mode behind nginx; `limit_memory_*` set; Postgres tuned (shared_buffers 25% RAM).
- Sizing guide: ≤20 users → 2 vCPU/4GB; ≤75 users → 4 vCPU/8GB; ≤200 users → 8 vCPU/16GB + separate DB volume. Load-test each tier once with realistic transaction mix (the DAT proposal promises concurrent-order load testing — keep that as standard practice).
- Low-bandwidth reality: test key screens on 3G-class latency; prefer list views over kanban-with-images for defaults; SMS fallbacks for critical alerts.

## 6. Data migration architecture

Standardized import kit per module: CSV templates (products incl. batch/expiry, partners, opening stock by location, opening balances, employees incl. salary structure), validation scripts that report errors *before* import, and a rehearsal-then-final two-pass migration. Data cleanup is a paid client deliverable with its own sign-off (failure stat: 38% of ERP failures are migration-related).

## 7. Integration architecture

- All external integrations behind thin provider abstractions (payments, SMS, fiscal/e-invoice, EFDA) with: sandbox mode, webhook endpoint hardening (signature verification), retry queues (`ir.cron` + queued jobs), and per-tenant credentials stored encrypted.
- Priority order: SMTP email → SMS gateway → Telebirr → Chapa → bank statement import (CSV/OFX) → EFDA GS1 API (pharma) → ITAS e-invoice (when dates firm up) → biometric attendance devices (ZKTeco-class, via intermediate sync service).
