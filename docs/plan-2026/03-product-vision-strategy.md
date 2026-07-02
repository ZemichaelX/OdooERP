# 03 — Product Vision & Strategy

## 1. What we are building

**SapianERP** (working name — white-labelable per client): a productized ERP for Ethiopian companies, built on **Odoo Community 19 + OCA**, with a proprietary Ethiopian localization layer and a per-client customization system. Sold as fixed-price packages with recurring hosting + support.

**Positioning statement:** "The only ERP built for how Ethiopian companies actually operate — Ethiopian taxes, payroll, calendar, Amharic, Telebirr — delivered in weeks, branded as yours."

**Not** bespoke consulting. Every client deployment is the same product + configuration + (rarely) thin custom modules. The product improves with every client; delivery cost falls with every client.

## 2. Why we win (differentiation, from research §02-A)

1. **Complete Ethiopian localization** — no competitor ships a full PAYE 1395/2025 engine, 15% VAT + 3% WHT automation, 7/11 pension, QR/e-invoice readiness, Ethiopian calendar reporting, and Amharic UX as a maintained product. This is the moat; keep it proprietary (don't publish the fiscal modules to OCA).
2. **Vertical templates** — pharma/medical distribution first (DAT blueprint: batch/expiry, EFDA GS1 traceability, import records). Then import/trading, retail/distribution, services/NGO, light manufacturing.
3. **Speed + fixed price** — QuickStart packages going live in 2–6 weeks vs incumbents' open-ended engagements; published transparent pricing (incumbents are opaque — being the one with a public rate card wins trust).
4. **Demo-led selling** — permanent per-vertical demo tenants with realistic Ethiopian sample data (ETB, Amharic names, local products); prospect gets a login before the first meeting.
5. **AI-assisted delivery cost structure** — Claude Code builds/maintains modules at a fraction of incumbent engineering cost; we underprice while keeping margin.
6. **Delivery discipline as a feature** — signed scope, paid data-cleanup workstream, per-phase UAT sign-offs, super-user training program, SLA-backed support (all promises from the DAT proposal, now standardized).

## 3. Target segments (Ethiopia)

| Segment | Size sweet spot | Pain led with | Package |
|---|---|---|---|
| Pharma/medical importers & distributors | 20–300 staff | Batch/expiry, EFDA compliance, multi-warehouse | Vertical: Pharma |
| Import/export & trading PLCs | 10–200 | Landed cost, inventory, LC/import docs, WHT | Vertical: Trading |
| Retail & distribution (FMCG) | 10–500 | POS + fiscal receipts, stock, Telebirr | Vertical: Retail |
| Manufacturing (light) | 20–300 | BOM/MRP, costing | Vertical: Manufacturing |
| Services/NGO/professional | 5–200 | Projects, timesheets, HR/payroll, donor reporting | Vertical: Services |
| Any company needing payroll only | any | PAYE/pension compliance | Entry product: Payroll+HR standalone |

**Beachhead:** pharma distribution (blueprint + urgency proven by DAT). **Entry wedge:** the standalone Ethiopian Payroll+HR package — low price, universal need, monthly-recurring, upsells to full ERP.

## 4. Business model

**Revenue streams:**
1. **Implementation fees** (one-off, fixed per package/module — see §6).
2. **Hosting** (monthly, 70–85% margin): we run a multi-tenant fleet (one DB per client) on Hetzner/DigitalOcean/local provider; retail at 4,000–15,000 ETB/mo by tier. "You manage, they own" option for enterprises (their cloud account, our management fee).
3. **Support/AMC retainer** (monthly, SLA-tiered): from the DAT model's 20k ETB/mo baseline; includes patches, monitoring, helpdesk, minor enhancements.
4. **Per-module subscription** for premium modules (payroll engine, e-invoice connector, EFDA connector) — protects the moat and creates recurring revenue even on one-off implementations.
5. Training packages, data-migration fees, custom integrations (fixed quotes).

**Cost structure advantages:** AI-assisted development; reusable vertical templates; multi-tenant ops tooling (bulk updates, central monitoring); Community edition = zero license cost.

**Odoo Enterprise question:** default to Community+OCA (margin, no forex license friction). If a client demands Enterprise features, resell Enterprise (partner commission ~20%) on top of the same localization layer — the localization works on both.

## 5. Packaging (three sizes × vertical flavors)

| Package | Modules | Target | Indicative price* |
|---|---|---|---|
| **Essential** | Inventory, Sales, Invoicing, Contacts, basic reports | Small trader, 5–20 users | 250k–450k ETB impl + 4–6k/mo |
| **Business** | Essential + CRM, Procurement, Accounting (ET taxes), HR+Payroll, Website | The DAT-class client, 20–100 users | 900k–1.8M ETB impl + 8–12k/mo |
| **Enterprise** | Business + vertical pack (e.g., Pharma: EFDA, fleet/delivery), portal, integrations (Telebirr/SMS/bank), BI dashboards, multi-branch | 100+ users, regulated | 1.8M–3.5M ETB impl + 15k+/mo |

*Anchored on DAT pricing (2.2M ETB for 6 modules in 2025) adjusted for productized delivery. Publish the rate card. 30% down payment, milestone-based remainder (proven terms from the proposal).

**Standalone wedge product:** "Ethiopian Payroll & HR" — 150k–300k ETB impl + monthly per-employee or flat fee.

## 6. Sales motion

1. **Inbound:** website with published pricing, vertical landing pages, live demo request; content on 1395/2025 payroll changes, VAT/WHT automation (compliance content is high-intent SEO in this market).
2. **Demo-led:** one-click branded demo tenant per vertical; prospect explores before/after first meeting.
3. **Proposal generator:** standardized proposal template (derived from the DAT document — it's good) auto-filled from a package/module picker; quote in 24h.
4. **Land-and-expand:** start with the urgent module (usually Inventory or Payroll), expand per the DAT phased model.
5. **References:** publish case studies per vertical; retention operations (QBRs) to keep referenceable clients.

## 7. KPIs / targets (first 18 months)

- 1 flagship pharma client live (DAT or equivalent) → case study.
- 6–10 paying clients across 2 verticals; ≥80% retention.
- ≥40% of revenue recurring (hosting + AMC + module subscriptions) by month 18.
- Median implementation time ≤ 6 weeks for Business package.
- Demo-to-proposal ≤ 48h; proposal-to-signature ≥ 30% close rate.

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Tax rules change again (they just did in 2025) | Rates/brackets are **config data, never code** (effective-dated tables); one maintainer updates all tenants |
| Odoo major version upgrades break custom modules | Minimal custom code; OCA-aligned patterns; OpenUpgrade path budgeted yearly; stable field names/external IDs |
| Client demands runaway customization | Decision ladder (standardize→configure→extend→customize) enforced contractually; change orders |
| Payment/forex friction for cloud hosting | Local hosting option; client-owned cloud accounts; ETB-billed hosting through us |
| Power/connectivity issues at client sites | Offline-tolerant POS choices, low-bandwidth UX testing, SMS-based alerts as fallback |
| Key-person dependency (you) | Everything in this docs package + CLAUDE.md = institutional memory; per-client config documented automatically |
| Competitors copy the localization | Ship fast, keep fiscal modules proprietary + subscription-licensed, build brand as "the compliance-safe choice" |
