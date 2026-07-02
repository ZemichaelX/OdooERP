# 06 — Customization Guide: Tailoring SapianERP Per Client

**Version:** 1.0 · **Date:** July 2026
**Purpose:** Your point 3 — exactly how you customize the ERP for each company you sell to: adding/removing modules, brand colors, naming, fonts, and every other lever (fields, workflows, reports, roles, language, integrations). Written so a consultant can do most of it without code, and an engineer/Claude Code knows how to do the rest cleanly.

---

## 1. The golden principle of safe customization

**Layered customization, never core edits.** Every client difference lives in one of four layers, from cheapest/safest to most involved:

```
Layer 1 — CONFIGURATION   (settings & wizard toggles)      → no code, minutes,   safe on upgrade
Layer 2 — DATA/CONTENT    (branding, templates, roles)     → no code, hours,      safe on upgrade
Layer 3 — NO-CODE STUDIO  (custom fields/views/automations)→ no code, hours,      review on upgrade
Layer 4 — CLIENT MODULE   (sapian_client_<name> code)      → code, days,          test on upgrade
```

Always solve a client need at the **lowest layer that works**. Never modify Odoo core or the shared `sapian_*` / `l10n_et_*` product modules for one client — client-specifics go in that client's own module. This keeps every client upgradeable and the product clean.

---

## 2. Layer 1 — Configuration (no code)

Done in the **onboarding wizard** and **Settings** (doc 02 §0). Covers most client differences.

**Adding / removing modules.**
- The **module catalog** screen lists every module (doc 04) with an on/off toggle. Enabling installs the Odoo app + its Ethiopian defaults + standard roles; disabling hides it.
- Sell a client a **starter pack** (doc 04 §3) to switch on a whole vertical bundle at once, then add/remove individual modules as needs change.
- Modules can be added later as the client grows — this is the "start small, expand" motion (doc 05). No re-implementation; just enable + configure + train.

**Company & operational config (per client):**
- Company identity: legal name, TIN/VAT number, addresses, fiscal year, base currency (ETB), multi-company if several legal entities.
- Tax: VAT registration on/off, withholding rules, tax rates (from the versioned localization tables).
- Inventory: number of warehouses/locations, shelf/bin tracking, expiry alert lead time, approval requirements.
- Sales: credit limits, price lists, pipeline stages, invoice fields.
- HR/Payroll: salary components, leave types/accruals, attendance method, pension applicability.
- Numbering: invoice/order/PO sequences and prefixes (e.g., `INV/2026/0001`).

> Rule of thumb: if two clients differ only in *settings*, that's Layer 1 — no engineering.

---

## 3. Layer 2 — Branding, content & roles (no code)

This is the "make it *theirs*" layer you asked about — colors, naming, fonts, logo, and more.

### 3.1 Visual branding (`sapian_theme`, per-client settings)
| Element | How | Notes |
|--------|-----|-------|
| **Logo** | Upload in Settings → Company / Branding | App bar, login page, printed documents (invoices, payslips, reports) |
| **Primary/accent colors** | Brand color pickers in the theme settings | Drives buttons, headers, links, highlights across the UI |
| **Fonts / typography** | Select from a font list or load a client web-font | UI font + document font; supports Amharic-capable fonts (e.g., Noto Sans Ethiopic) |
| **Login page** | Background image, tagline, logo | First impression, fully client-branded |
| **Favicon** | Upload | Browser tab icon |
| **Email/document templates** | Header/footer/colors editable | Invoices, quotations, POs, payslips carry client branding |
| **Report layouts** | Choose layout + colors + logo position | Odoo's document layout settings, extended |
| **App/system name** | Rename the product for the client (white-label) | See naming below |

### 3.2 Naming & white-labeling
- **System/app name & title:** rename "SapianERP" to the client's preferred name (or keep your brand) via theme/white-label settings — browser title, menus, "powered by" line.
- **Menu & terminology renaming:** clients often use their own words (e.g., "Customers" → "Pharmacies", "Vendors" → "Suppliers", "Employees" → "Staff"). Rename menu items, model labels, and field labels via translation/label overrides (Layer 2/3) without touching logic.
- **Language:** English, Amharic, or both, with a user-level toggle. Printed documents can be bilingual. Additional Ethiopian languages (e.g., Afaan Oromoo, Tigrinya) can be added as translation files.
- **Domain:** each client gets their own subdomain (`client.sapianerp.com`) or their own domain, with TLS.

### 3.3 Roles & permissions (per client)
- Assign users to **standard role templates** per module (doc 02 §10), or clone-and-adjust a template for a client's org structure.
- Set approval thresholds (e.g., PO approval above an amount), separation-of-duties (reps create / finance validates), and portal scoping (customers see only their own records).

### 3.4 Data & starting content
- Chart of accounts (Ethiopian template, adjusted to client), tax codes, journals.
- Master data import via `data-templates/` spreadsheets (products, partners, employees, opening balances) with validation.
- Sample dashboards and reports pre-loaded per pack.

---

## 4. Layer 3 — No-code Studio-style customization

For custom **fields, screens, and simple automations** without a client module. Odoo's official *Studio* is Enterprise-only, so the plan includes building an in-house **Studio-style customizer** (`sapian_studio`, doc 04 §G) — or, per client, an engineer/Claude Code applies these as small data-driven changes.

What this layer covers:
- **Custom fields:** add a field to any form (e.g., "Cold-chain required?" on a product, "Region" on a customer) — stored per client, shown on views and reports.
- **View tweaks:** show/hide fields, reorder, add tabs, rename labels, adjust list columns.
- **Automations (`base_automation`):** "when X happens, do Y" rules — e.g., email the manager when a high-value order is placed, auto-tag customers by region, create an activity when a lot nears expiry.
- **Server actions & scheduled jobs:** simple recurring tasks (reminders, status rollups).
- **Report/PDF tweaks:** add a field or logo to a printed document.

These are configuration-data changes (stored in the DB / small XML), reviewed on Odoo upgrades but far lighter than code.

---

## 5. Layer 4 — Client-specific module (`sapian_client_<name>`)

When a client needs true bespoke logic that config/Studio can't express (a unique approval chain, a custom pricing algorithm, an integration with their existing system, a special printed form). Rules (from doc 01):

- Create a dedicated module `sapian_client_<name>` — **all** that client's custom code lives here, nothing leaks into the shared product.
- Extend via inheritance (`_inherit`, view `xpath`), never edit core or shared modules.
- Ship with tests, security rules, translations, and a README.
- Keep it small and well-bounded so Odoo upgrades only require re-testing this module.

**Decision test:** *Can I do this in Settings? → Layer 1. Just branding/labels/roles/data? → Layer 2. A field/view/automation? → Layer 3. Genuinely new logic? → Layer 4.* Push work down the layers.

---

## 6. The per-client customization workflow (operational)

Reuse this for every sale (ties to the delivery playbook, doc 00 §6 and the checklist in doc 01 §9):

1. **Discovery:** run each enabled module's **client configuration questionnaire** (doc 02) → capture modules, branding, terminology, roles, integrations, data.
2. **Provision:** `provision_client.sh` → isolated instance + subdomain + TLS.
3. **Enable modules** (Layer 1) from the questionnaire / chosen starter pack.
4. **Brand it** (Layer 2): logo, colors, fonts, naming, language, templates, roles.
5. **Configure operations** (Layer 1): warehouses, taxes, payroll, numbering, credit limits, etc.
6. **Migrate data:** import master data via templates; validate.
7. **Studio tweaks** (Layer 3) for small custom fields/automations they asked for.
8. **Client module** (Layer 4) only if a true bespoke requirement remains.
9. **Train + UAT + sign-off**, then go-live, hypercare, and support.

Standard clients finish at step 6–7 (fast). Only heavily bespoke clients reach step 8.

---

## 7. Customization dimensions — quick reference

| Dimension | Layer | Example |
|-----------|-------|---------|
| Which modules are active | 1 | Retail client: POS + eCommerce on, Manufacturing off |
| Company/tax/inventory/HR settings | 1 | 3 warehouses, VAT on, expiry alert = 60 days |
| Logo, colors, fonts, favicon, login | 2 | Client's green/gold palette + Noto Sans Ethiopic |
| Product/app name (white-label) | 2 | "MediTrack" instead of SapianERP |
| Menu & field terminology | 2/3 | "Customers" → "Pharmacies" |
| Language(s) | 2 | Amharic + English bilingual invoices |
| Roles & approval limits | 2 | PO > 500k needs manager approval |
| Starting data & chart of accounts | 2 | Client's CoA + opening balances |
| Custom fields & views | 3 | "Cold-chain required?" flag on products |
| Automations & alerts | 3 | SMS customer when order ships |
| Custom reports/dashboards | 2/3 | Board-format monthly report |
| Bespoke workflows/logic/integrations | 4 | Integration with client's legacy system |
| Domain & hosting region | infra | client.sapianerp.com, Addis-latency host |

---

## 8. Keeping customization maintainable (so it scales to many clients)

- **Never fork the core or shared modules** for one client — always a client module.
- **Version rate tables and config data** so changes are traceable and upgrade-safe.
- **Document each client's customizations** in their admin manual + config doc (doc 01 Definition of Done) — essential when you have many clients and a small team.
- **Reuse upward:** if three clients ask for the same "custom" thing, promote it into the shared product as a configurable option — your product gets richer with every sale.
- **Test on upgrade:** the CI + module tests (doc 01 §10) are what let you upgrade Odoo across many client instances safely.

> This layered model is exactly what lets you "fully customize per company" (your goal) *without* ending up with dozens of unmaintainable one-off systems. Each client feels bespoke; you maintain one product plus small, isolated client modules.
