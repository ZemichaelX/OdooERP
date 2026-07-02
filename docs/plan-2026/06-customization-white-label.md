# 06 — Customization & White-Label System

Goal: every client gets an ERP that looks and feels like *their* system — their brand, their vocabulary, their modules, their workflows — without forking the codebase. All customization is **configuration, not code**, unless it passes the decision ladder.

## 1. The decision ladder (enforced contractually and in CLAUDE.md)

1. **Standardize** — can the client adopt the standard process? (70–85% of requests end here)
2. **Configure** — settings, studio-less config: fields on/off, approval thresholds, report layouts
3. **Extend** — a thin, generic, reusable module (goes into the catalog, benefits all clients)
4. **Customize** — client-specific module, only for high-value recurring needs; billed as change order; owner signs an "upgrade tax" acknowledgment

## 2. Branding layer (`sapian_theme`)

Per-tenant branding record, applied by the onboarding wizard:

| Element | Mechanism |
|---|---|
| Product name (white-label) | Debranding: replace "Odoo" everywhere — window titles, dialogs, OdooBot name, email footers, portal ("Powered by <ClientName/SapianERP>") |
| Logo & favicon | Company logo fields → navbar, login page, reports, portal, favicon |
| **Colors** | Primary/secondary/accent color fields → compiled into SCSS variables (backend + website + reports); presets + custom hex |
| **Fonts** | Font selection (incl. Ethiopic-script-safe fonts: Noto Sans Ethiopic, Abyssinica SIL) applied via theme CSS to backend, website, PDF reports |
| Login screen | Client background/logo/welcome text; optional Amharic tagline |
| Report templates | Branded letterhead (logo, address, TIN, VAT reg no.), signature blocks, QR area; per-document overrides (invoice vs delivery note vs payslip) |
| Email templates | Client identity, colors, footer, reply-to; SMS sender name where supported |
| Domain | `client.sapianerp.com` or fully client-owned domain + TLS |

Off-the-shelf debranding modules (Webkul/Softhealer-style) prove this is low-risk; we build our own thin equivalent to avoid third-party license friction.

## 3. Vocabulary & naming customization

- **Renaming apps/menus per client:** "Inventory" → "Store Management", "CRM" → "Tender Desk" — via translated terms/menu overrides stored in client config (survives upgrades because it's data).
- **Field label overrides** for key screens (e.g., "Lot" → "Batch No."), kept in a per-tenant terminology table.
- **Language:** English/Amharic user choice; ship our maintained Amharic translation pack for the modules we sell (core Odoo Amharic is partial — completing it for *our* screens is a differentiator).
- Document numbering schemes per client (prefixes, Ethiopian-calendar year in sequence, e.g., `INV/2017EC/0001`).

## 4. Module composition per client

- Onboarding wizard reads the module catalog (05) → client ticks modules → wizard installs, configures defaults, loads demo-or-blank data, sets up roles.
- Post-go-live add/remove via the same catalog (managed uninstall with dependency + data-retention checks).
- Feature flags within modules (e.g., approval-on-transfers on/off, expiry-alert horizon, credit-limit blocking hard/soft) — per-tenant `ir.config_parameter`-backed settings screen, documented automatically into the client's admin manual.

## 5. Workflow & policy customization (config, not code)

- Approval matrix: which documents need approval, above what thresholds, by which role (POs, internal transfers, discounts, expenses, leave).
- Sales policy: quotation validity, credit-limit behavior, auto-invoice on delivery on/off.
- Inventory policy: FEFO/FIFO, expiry alert horizon, negative stock allowed or not, mandatory lot on receipt.
- HR policy: leave types & accrual (default = labor proclamation 1156/2019 minimums), overtime classes, probation length (≤60 working days), payroll rounding.
- Accounting policy: fiscal year (Gregorian or Ethiopian July–June), IFRS statement layout, WHT applicability by partner type, cash-payment cap warning (ETB 30,000 rule).

## 6. Custom fields & simple screens without code

- A constrained "custom fields" capability (curated `ir.model.fields` creation via admin UI) for extra partner/product/employee attributes — with rules: no compute code, prefixed `x_client_`, auto-included in exports and the config manual. Anything beyond this escalates the decision ladder.

## 7. Roles & permissions per client

- Role templates shipped: GM/Executive (read-everything dashboards), Finance, Sales, Warehouse, Procurement, HR, Branch Manager, Auditor (read-only + logs), Portal customer/vendor.
- Onboarding maps client staff → roles; principle of least privilege; the DAT examples are the spec (sales can quote but not validate invoices; warehouse can't see HR).
- Per-client tweaks = record-rule/group config stored as data, exported into the admin manual.

## 8. Client-config manifest (the key operational idea)

Everything above (branding, terminology, modules, flags, roles, policies) serializes into **one versioned YAML/JSON manifest per client**, stored in the repo (`clients/<name>/manifest.yaml`) and applied by `provision_client.sh`:

- Rebuild any client environment from scratch = provision + manifest + data restore.
- A diff of the manifest = the change-order record.
- The admin-manual deliverable (promised in the DAT proposal) is **generated** from the manifest — documentation that can't go stale.
- Claude Code edits manifests, not tenant databases, for config changes → reviewable, testable, reversible.
