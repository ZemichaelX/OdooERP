# Ethiopian ERP Platform — Master Planning Package

**Prepared for:** Zemichael Muluken (Sapian Technologies PLC)
**Origin:** Productized from the *DAT International Trading PLC — Odoo ERP Implementation Proposal* (Aug 2025, v1.0)
**Purpose:** Turn a one-client Odoo implementation into a repeatable, customizable ERP product for Ethiopian companies, built and maintained with Claude Code.
**Date:** July 2026

---

> **Planning refresh (July 2026): see [`plan-2026/`](./plan-2026/00-README.md).**
> A v2 package built from the full 27-page proposal extraction plus fresh market/regulatory research.
> Where the two disagree, **plan-2026 wins** on strategy, pricing, current tax rules (WHT 3%, TOT abolished,
> ETB 30k cash cap, VAT threshold 2M), customization spec, delivery methodology, and epic ordering.
> This original package remains the detailed task-level build spec (01, 02, 03).

## What this package is

The original proposal was a fixed-scope Odoo implementation for a single pharmaceutical importer (DAT). This package re-frames that work as a **reusable ERP product** you can configure per client and sell to many Ethiopian companies — while keeping everything that made the DAT proposal strong (phased delivery, Ethiopian tax/compliance, security, real-time dashboards).

It also converts the plan into a form **Claude Code can execute**: a repo layout, coding standards, per-module specs, an architecture with a concrete data model, and a phase-by-phase ticket backlog.

## The deliverables

| # | Document | What it answers |
|---|----------|-----------------|
| 00 | **[Master Plan](./00_MASTER_PLAN.md)** | Vision, foundation decision (why Odoo 19 Community), product & go-to-market model, module portfolio, roadmap, pricing, team, risks. The "why" and "what". |
| 01 | **[Claude Code Build Spec](./01_CLAUDE_CODE_BUILD_SPEC.md)** | Repo-ready: `CLAUDE.md` content, folder structure, tech stack, coding standards, environment setup, and a phase-by-phase backlog of build tickets Claude Code can pick up. The "how to build". |
| 02 | **[Module Requirement Specs](./02_MODULE_REQUIREMENT_SPECS.md)** | Detailed functional + technical spec for every core module: data models, workflows, screens, roles, acceptance criteria, Ethiopia-specific rules. The "what each module must do". |
| 03 | **[Architecture & Data Model](./03_ARCHITECTURE_AND_DATA_MODEL.md)** | System architecture, tenancy model, entity-relationship model, API design, integrations (Telebirr, SMS, e-invoicing), deployment topology, security controls. The "how it fits together". |
| 04 | **[Full ERP Module Catalog](./04_ERP_MODULE_CATALOG.md)** | Every module you can offer — the six from the proposal plus all standard ERP modules (project, expenses, assets, docs, quality, maintenance, helpdesk, subscriptions, eCommerce, marketing, recruitment, etc.) and pre-bundled industry "starter packs". The "complete menu". |
| 05 | **[Differentiation & Market Playbook](./05_DIFFERENTIATION_AND_MARKET_PLAYBOOK.md)** | Researched: how ERP builders stand out (verticalization, localization moat, productized delivery, change management, recurring/white-label revenue, modern UX, selective AI) and how to win Ethiopian clients. The "how to compete and win". |
| 06 | **[Customization Guide](./06_CUSTOMIZATION_GUIDE.md)** | How to fully tailor per client — a 4-layer model covering modules on/off, branding (colors, logo, fonts, naming, white-label), language, roles, custom fields/workflows, and client-specific modules — kept maintainable across many clients. The "how to customize". |

## How to use it

1. **Read 00 first** — it contains the key decisions. If you disagree with the foundation choice, everything downstream adapts.
2. **Hand 01 to Claude Code** as the starting brief. Drop `CLAUDE.md` into the repo root, then work the ticket backlog phase by phase.
3. **Use 02 as the source of truth** when implementing or demoing a module to a client. Each module has a client-facing "configuration questionnaire" you can reuse for every new company.
4. **Use 03 for architecture reviews** and when onboarding a new engineer, or when a client asks security/integration questions.

## Key de