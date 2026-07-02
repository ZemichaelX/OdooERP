# 03 — Architecture & Data Model: SapianERP

**Version:** 1.0 · **Date:** July 2026
**Purpose:** How the system fits together — deployment topology, tenancy, the data model (ERD), API design, integrations, and the security control set. Use for architecture reviews, engineer onboarding, and answering client security/integration questions.

---

## 1. Architecture at a glance

SapianERP is a set of custom addon modules on **Odoo 19 Community** (Python + PostgreSQL + OWL). It runs as a containerized stack behind an HTTPS reverse proxy. Today each client is an **isolated instance** (own DB, own container, own subdomain). The data model and code are written so the same modules run unchanged in a future **multi-tenant SaaS** consolidation.

```
                        ┌──────────────────────────────────────────────┐
   Internet  ──HTTPS──▶ │  Nginx (TLS, reverse proxy, rate limiting)    │
                        └───────────────┬──────────────────────────────┘
                                        │
                        ┌───────────────▼──────────────────────────────┐
                        │  Odoo 19 app container(s)                     │
                        │  ├─ Odoo core apps (stock, sale, account, hr) │
                        │  ├─ l10n_et_*  (localization)                 │
                        │  ├─ sapian_*   (product features)             │
                        │  └─ workers: web + cron + longpolling         │
                        └───────┬───────────────┬──────────────────────┘
                                │               │
                 ┌──────────────▼───┐   ┌───────▼────────────────────┐
                 │ PostgreSQL 16    │   │ Filestore (attachments)    │
                 │ (per-client DB)  │   │ (volume / object storage)  │
                 └──────────────────┘   └────────────────────────────┘
                                │
        Integrations ◀─────────┼─────────▶  Telebirr · SMS/Ethio Telecom · SMTP
                                │             e-invoicing (MoR) · biometric · barcode
                                ▼
                   Backups (daily DB + filestore → off-site) · Monitoring/alerts
```

**Layering (dependency direction, top depends on bottom):**
1. **Product modules** `sapian_*` (onboarding, theme, dashboards, integrations)
2. **Localization modules** `l10n_et_*` (tax, payroll, calendar, e-invoice)
3. **Odoo core apps** (stock, sale, crm, purchase, account, hr, website, portal)
4. **Odoo framework** (ORM, security, web, cron)
5. **PostgreSQL + filestore**

Never invert this: core never depends on your modules; localization never depends on product features.

---

## 2. Tenancy model

### 2.1 Phase A — instance-per-client (now)
- One Docker stack (Odoo + Postgres + filestore) per client, one subdomain (`client.sapianerp.com`), separate backups.
- **Isolation:** absolute (separate DB and container). Simplest, safest, easiest to customize heavily.
- **Trade-off:** more instances to operate; automate with `provision_client.sh` and a standard image.

### 2.2 Phase B — multi-tenant SaaS (later)
Two viable routes, decided when volume justifies it:
- **DB-per-tenant on shared app servers** (Odoo's native multi-DB): strong isolation, moderate density. Recommended first step — minimal code change from Phase A.
- **Shared DB, row-level isolation by `company_id`** (single Odoo DB, many companies): highest density, but every query and record rule must be company-scoped and audited. Higher risk; only if density economics demand it.

### 2.3 The rule that makes both work
Every custom model that holds client data includes `company_id` and is filtered by it via `ir.rule` record rules. No business logic assumes a single company. This is enforced from day one (doc 01, rule #4) so Phase A code carries into Phase B without a rewrite.

---

## 3. Data model (entity-relationship)

Most entities are Odoo's proven models, extended with custom fields; a few are new (prefixed `sapian.` / `l10n.et.`). The ERD below shows the core relationships that matter for this product.

```
COMPANY (res.company)
  │1
  ├───< USER (res.users) ──many2many── SECURITY GROUP (res.groups)
  ├───< WAREHOUSE (stock.warehouse) ──1─< LOCATION (stock.location, hierarchical)
  ├───< PARTNER (res.partner)  ← customers, vendors, portal users, directory
  ├───< PRODUCT (product.template/product.product)
  ├───< JOURNAL (account.journal)   [Sales, Purchase, Bank, Cash, Payroll]
  └───< EMPLOYEE (hr.employee)

PRODUCT
  │1
  ├───< LOT/BATCH (stock.lot) ── expiry_date, l10n_et_import_record_id
  └───< REORDER RULE (stock.warehouse.orderpoint)  min/max

LOT/BATCH ──1─< STOCK MOVE LINE (stock.move.line) [audit: qty, from, to, date, user]
IMPORT RECORD (sapian.import.record) ──1─< LOT/BATCH   [shipment, supplier, docs, cost]

PARTNER (customer)
  ├───< SALE ORDER (sale.order) ──1─< SALE LINE ──> PRODUCT
  │                             └──> STOCK PICKING (delivery) ──> STOCK MOVE
  ├───< INVOICE (account.move, type=out) ──1─< INVOICE LINE ──> TAX (account.tax: VAT/withholding)
  └───< CRM LEAD (crm.lead) ── stage_id (Inquiry→Proposal→Negotiation→Won/Lost)

PARTNER (vendor)
  ├───< PURCHASE ORDER (purchase.order) ──1─< PO LINE ──> PRODUCT
  │                                      └──> RECEIPT (stock.picking, in)
  ├───< VENDOR PRICELIST (product.supplierinfo)
  └───< VENDOR SCORECARD (sapian.vendor.scorecard) [on_time%, quality]

account.move (any) ──1─< JOURNAL ITEM (account.move.line) ──> ACCOUNT (account.account)
   ▲ auto-posted from: invoices, bills, stock valuation, payroll

EMPLOYEE
  ├───< CONTRACT (hr.contract) ──> SALARY STRUCTURE (hr.payroll.structure)
  ├───< ATTENDANCE (hr.attendance)
  ├───< LEAVE (hr.leave) ── leave_type, balance
  ├───< PAYSLIP (hr.payslip) ──1─< PAYSLIP LINE ──> RULE (PAYE, pension, allowance)
  └───< APPRAISAL (hr.appraisal)

CONFIG TABLES (versioned, effective-dated) — the localization moat
  l10n.et.paye.band   (bracket_from, bracket_to, rate, effective_from, effective_to)
  l10n.et.pension.cfg (employee_rate=7%, employer_rate=11%, cap=15000, effective_from)
  account.tax         (VAT 15%, withholding %, effective via fiscal position)
```

**Design notes.**
- **Rate tables are data, not code.** `l10n.et.paye.band`, `l10n.et.pension.cfg`, and tax records carry effective dates so a rate change never rewrites historical payslips/entries. This is central to staying compliant across proclamations.
- **One ledger, auto-posted.** Operational documents (invoice, bill, stock move, payslip) each generate `account.move` entries, so operational and financial data can never drift apart.
- **Traceability chain.** Import Record → Lot/Batch → Stock Move Lines → Delivery gives full import-to-customer traceability and recall support.
- **`company_id` everywhere.** On every client-data model, for tenancy.

---

## 4. API & integration design

### 4.1 External API surface
- **Odoo JSON-RPC / XML-RPC** for programmatic access (reports, external apps).
- **Odoo controllers (`http.Controller`)** for custom REST-style endpoints (portal request form, Telebirr callbacks, webhook receivers). Authenticated; rate-limited at Nginx.
- **Portal** for customer/partner self-service (scoped to own records by record rules).

### 4.2 Integration adapters (all behind clean interfaces, config-driven, keys from env)

| Integration | Direction | Pattern | Notes |
|-------------|-----------|---------|-------|
| **Telebirr** | in (collect) / out (payout) | Adapter module `sapian_telebirr`; controller endpoint for payment callbacks; sandbox + live | Reconcile payments to invoices; salary payout export. Confirm current API/terms per client. |
| **SMS / Ethio Telecom** | out | `sapian_sms` adapter; templated bilingual messages triggered by events | Order/delivery/payment notifications. |
| **Email (SMTP)** | out | Odoo native outgoing mail server | Confirmations, system notifications. |
| **E-invoicing (MoR)** | out | `l10n_et_einvoice` builds structured invoice; transport adapter stubbed until API confirmed | Enable per client when mandate applies. |
| **Biometric attendance** | in | Import adapter interface (device push or scheduled pull) | Optional HR add-on. |
| **Barcode scanner** | in | Odoo barcode app integration | Inventory operations. |

**Adapter rules:** every integration runs in **sandbox first**; failures are logged and retried with backoff; no secrets in code (env + `ir.config_parameter`); each is independently enable/disable-able per client without code changes.

---

## 5. Deployment topology & environments

**Environments:** `dev` (local Docker) → `staging` (per-client, for UAT) → `production`.

**Production stack per client:**
- Nginx (TLS via Let's Encrypt, HSTS, security headers, rate limiting) → Odoo app (multi-worker: web + longpolling + cron) → PostgreSQL 16 → filestore volume (or object storage).
- `odoo.conf` production settings: `list_db = False`, `proxy_mode = True`, `admin_passwd` from env, workers sized to CPU/RAM, `db_maxconn` tuned.
- Hosting: DigitalOcean or AWS, Linux, region chosen for Ethiopian latency; local/on-prem hosting supported where a client requires data residency.

**Provisioning:** `provision_client.sh` creates the DB, installs `sapian_core` + `l10n_et_*` + chosen modules, sets admin credentials from env, configures the subdomain and TLS. One command to a running instance.

**CI/CD:** Git → CI (lint + module tests) → build image → deploy to staging → UAT sign-off → promote to production. Odoo module upgrades run via `-u <module>` with a DB backup taken first.

---

## 6. Security controls (the full set)

Every control is a **default applied to every client**, carried from the DAT proposal and extended.

**Identity & access**
- **RBAC / least privilege:** security groups + `ir.model.access.csv` + `ir.rule` record rules on every model. Standard role templates per module (doc 02 §10).
- **2FA:** enforced for admin and remote accounts; available to all users.
- **Separation of duties:** e.g., sales reps create invoices, only finance validates; payroll visible only to HR + the employee.
- **Portal scoping:** portal users see strictly their own records via record rules.

**Data protection**
- **Encryption in transit:** HTTPS everywhere (TLS, HSTS). No plaintext credentials or secrets; secrets in env vars.
- **Encryption at rest:** disk/volume encryption on the host; DB backups encrypted.
- **Tenant isolation:** separate DB per client (Phase A); `company_id` record rules audited for Phase B.
- **Data-protection practices:** consent capture where personal data is collected; access controls; retention limits; export/delete-on-request support — aligned to Ethiopia's data-protection law and GDPR-style principles.

**Operational security**
- **Server hardening:** firewall, `fail2ban`, minimal open ports, unattended security updates, non-root containers.
- **Backups & recovery:** daily automated DB + filestore backups, off-site copies, **tested restore**; documented RPO/RTO.
- **Monitoring & alerting:** uptime, error rate, disk, and anomaly alerts; audit logging of admin actions.
- **Audit trails:** stock moves, purchases, sales, and financial entries are attributable (user + timestamp) and immutable once posted.

**Application security**
- Custom code reviewed for injection, access-control, and data-leak issues; `/security-review` run on the addon set before any go-live.
- Dependency hygiene: pinned versions; no unvetted addons; Odoo security patches applied under the support plan.

**Compliance packs**
- Pharma/EFDA: batch/expiry controls, good-distribution audit trail, recall support, regulator report generation.
- Tax compliance: VAT/withholding reporting, e-invoicing readiness.

---

## 7. Non-functional targets

| Concern | Target |
|---------|--------|
| Availability | ≥ 99.5% (single-instance), monitored; higher with HA at SaaS stage |
| Backup RPO | ≤ 24h (daily); tighter with more frequent dumps if required |
| Restore RTO | ≤ 4h from off-site backup (tested) |
| Concurrency | Load-tested for the client's peak concurrent users/transactions (per proposal) |
| Response time | Interactive screens < 2s under normal load |
| Upgradability | Custom modules pass tests on the pinned Odoo version; upgrades planned as maintenance |
| Localization accuracy | Tax/payroll golden-value tests pass; rate tables re-verified before each go-live |

---

## 8. Upgrade & maintenance model

- **Pin Odoo version per client**; schedule upgrades as billable maintenance windows.
- **Custom modules are the upgrade unit:** because core is never edited, upgrades mean re-testing `sapian_*` / `l10n_et_*` against the new Odoo version, not untangling core patches.
- **Rate-table updates** (VAT/PAYE/pension) ship as data updates with new effective dates — no version upgrade needed, no history rewritten.
- **Support SLA** (from the proposal): response within 1 business day for major issues, immediate for critical; patches and minor enhancements included.

---

## 9. Build-vs-configure summary (so effort lands in the right place)

| Area | Mostly configure (Odoo) | Custom build (your value) |
|------|-------------------------|---------------------------|
| Inventory | warehouses, lots, reorder rules | expiry alerts, import record, pharma pack |
| Sales/CRM | pipeline, quotes, invoicing | credit limits, Ethiopian invoice, dashboards |
| Procurement | vendors, RFQ, PO, receipts | reorder pack, vendor scorecards |
| Accounting | journals, bank rec | Ethiopian CoA, VAT/withholding, ET reports |
| HR/Payroll | employees, leave, attendance | PAYE/pension engine, ET payslip, exports |
| Website/Portal | site builder, portal | branded theme, request forms, directory |
| Platform | Docker, Odoo config | onboarding wizard, module catalog, provisioning, integrations |

Concentrate custom effort on the localization moat and the onboarding/provisioning engine — that's what makes it a product, not a one-off.
