# 10 — Claude Code Build Roadmap

How to actually build this with Claude Code: epics, order, and definition of done. Repo layout is in 04 §3. Rules live in `CLAUDE.md` (copy to repo root).

> **Head start:** epics 0–2 were substantially built in your earlier chat ("ERP implementation master plan"): Docker/Postgres/nginx skeleton, `provision_client.sh`, `backup.sh`, `sapian_core` (module catalog + branding hooks), and `l10n_et_payroll` with a pure-Python calculator and 22/22 passing tests. Reuse that `sapianerp/` folder if you still have it; otherwise these epics rebuild it.

## Working method (every epic)

1. Start the session: "Read CLAUDE.md and docs/10-claude-code-roadmap.md; we're doing Epic N. Spec: docs/<file> §<n>."
2. Claude Code writes the reference calculator/tests first (where applicable), then the Odoo module, then integration tests.
3. Definition of done (all epics): tests pass; XML/manifest/CSV access rules validate; no core/OCA files modified; demo data included; docs/CHANGELOG updated; runs in the local Docker stack.
4. End the session with a verification pass (`pytest`, module install/uninstall on a scratch DB, screenshot of key screens if UI).

## Epic 0 — Foundation (week 1)
Docker Compose (Odoo 19 + Postgres 16 + nginx), hardened `odoo.conf`, `.env` secrets, `provision_client.sh`, `backup.sh`/`restore.sh`, CI (ruff + pylint-odoo + XML validation + pytest), pre-commit hooks.
**Done when:** fresh clone → running Odoo with one command; CI green.

## Epic 1 — `sapian_core` + client manifest (weeks 1–2)
`sapian.module.catalog` model (sellable modules, tiers, prices, dependencies, install hooks); client manifest loader (YAML → config); company Ethiopian fields (TIN, licence, Amharic name).
**Done when:** provisioning script + manifest installs a chosen module set unattended.

## Epic 2 — `l10n_et_payroll` (weeks 2–3) ✅ mostly built
Reference calculator (PAYE 1395/2025 bands, pension 7/11, overtime classes, severance) + effective-dated rate models + payslip compute + payroll register + bank export + journal posting.
**Done when:** golden-number tests pass (10,000 basic → 1,650 PAYE / 700 pension / 7,650 net); a full payroll run posts correct journal entries on a demo company.

## Epic 3 — `l10n_et_base` accounting (weeks 3–5)
ET chart of accounts template, 15% VAT tax codes + fiscal positions, 3% WHT automation (thresholds 20k/10k, punitive 30% for no-TIN partners), cash-cap warning (30k), multi-currency + NBE rates.
**Done when:** demo flow — vendor bill 50k ETB goods → auto 3% WHT line, correct postings; sale invoice → 15% VAT; trial balance clean.

## Epic 4 — `sapian_theme` + `sapian_onboarding` (weeks 5–6)
Debranding, logo/colors/fonts (SCSS variable pipeline), login page, branded report layouts (letterhead w/ TIN + VAT reg), email templates, terminology overrides; onboarding wizard (company info → brand → module picks → roles).
**Done when:** two demo tenants provisioned from different manifests look like two different products.

## Epic 5 — `l10n_et_calendar` + `l10n_et_reports` (weeks 6–8)
EC↔GC conversion (validated against Andegna vectors incl. Pagume/leap), EC display + fiscal-year option, ET holidays; VAT declaration, WHT summary/certificates, PAYE + pension remittance reports, IFRS-for-SMEs statements.
**Done when:** conversion test suite passes; each statutory report matches a hand-prepared fixture.

## Epic 6 — HR policy pack (week 8)
Leave types/accrual per 1156/2019, probation, overtime feeding payroll, severance calculator, departure→user-deactivation flag.
**Done when:** leave accrual and each overtime class produce correct payslip lines in tests.

## Epic 7 — `vertical_pharma` (weeks 9–11) — the DAT blueprint
FEFO + mandatory lots + configurable expiry alerts (default 3mo, email/SMS digest), import shipment dossier (docs, batch linkage), recall report, GS1 DataMatrix parsing, EFDA export stub (API when specs confirmed), medicine-request portal form → CRM/quotation, partner directory website block, delivery run management.
**Done when:** demo: receive batch → alert at horizon → sell FEFO → recall report finds every recipient of a batch; portal request becomes a draft quotation.

## Epic 8 — `sapian_payments` + `sapian_sms` (weeks 11–12)
Chapa first (best docs: hosted checkout + webhook), then Telebirr H5, M-PESA STK; SMS abstraction (Amharic UCS-2 safe) with order-status/expiry/payslip notices.
**Done when:** sandbox payment completes → invoice auto-reconciled; webhook signature verified; SMS sent on demo events.

## Epic 9 — Demo fleet + proposal generator (weeks 12–13)
Pharma + trading demo tenants with realistic Ethiopian sample data (Amharic names, ETB, local products), nightly reset; proposal generator (module picker → DAT-style proposal docx/pdf with pricing from catalog).
**Done when:** a prospect-ready demo link + a client-ready proposal are producible in under an hour.

## Epic 10 — Ops & fleet tooling (weeks 13–14)
Monitoring (Uptime Kuma + alerts), `upgrade_tenant.sh`, restore-drill runbook, auditlog defaults, security checklist automation (08), status page.
**Done when:** monthly patch + restore drill executed end-to-end on the demo fleet.

## Later epics (post-first-client)
`vertical_trading` (landed cost, LC files) · `vertical_retail` (POS + fiscal/QR) · `l10n_et_einvoice` ITAS transport (when MoR publishes) · biometric attendance sync · BI cockpit · eCommerce · Amharic translation completion · OpenUpgrade 19→20 rehearsal.

## Suggested first-90-days sequence

Weeks 1–3: Epics 0–2 (or port the existing starter repo) → **you can already sell standalone Payroll+HR**.
Weeks 3–6: Epics 3–4 → sellable Essential package, white-labeled.
Weeks 6–8: Epics 5–6 → compliance reports complete; Business package ready.
Weeks 9–13: Epics 7–9 → pharma vertical + demo + proposal machine; go get the flagship client.
Week 14: Epic 10 → operate like a product company.
