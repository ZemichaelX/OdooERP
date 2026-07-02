# 00 — Master Plan: Ethiopian ERP Platform

**Version:** 1.0 · **Date:** July 2026 · **Owner:** Zemichael Muluken, Sapian Technologies PLC
**Derived from:** DAT International Trading PLC ERP Implementation Proposal (Aug 2025, v1.0)

---

## 1. From one client to a product

### 1.1 Where this started
The DAT proposal committed to a tailored Odoo ERP for a single pharmaceutical importer, covering **Inventory, Website/Portal, Sales & CRM, Procurement, Accounting & Finance, and HRM & Payroll**, delivered in **7 phases over 14 weeks** for **ETB 2,200,000**, hosted in the cloud, with role-based security, 2FA, daily backups, and an optional support plan at **ETB 20,000/month**. (Full extract of the proposal is in §12 of this document.)

### 1.2 Where this goes
You now want to **offer this as an ERP to many Ethiopian companies**, customizing modules to each company's preferences and business needs, and to **build it efficiently with Claude Code** so it is secure, fully working, easy to use, and well designed.

That is a shift from *"a project"* to *"a product with a delivery method."* The rest of this plan is organized around that shift:

- A **reusable core** (the same code for every client).
- A **configuration layer** (per-client toggles and settings, no code changes).
- A **customization layer** (client-specific modules when config isn't enough).
- A **delivery engine** (Claude Code + a repeatable playbook to stand up a new client fast).

### 1.3 Product name (placeholder)
Referred to throughout as **"SapianERP"** (working name). Swap for your final brand. The Ethiopian-localization module family is namespaced `l10n_et_*`; the product modules are namespaced `sapian_*`.

---

## 2. The foundation decision (your question answered)

You asked: *"What is the best option to have a standard but greater ERP and do it in a not-so-long timeline?"*

**Recommendation: build on Odoo 19 Community (open-source), extended with your own modules.** Do **not** build from scratch.

### 2.1 Why not from scratch
A from-scratch ERP means rebuilding accounting (double-entry ledgers, tax engine, bank reconciliation), inventory (lots, valuation, multi-warehouse), HR/payroll, CRM, reporting, access control, and an admin UI — each a multi-month effort on its own. Realistically 12–24 months to reach parity with what Odoo already ships, before you sell a single license. It maximizes IP ownership but fails your "not-so-long timeline" and "standard but great" constraints.

### 2.2 Why Odoo Community is the right base
- **Standard + great, immediately.** Odoo already delivers proven double-entry accounting, lot/expiry tracking, multi-warehouse inventory, CRM pipeline, purchase/RFQ flows, HR, a website builder, and role-based security — the exact modules the DAT proposal scoped.
- **Open-source, no license lock-in.** Odoo **Community** edition is free and open-source; you avoid Enterprise per-user fees, which matters for price-sensitive Ethiopian clients. (The proposal already assumed Community by default.)
- **Customizable by design.** Odoo's module architecture (Python + PostgreSQL + the OWL JS framework) lets you add fields, workflows, screens, and whole apps without forking the core. This is where Claude Code shines — generating well-structured Odoo modules.
- **Current & supported.** Odoo 19 is the current major release (Oct 2025); versions 17/18/19 are supported as of 2026. Building on 19 gives you the longest runway before a forced upgrade.
- **Talent & community.** A large global community, addons ecosystem, and documentation reduce how much you must invent.

### 2.3 What "greater" means here — the differentiators you build
Odoo out of the box is capable but generic. Your product value (the reason a client pays you, not just downloads Odoo) is the layer you add:

1. **Ethiopian localization pack (`l10n_et_*`)** — VAT 15%, PAYE 2026 tax bands, 7%/11% pension, withholding tax, Ethiopian fiscal calendar & date display, Amharic UI strings, EFDA/pharma compliance reports, e-invoicing readiness. This is your moat; most global Odoo partners don't have it polished for Ethiopia.
2. **Telebirr & local payments integration** — collect and reconcile mobile-money payments natively.
3. **A configurable module catalog** — a clean onboarding wizard so each client turns on exactly the modules they need with sensible Ethiopian defaults.
4. **Branded, simplified UX & dashboards** — a cleaner theme, role-based home dashboards, and Amharic/English toggle, so "easy to use" is real.
5. **A repeatable delivery playbook** — Dockerized deployment, seed data, and a per-client configuration questionnaire that turns a 14-week custom project into a ~2–4 week standardized onboarding for common cases.

### 2.4 The one caveat, stated honestly
Building on Odoo means you inherit Odoo's UX conventions and upgrade cycle, and your custom modules must be maintained across version upgrades. This is a far smaller cost than building from scratch, and it is managed by the coding standards and test discipline in doc 01. If a client ever needs a radically different UX for a specific customer-facing flow (e.g., a slick public ordering portal), build **that piece** as a custom frontend calling Odoo's API — a targeted hybrid, not a rewrite.

---

## 3. Product & go-to-market model

You said you'll likely reach out to companies directly or via your network. That favors a model that is easy to demo, quick to stand up, and cheap to run per client early on.

### 3.1 Chosen model: Configurable core + module catalog, deployed per-client (Docker), evolving to SaaS

**Phase A — Per-client deployments (now → first ~5–10 clients).**
Each client gets their own Dockerized Odoo instance (isolated database, own subdomain, own backups). Simple, secure isolation; easy to customize heavily for early flagship clients; low upfront platform engineering. This is how you land DAT and the next few companies fast.

**Phase B — Multi-tenant SaaS (once demand is proven).**
Consolidate onto shared infrastructure with per-tenant data isolation, a self-service signup/trial, subscription billing (incl. Telebirr), and centralized upgrades. Higher margins and scale, but only worth the platform investment once you have repeat demand. Doc 03 designs the data model and deployment so Phase A code carries into Phase B without a rewrite.

### 3.2 Why not pure SaaS from day one
Multi-tenancy, self-service onboarding, and subscription billing are real platform work that pays off only at volume. Starting per-client lets you sell and deliver immediately, learn what Ethiopian clients actually configure, and standardize before you industrialize.

### 3.3 Packaging & pricing (productized)
Repackage the DAT figures into repeatable offers. Keep implementation as a one-time fee plus a recurring support/hosting subscription — recurring revenue is what makes this a business, not a series of projects.

| Offer | What's included | Indicative price (ETB) |
|-------|-----------------|------------------------|
| **Starter** | Core + 2 modules (e.g. Inventory + Sales), standard config, 1 week onboarding, training | 250,000 – 400,000 one-time |
| **Business** | Core + 4–5 modules, Ethiopian localization, dashboards, data migration, 2–4 wk onboarding | 800,000 – 1,500,000 one-time |
| **Enterprise / Full** | All modules + custom workflows + website/portal (the DAT scope) | 2,000,000 – 3,000,000+ one-time |
| **Support & Hosting** | Managed hosting, backups, updates, SLA, minor enhancements | 20,000 – 50,000 / month |
| **Localization add-ons** | Telebirr, e-invoicing, biometric attendance, custom reports | priced per add-on |

> Pricing is indicative and inherits the DAT proposal's logic (per-module effort). Adjust per client size. Keep the **30% upfront** term from the proposal. Hosting billed at cost or bundled.

### 3.4 Ideal early customers
The DAT profile generalizes well: **importers/distributors, wholesalers, manufacturers, pharma/medical suppliers, retail chains, logistics firms** — companies with inventory + multi-department coordination + a compliance burden. These feel ERP pain most and pay for it.

---

## 4. Module portfolio (the catalog)

Each client enables a subset. Modules map to the DAT proposal but are generalized so they fit any Ethiopian company. Detailed specs are in **doc 02**.

| Module | Core purpose | Odoo base app(s) | Your custom layer |
|--------|--------------|------------------|-------------------|
| **Core / Company Setup** | Company profile, users, roles, branding, module toggles, Ethiopian defaults | `base`, `web` | `sapian_core`, onboarding wizard, theme |
| **Inventory & Warehouse** | Multi-warehouse stock, lots/expiry, transfers, valuation | `stock` | expiry alerts, import-record log, shelf/bin config |
| **Sales & CRM** | Quotation→order→invoice, customer profiles, pipeline | `sale`, `crm` | credit limits, Ethiopian invoice format |
| **Procurement** | Vendors, price lists, reordering, RFQ→PO, receipts | `purchase` | min/max rules pack, vendor scorecards |
| **Accounting & Finance** | Double-entry, journals, bank rec, tax, reports | `account` | `l10n_et_accounting`: chart of accounts, VAT/withholding, reports |
| **HR & Payroll** | Employees, attendance, leave, payroll, appraisals | `hr`, `hr_holidays`, `hr_attendance`, `hr_payroll` (community) | `l10n_et_payroll`: PAYE, pension, payslip formats |
| **Website & Portal** | Public site + customer/partner self-service | `website`, `portal` | branded theme, request/order forms |
| **Delivery & Fleet** *(optional)* | Delivery planning, route/status, vehicle records | `fleet`, `stock` | delivery-status ↔ inventory sync |
| **Manufacturing** *(optional)* | BOM, work orders (for producers) | `mrp` | — |
| **Point of Sale** *(optional)* | Retail counter sales | `point_of_sale` | Telebirr POS payment |
| **Dashboards & Reporting** | Role-based real-time dashboards | `spreadsheet_dashboard`, custom | executive dashboard pack |
| **Integrations** | Telebirr, SMS, e-invoicing, email | — | `sapian_telebirr`, `sapian_sms`, `l10n_et_einvoice` |

---

## 5. Ethiopian localization — the moat (detail)

This is the single most valuable thing you build, because it's what makes the product *Ethiopian* rather than generic Odoo. Reusable across every client.

- **Tax engine (`l10n_et_accounting`):** VAT at **15%** (standard), VAT registration awareness (mandatory at **ETB 1,000,000** annual turnover), **withholding tax** (commonly 2% on qualifying purchases), reverse-VAT handling on imported services, and pre-built **VAT declaration** and **withholding** reports. Ethiopian chart of accounts template.
- **Payroll (`l10n_et_payroll`):** **PAYE 2026 bands** (tax-free up to **ETB 2,000/month**, progressive to a **35%** top rate above **ETB 14,000/month**, 6 brackets), **pension 7% employee + 11% employer** (max insurable earning ETB 15,000/month, Ethiopian citizens), overtime and allowance rules, payslip in the local format, and bank/Telebirr salary export files. *Bands are periodically amended — see §11 governance.*
- **Calendar & locale:** Ethiopian calendar display option (13-month), Ethiopian fiscal year (Hamle–Sene), and **Amharic** translations for key UI and printed documents; English/Amharic toggle.
- **Compliance packs:** Pharma/EFDA good-distribution-practice reports (batch/expiry, movement audit trail) as an optional pack, plus generic audit-trail reporting reusable by any regulated client.
- **E-invoicing readiness (`l10n_et_einvoice`):** structured invoice data and an adapter interface, so when the Ministry of Revenue's e-invoicing mandate applies to a client you can connect quickly. *(Ethiopia is moving toward electronic invoicing; treat the exact API as a to-confirm integration per client — see §11.)*
- **Data protection:** align with Ethiopia's data-protection expectations (consent, access control, retention) — see doc 03 §Security.

---

## 6. Delivery playbook — how a new client goes live

The reusable process that turns each sale into a live system fast. Full ticketed detail in doc 01.

1. **Discovery (2–4 days).** Run the **Client Configuration Questionnaire** (one per module, in doc 02). Capture which modules, warehouses, chart of accounts, roles, and integrations they need.
2. **Provision (1 day).** Spin up a Dockerized Odoo 19 instance from the standard image; apply the `sapian_*` and `l10n_et_*` modules; create the database and subdomain.
3. **Configure (2–5 days).** Use the onboarding wizard + questionnaire answers to set company, users/roles, warehouses, taxes, payroll rules, branding. No code for standard cases.
4. **Migrate data (2–5 days).** Import master data (products, partners, employees, opening balances) via templated spreadsheets.
5. **Customize (only if needed).** Build client-specific modules for anything config can't cover, following the coding standards in doc 01.
6. **Train & UAT (2–4 days).** Train users/admins, run UAT scripts, capture sign-off (inherit the DAT phase-sign-off discipline).
7. **Go-live & support.** Cut over, enable daily backups & monitoring, hand over admin manual, start the support SLA.

**Target:** Starter clients live in ~1–2 weeks; Business in ~3–4 weeks; Full/Enterprise on the DAT-style 14-week track only when heavily customized.

---

## 7. Build roadmap (product engineering, with Claude Code)

This is the *product* roadmap (building the reusable platform), distinct from the *per-client* delivery playbook above. Phase durations assume you + Claude Code + focused effort; adjust to your capacity.

| Stage | Goal | Key outputs | Rough effort |
|-------|------|-------------|--------------|
| **S0 — Foundation** | Repo, standards, Dockerized Odoo 19, CI | `CLAUDE.md`, repo skeleton, docker-compose, base test harness | 1–2 weeks |
| **S1 — Core & localization** | `sapian_core` + `l10n_et_accounting` + `l10n_et_payroll` + theme | Onboarding wizard, tax engine, payroll, chart of accounts, Amharic base | 3–5 weeks |
| **S2 — Inventory + Sales/CRM** | The two most-demanded modules productized | expiry alerts, import log, Ethiopian invoice, credit limits | 2–3 weeks |
| **S3 — Procurement + Finance dashboards** | Close the buy-side + management reporting | reorder pack, vendor scorecards, P&L/BS dashboards | 2 weeks |
| **S4 — HR/Payroll polish + Website/Portal** | HR self-service + branded public site/portal | leave/attendance, appraisals, request forms, partner directory | 2–3 weeks |
| **S5 — Integrations** | Telebirr, SMS, e-invoicing adapter | `sapian_telebirr`, `sapian_sms`, e-invoice interface | 2–3 weeks |
| **S6 — Hardening & SaaS prep** | Security, backups, monitoring, multi-tenant groundwork | security review, backup/restore, tenant provisioning scripts | 2 weeks |

Deliver S0→S2 first, land a paying client on that, then fund the rest from revenue.

---

## 8. Technology stack (inherited + productized)

Consistent with the DAT proposal, updated to current versions.

- **ERP engine / backend:** Odoo **19** Community (Python 3.12+ framework).
- **Frontend:** Odoo web client (OWL, JS, HTML5, Bootstrap) + a custom branded theme; targeted custom frontends (React/Vue) only where a bespoke customer-facing flow demands it.
- **Database:** PostgreSQL 16+ (Odoo's required DB).
- **Runtime/packaging:** Docker + docker-compose (per-client isolation now, Kubernetes optional at SaaS scale).
- **Hosting:** Cloud, Linux — DigitalOcean or AWS (per client preference), Addis-region latency permitting; local hosting possible if a client requires data residency.
- **Reverse proxy / TLS:** Nginx + Let's Encrypt (HTTPS everywhere).
- **Integrations:** SMTP email, SMS gateway / Ethio Telecom SMS, **Telebirr** payments, e-invoicing adapter, optional biometric attendance devices, barcode scanners.
- **Tooling:** Git (GitHub/GitLab), CI (lint + tests), Claude Code as the primary build agent.

Full topology and security controls in **doc 03**.

---

## 9. Security & compliance (productized from the proposal)

Carry every control from the DAT proposal into the product baseline, applied to *every* client by default:

- **Role-based access control** (least privilege) — shipped as standard role templates per module.
- **Two-factor authentication (2FA)** — enforced for admin/remote accounts.
- **Daily automated backups** with off-site copies and tested restore; uptime & anomaly monitoring.
- **HTTPS everywhere, hardened servers** (firewall, fail2ban, no plaintext secrets).
- **Audit trails** on stock, purchase, sales, and financial records.
- **Pharma/regulatory packs** (batch/expiry, EFDA-style reporting) for clients who need them.
- **Data-protection practices** aligned to Ethiopian data-protection law and GDPR-style principles (consent, access control, retention, export/delete on request).

Full control catalog, threat considerations, and the tenant-isolation model are in **doc 03 §Security**.

---

## 10. Team & roles

Inherited from the proposal, generalized for a product operation:

- **Product/Project lead & senior ERP consultant:** Zemichael Muluken — owns roadmap, client relationships, sign-offs.
- **Odoo/Python engineers (with Claude Code):** build and maintain `sapian_*` / `l10n_et_*` modules.
- **Implementation consultant:** runs discovery, configuration, migration, training per client.
- **UI/UX:** theme, dashboards, Amharic content, usability.
- **Support engineers (2, per the support plan):** SLA response, patches, minor enhancements.
- **Partner:** CodeLight Software Engineering PLC (per the proposal's partnership).

Claude Code acts as a force-multiplier across engineering: module scaffolding, tests, migrations, documentation, and reviews — governed by doc 01.

---

## 11. Governance, risks & assumptions

**Keep-current items (must re-verify periodically):**
- **Tax bands & rates** (VAT, PAYE, pension, withholding) change by proclamation. Treat `l10n_et_*` rate tables as **configuration data**, version them, and re-confirm against the **Ministry of Revenue** before every payroll/accounting go-live.
- **E-invoicing** requirements in Ethiopia are evolving; confirm the current mandate and API per client before committing a go-live date.
- **Telebirr API** terms and endpoints change; keep the integration behind an adapter.

**Risks & mitigations:**
- *Odoo version upgrades break custom modules* → strict module boundaries, automated tests, pin the Odoo version per client, plan upgrades as billable maintenance.
- *Scope creep per client* → the configuration questionnaire + change-order process (inherited from the proposal).
- *Over-customizing early flagships* → keep custom code in clearly separated modules so it never blocks the reusable core.
- *Data-migration quality* → templated importers + validation + UAT sign-off.
- *Single-person key dependency* → document everything (this package is the start); grow the support team.

**Assumptions:** Odoo 19 Community; clients accept cloud hosting (or arrange local hosting); Ethiopian clients want English/Amharic; pricing in ETB; 30% upfront term retained.

---

## 12. Appendix — full extraction of the DAT proposal (source of truth)

Everything the original proposal specified, preserved so nothing is lost in the pivot to a product.

**Header.** Project: *DAT ERP Implementation*. Client: *DAT International Trading PLC*. Prepared by: *Zemichael Muluken*, *Sapian Technologies PLC* in partnership with *CodeLight Software Engineering PLC*. Contact: 251919125193 | zemichael@sapiantech.com. Issue: Aug 2025. Version 1.0.

**Client & problem.** DAT is a leading Ethiopian pharmaceutical importer/distributor: imports medicines in bulk, warehouses them, and distributes to hospitals/pharmacies via its own truck fleet. Needs: centralized multi-warehouse stock (down to shelf level); batch & expiry tracking with alerts; delivery & fleet coordination; regulatory documentation/audit readiness; scalability for growth. Current state: manual/fragmented systems causing inconsistency and inefficiency.

**Vision & objectives.** A centralized, fully digitized ERP as the company's digital backbone. Objectives: unify medicine tracking (import→warehouse→delivery, per batch); prevent stockouts & expired products via proactive alerts and auto-reordering; streamline cross-department communication; provide real-time dashboards; automate routine tasks (HR, finance, sales, procurement).

**Scope of work.** Full Odoo deployment: business analysis, configuration & customization, data migration, training, deployment. Phased for incremental validation with per-phase UAT sign-off. In-scope: requirements gathering & process mapping; standard module config + custom features; integration setup (email, SMS, Ethio Telecom APIs); iterative testing & feedback; cloud deployment with security hardening & backups; training + user manuals; go-live support. Out-of-scope handled via change management.

**Project deliverables.** Fully functional Odoo ERP (web + optional mobile); complete data migration (opening balances, master records); user training & documentation (on-site/virtual + manuals); hosting & deployment setup (production server, DB, backups, VPN/secure access); custom dashboards & reports (inventory aging, sales performance, financial statements). All complete only after testing + formal acceptance.

**Software deliverables.** Configured Odoo modules (Inventory, Sales, CRM, Procurement, Accounting, HRM — e.g. Ethiopian chart of accounts, lot tracking); custom workflows/features (e.g. website medicine-request workflow, internal-transfer approval flow); website & customer portal (branded, medicine-request form, partner directory); user access roles & permissions (RBAC, least privilege); documentation of configuration (admin manual). Built on latest stable Odoo; extensible.

**Testing services.** Module functional testing; User Acceptance Testing (UAT) at each phase end with scripts & sign-off; performance & load testing on production; bug fixes & optimization (target zero critical bugs at launch); final end-to-end acceptance ("day-in-the-life") test before go-live. All documented; results & issue logs shared.

**Module details as scoped:**
- *Inventory (Phase 1, urgent):* stock tracking by location (shelf/bin, multi-warehouse); batch & expiry tracking with **alerts 3 months before expiry**; import records & history per shipment; internal transfers & stock moves with optional approvals and full audit trail; integration with delivery operations (allocate on prep, reduce on ship, real-time status).
- *Website & Portal (Phase 2):* public company profile (Odoo website builder, staff-editable); medicine request submission form feeding Sales/inventory; partner directory listing (suppliers/distributors with logos, regions, contacts).
- *Sales & CRM (Phase 3):* customer profiles & order history (contacts, contract terms, credit limits, full history); quotation→order→invoice workflow (one-click convert, auto-reserve inventory, auto-invoice on delivery); CRM pipeline for key deals (stages Inquiry→Proposal→Negotiation→Won/Lost, reminders, attachments); sales reporting & performance tracking (by product line/region/rep, YoY/MoM, dashboards).
- *Procurement (Phase 4):* vendor database & price lists (contacts, terms, price lists, performance metrics); automated purchase requests via min/max reordering; RFQs & PO generation (multi-supplier compare, convert to PO, expected dates); integration with inventory receipts (auto-update PO on receipt).
- *Accounting & Finance (Phase 5):* multi-journal double-entry (Ethiopian chart of accounts & tax accounts; Sales/Purchase/Bank/Cash/Payroll journals; IFRS or Ethiopian GAAP); bank reconciliation (statement import & reconcile); tax configuration & reporting (VAT, withholding, VAT declarations); profitability dashboards (P&L, Balance Sheet, by branch/department, product profitability, charts).
- *HRM & Payroll (Phase 6):* employee records & org structure (profiles, org chart, document attachments); attendance & leave (optional biometric, leave workflow, balances); automated payroll (allowances, deductions, PAYE, pension per Ethiopian law; one-click payslips; registers; bank transfer export); performance & appraisal (KPIs, reviews, self-service, 360°). All modules integrated (e.g., payroll → accounting entries; HR departure → user-access update).

**Technology stack (as proposed):** Odoo (Python) backend; HTML5/JS/Bootstrap frontend; PostgreSQL; cloud hosting on DigitalOcean or AWS (Linux); integrations for email, SMS gateway, Telecom APIs, Telebirr, barcode.

**Timeline (14 weeks, 7 phases):** Phase 1 Inventory **6 wks**; Phase 2 Website/Portal **2 wks**; Phase 3 Sales & CRM **2 wks**; Phase 4 Procurement **1 wk**; Phase 5 Accounting & Finance **1 wk**; Phase 6 HRM & Payroll **1 wk**; Phase 7 Testing & Go-Live **1 wk**. Milestones: Week 0 kickoff; Week 2 website live (internal); Week 8 core ERP in UAT; Week 14 go-live. Phases may overlap; each ends with a demo + sign-off; weekly/bi-weekly progress meetings.

**Pricing (ETB, fixed-price, excl. Odoo Enterprise license & VAT):** Inventory 200,000; Website & Portal 100,000; Sales & CRM 300,000; Procurement 300,000; Accounting & Finance 300,000; HRM & Payroll 300,000; **Total 2,200,000**. Terms: **30% upfront** on signing; remainder tied to milestones. Hosting excluded (~ETB 5,000–10,000/month, client pays provider directly). Training on-site in Addis Ababa; travel billed at actuals.

**Security & compliance (as proposed):** RBAC; 2FA (esp. admin/remote); daily automated backups off-site + uptime monitoring & alerts; pharmaceutical-regulation compliance (batch/expiry, EFDA reporting, audit trails); GDPR-inspired data-privacy practices; secure development & deployment (HTTPS, hardened server, firewall, fail2ban, no plaintext secrets).

**Optional maintenance & support:** 6- or 12-month terms; **ETB 20,000/month** (fixed first year); 2 dedicated support engineers; real-time bug fixes & Odoo patches/security updates; user assistance & minor enhancements/reports; SLA — response within **1 business day** for major issues, immediate for critical (system down), 1–2 days for minor; knowledge transfer to internal IT.

**Major Odoo features leveraged:** inventory traceability (lot/serial, expiry alerts); automated procurement rules & vendor price lists; CRM & sales pipeline; double-entry accounting + bank reconciliation; HR & payroll integration.

**Next steps (as proposed):** review & approve → finalize agreement & sign contract (+ NDA) → 30% initial payment → kickoff meeting → begin Phase 1 (Inventory, urgent).

---

## Sources (facts verified July 2026)
- Latest Odoo version / support: [ECOSIRE — Latest Odoo Version](https://ecosire.com/blog/latest-odoo-version), [Odoo 19 documentation — support](https://www.odoo.com/documentation/19.0/administration/standard_extended_support.html)
- Ethiopia VAT: [Quaderno — Ethiopia VAT Guide](https://quaderno.io/guides/ethiopia-vat-guide/), [PwC — Ethiopia Other taxes](https://taxsummaries.pwc.com/ethiopia/corporate/other-taxes)
- Ethiopia PAYE 2025/2026 changes: [PaySpace — Ethiopia income tax amendments 2025](https://www.payspace.com/blog/ethiopia-income-tax-amendments-key-payroll-changes-2025/)
- Pension & payroll: [PwC — Ethiopia Individual Other taxes](https://taxsummaries.pwc.com/ethiopia/individual/other-taxes), [Playroll — Payroll in Ethiopia](https://www.playroll.com/payroll/ethiopia)
- Telebirr integration: [zoromia — Telebirr Payment Integration 2025](https://zoromia.com/how-to-integrate-telebirr-payment-in-2025-a-simple-guide/)
