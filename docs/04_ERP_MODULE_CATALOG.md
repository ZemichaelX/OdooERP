# 04 — Full ERP Module Catalog: SapianERP

**Version:** 1.0 · **Date:** July 2026
**Purpose:** The complete menu of modules you can offer clients — the six from the DAT proposal, the extras already added in the plan, **plus every other standard ERP module** a modern ERP should carry. Each client enables a subset; this is your "catalog" for sales and for the onboarding wizard.

> **Answering your point 1:** Yes — the plan already went beyond the proposal (Delivery/Fleet, Manufacturing, POS, Dashboards, Integrations). This document adds the remaining standard modules so nothing is missing. Everything maps to an existing Odoo 19 Community app where one exists, so most of the catalog is *configuration*, not new code.

---

## 1. How to read this catalog

- **Tier** — how central it is: **Core** (almost every client), **Common** (many clients), **Optional/Vertical** (specific businesses).
- **Odoo base** — the Community app you configure/extend (so build cost is low). "custom" = you build it.
- **Your layer** — the Ethiopian/product value you add on top.
- **Sell it as** — the packaging angle.

Modules already specified in detail in doc 02 are marked ✅ (spec exists). New ones added here are marked ➕ and get a short spec inline.

---

## 2. The catalog

### A. Finance & Accounting
| Module | Tier | Odoo base | Your layer | Notes |
|--------|------|-----------|------------|-------|
| ✅ Accounting & Finance | Core | `account` | `l10n_et_accounting` (VAT, withholding, CoA, reports) | Doc 02 §4 |
| ➕ **Invoicing** (light) | Core | `account` (invoicing-only) | ET invoice layout | For clients who want billing without full accounting |
| ➕ **Expenses** | Common | `hr_expense` | ET per-diem rules, approval flow | Staff expense claims → reimbursement → accounting |
| ➕ **Asset Management / Depreciation** | Common | `account_asset` | ET depreciation schedules | Track fixed assets, auto-depreciation entries |
| ➕ **Budgets** | Common | `account_budget` | budget-vs-actual dashboard | Departmental budget control |
| ➕ **Analytic / Cost Accounting** | Common | `analytic` | cost-center reporting by branch/project | Profitability by branch/product/project |
| ➕ **Multi-currency & Consolidation** | Optional | `account` | ETB base + FX handling | For importers dealing in USD/EUR (like DAT) |

**➕ Expenses (spec).** Employee submits an expense with receipt → manager approves → posts to accounting → reimbursed via bank/Telebirr. Roles: Employee, Manager, Finance. ET: per-diem and mileage rate config.
**➕ Assets (spec).** Register asset, set method/duration, auto-post depreciation, dispose/sell with gain/loss entry. Feeds Balance Sheet.

### B. Supply Chain & Operations
| Module | Tier | Odoo base | Your layer | Notes |
|--------|------|-----------|------------|-------|
| ✅ Inventory & Warehouse | Core | `stock` | `sapian_inventory` (expiry, import log) | Doc 02 §1 |
| ✅ Procurement / Purchase | Core | `purchase` | reorder pack, scorecards | Doc 02 §3 |
| ✅ Delivery & Fleet | Optional | `fleet`, `stock` | delivery↔inventory sync | Doc 02 §7 |
| ➕ **Barcode Operations** | Common | `stock_barcode` (community equiv.) | scanner workflows | Fast receiving/picking with handheld scanners |
| ➕ **Manufacturing (MRP)** | Vertical | `mrp` | BOM, work orders | For producers/assemblers |
| ➕ **Quality Management** | Vertical | `quality` (community add-ons) | QC checkpoints, pharma checks | Inspections at receipt/production |
| ➕ **Maintenance** | Optional | `maintenance` | preventive schedules | Equipment/vehicle maintenance requests |
| ➕ **Repair** | Optional | `repair` | RMA workflow | After-sales repair orders |
| ➕ **Rental** | Vertical | `sale_renting` (community equiv.) | rental pricing | Asset/equipment rental businesses |
| ➕ **Dropshipping / Cross-dock** | Optional | `stock`+`purchase` config | — | Ship direct from vendor to customer |

**➕ Manufacturing (spec).** Bill of Materials → manufacturing order → consume components, produce finished goods → cost roll-up → inventory update. Roles: Production Planner, Operator, Manager. ET: batch/expiry carried to produced goods (pharma).
**➕ Quality (spec).** Define control points (on receipt, in production); pass/fail with corrective action; audit trail for regulators.

### C. Sales & Customer
| Module | Tier | Odoo base | Your layer | Notes |
|--------|------|-----------|------------|-------|
| ✅ Sales & CRM | Core | `sale`, `crm` | credit limits, ET invoice | Doc 02 §2 |
| ✅ Point of Sale (POS) | Vertical | `point_of_sale` | Telebirr POS payment | Retail counters |
| ➕ **eCommerce** | Common | `website_sale` | Telebirr checkout, Amharic | Online store integrated with inventory |
| ➕ **Subscriptions / Recurring Billing** | Common | `sale_subscription` (community equiv.) | recurring invoices | For service clients — and for YOUR own SaaS billing |
| ➕ **Sales Contracts / Agreements** | Optional | `sale` + custom | contract terms, renewals | Framework agreements, tenders |
| ➕ **Loyalty / Promotions** | Optional | `loyalty` | ET promo rules | Retail loyalty, coupons, discounts |
| ➕ **Rental / Field quoting** | Optional | config | — | Combine with services |

**➕ Subscriptions (spec).** Define a plan (price, cycle) → recurring invoice generation → payment (Telebirr/bank) → dunning on failure. Doubles as the billing engine for your own SaaS phase.
**➕ eCommerce (spec).** Product catalog on the website, cart, Telebirr checkout, order → same fulfilment pipeline as Sales; bilingual storefront.

### D. Human Resources
| Module | Tier | Odoo base | Your layer | Notes |
|--------|------|-----------|------------|-------|
| ✅ HR & Payroll | Core | `hr`, `hr_payroll` | `l10n_et_payroll` (PAYE, pension) | Doc 02 §5 |
| ✅ Attendance & Leave | Core | `hr_attendance`, `hr_holidays` | biometric adapter | Doc 02 §5 |
| ✅ Appraisals | Common | `hr_appraisal` | KPI templates | Doc 02 §5 |
| ➕ **Recruitment** | Common | `hr_recruitment` | job portal on website | Applicant tracking → hire → employee |
| ➕ **Employee Self-Service Portal** | Common | `hr` + portal | payslip/leave online | Reduces HR admin load |
| ➕ **Skills & Training** | Optional | `hr_skills` + `elearning` | training records | Staff development, certifications |
| ➕ **Fleet-driver / Timesheet link** | Optional | `hr_timesheet` | — | Labor cost to projects |

**➕ Recruitment (spec).** Post job (website) → applications tracked through stages → interviews/scorecards → offer → convert to employee record. Roles: Recruiter, Hiring Manager.

### E. Services, Projects & Productivity
| Module | Tier | Odoo base | Your layer | Notes |
|--------|------|-----------|------------|-------|
| ➕ **Project Management** | Common | `project` | ET project templates | Tasks, stages, Gantt, deadlines |
| ➕ **Timesheets** | Common | `hr_timesheet` | billable-hours → invoice | Service firms bill time |
| ➕ **Field Service** | Vertical | `industry_fsm` (community equiv.) | dispatch + mobile | On-site jobs, technicians |
| ➕ **Helpdesk / Support Tickets** | Common | `helpdesk` (community add-ons) | SLA, ET channels | Customer support desk |
| ➕ **Document Management (DMS)** | Common | `documents` (community equiv.) | ET compliance filing | Central files, versioning, approvals |
| ➕ **Approvals / Requests** | Common | `approvals` (community equiv.) | ET approval matrices | Generic request-and-approve workflows |
| ➕ **Sign / e-Signature** | Optional | `sign` (community equiv.) | contract signing | Digital signatures on documents |
| ➕ **Knowledge Base / Wiki** | Optional | `knowledge` (community equiv.) | SOPs, manuals | Internal documentation |
| ➕ **Calendar & Scheduling** | Core | `calendar` | — | Shared calendars, meeting booking |

**➕ Project (spec).** Project → tasks with stages/assignees/deadlines → timesheets → progress dashboard; optional link to invoicing for billable projects. Roles: Project Manager, Member.
**➕ Helpdesk (spec).** Ticket via email/portal/website → assignment → SLA timer → resolution → satisfaction rating; knowledge-base deflection.

### F. Marketing & Communication
| Module | Tier | Odoo base | Your layer | Notes |
|--------|------|-----------|------------|-------|
| ✅ Website & Portal | Common | `website`, `portal` | branded theme, forms | Doc 02 §6 |
| ➕ **Email Marketing** | Optional | `mass_mailing` | ET templates, Amharic | Campaigns, newsletters |
| ➕ **SMS Marketing** | Common | `sms` | Ethio Telecom gateway | Bulk SMS, campaigns |
| ➕ **Events** | Optional | `event` | registration + payment | Conferences, trainings |
| ➕ **Social / Live Chat** | Optional | `livechat`, `social` | — | Website chat, social posting |
| ➕ **Surveys** | Optional | `survey` | — | Feedback, assessments |
| ➕ **Marketing Automation** | Optional | `marketing_automation` (community equiv.) | — | Drip campaigns, lead nurturing |

### G. Platform & Cross-cutting (always present or foundational)
| Module | Tier | Odoo base | Your layer | Notes |
|--------|------|-----------|------------|-------|
| ✅ Core / Company Setup | Core | `base`, `web` | onboarding wizard, catalog | Doc 02 §0 |
| ✅ Dashboards & Reporting | Core | `spreadsheet_dashboard` | executive dashboards | Doc 02 §8 |
| ✅ Integrations | Common | custom | Telebirr, SMS, e-invoice | Doc 02 §9 |
| ➕ **Business Intelligence / Spreadsheet** | Common | `spreadsheet` | ET report packs | Live pivot reports, ad-hoc analysis |
| ➕ **Studio-style Customizer** | Common | custom (see doc 06) | no-code field/screen editor | Your in-house alternative to Odoo Studio (Enterprise-only) |
| ➕ **Audit Log** | Core | `base` + custom | immutable trail | Who changed what, when |
| ➕ **Multi-company** | Optional | `base` | group consolidation | Client with several legal entities |
| ➕ **Mobile App (PWA)** | Optional | web/PWA | branded mobile | Field/warehouse/portal on phones |

---

## 3. Industry "starter packs" (pre-bundled module sets — a sales accelerator)

Instead of selling modules one by one, bundle them into vertical packs with Ethiopian defaults. This is a core differentiation move (see doc 05).

| Pack | Modules included | Target client |
|------|------------------|---------------|
| **Pharma / Medical Distribution** (the DAT pack) | Inventory (+expiry/EFDA), Procurement, Sales/CRM, Delivery/Fleet, Accounting, HR/Payroll, Portal, Quality | Drug importers/distributors |
| **Wholesale / Import-Distribution** | Inventory, Procurement (multi-currency), Sales/CRM, Delivery, Accounting, Dashboards | General importers/wholesalers |
| **Retail / Multi-branch** | POS, Inventory, eCommerce, Loyalty, Accounting, HR/Payroll | Shops, chains, supermarkets |
| **Manufacturing** | MRP, Quality, Inventory, Procurement, Maintenance, Sales, Accounting | Producers/assemblers |
| **Professional Services** | Project, Timesheets, Helpdesk, Sales/CRM, Invoicing, HR, Expenses | Agencies, consultancies |
| **Trading + Construction/Projects** | Project, Procurement, Inventory, Accounting, HR, Assets, Documents | Contractors, engineering firms |
| **NGO / Program** | Project, Accounting (fund/analytic), HR/Payroll, Procurement, Documents | NGOs, donor-funded programs |
| **Starter / Small Business** | Invoicing, Inventory (light), Sales/CRM, HR-lite | Small firms, first-time ERP |

Each pack ships with sensible defaults (chart of accounts, roles, taxes, sample dashboards) so onboarding is fast.

---

## 4. Build priority (what to productize first, tied to doc 00 roadmap)

1. **Already scoped Core + localization** (Accounting, Inventory, Sales/CRM, Procurement, HR/Payroll, Website/Portal) — build first; they cover most clients.
2. **High-demand common adds:** Expenses, Assets, Project, Timesheets, Helpdesk, Documents, Approvals, eCommerce, Subscriptions, Recruitment — mostly Odoo configuration, low cost, high sales value.
3. **Vertical/optional:** Manufacturing, Quality, Maintenance, Repair, Rental, Field Service, Events, Marketing Automation — build/enable when a client in that vertical signs.
4. **Platform value:** Studio-style customizer, Audit Log, Mobile PWA — these strengthen the product and the customization story (doc 06).

> Because nearly all of these are Odoo Community apps, "adding a module" is usually enabling + configuring + Ethiopian defaults + testing — not months of development. That's the whole point of building on Odoo.
