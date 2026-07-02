# SapianERP — Master Planning Package

A productized, Ethiopia-localized ERP built on Odoo Community + OCA, delivered per-client with full customization (modules, branding, workflows) — developed with Claude Code.

**Origin:** DAT International Trading PLC proposal (Aug 2025, Sapian Technologies + CodeLight) — generalized into a repeatable product for Ethiopian companies.

## How to use this package with Claude Code

1. Create your build repo (e.g., `sapianerp/`) and copy this folder into it as `docs/`.
2. Copy `CLAUDE.md` from this package to the repo root — it contains the operating rules Claude Code must follow.
3. Work epic-by-epic from `10-claude-code-roadmap.md`. Each epic references the spec files below; point Claude Code at the relevant doc when starting an epic ("Build epic 2; spec is docs/07-ethiopian-localization.md §2").
4. Never let a session end without tests passing; the roadmap defines the test gates.

> Note: a starter repo was already built in your earlier chat ("ERP implementation master plan") — Docker/Postgres setup, `sapian_core` (module catalog + branding hooks), and a tested `l10n_et_payroll` engine (22/22 tests). If you still have that `sapianerp/` folder, reuse it as the starting point for epic 0–2 instead of rebuilding.

## Package contents

| File | What it is |
|---|---|
| `01-proposal-extraction.md` | Every detail extracted from the DAT proposal — the factual baseline |
| `02-market-research.md` | How ERP firms win/differentiate + Ethiopian regulatory & market facts (researched Jul 2026, with sources) |
| `03-product-vision-strategy.md` | Product definition, target segments, differentiation, business model, pricing & packaging |
| `04-architecture.md` | Technical architecture: stack, multi-tenancy, environments, upgrades, performance |
| `05-module-catalog.md` | Full module catalog: core, standard, Ethiopian, vertical packs — with tiering |
| `06-customization-white-label.md` | The customization system: branding, module toggles, naming, fonts, workflows, per-client config |
| `07-ethiopian-localization.md` | Exact tax/payroll/compliance specs (PAYE, VAT, WHT, pension, e-invoice, labor law, calendar) |
| `08-security-compliance.md` | Security architecture, hardening checklist, backup/DR, audit & privacy |
| `09-delivery-methodology.md` | The client playbook: sell → discover → implement → UAT → train → support |
| `10-claude-code-roadmap.md` | Build epics, repo structure, definition of done, Claude Code workflow |
| `CLAUDE.md` | Drop-in operating rules for the Claude Code build repo |

## The strategy in one paragraph

Sell a **branded, fixed-price, fast-deploy ERP product** (not bespoke consulting) built on Odoo 19 Community + OCA, self-hosted multi-tenant for margin, with a **deep Ethiopian localization layer nobody else has complete** (PAYE 1395/2025 engine, 15% VAT + 3% WHT automation, pension, QR/e-invoice readiness, Ethiopian calendar, Amharic, Telebirr/Chapa/M-PESA payments, EFDA traceability). Differentiate on vertical templates (pharma distribution first — you already have the DAT blueprint), demo-led selling, disciplined change management, and an AI-assisted delivery cost structure incumbents can't match. Recurring revenue from hosting + support retainers.
