# 02 — Module Requirement Specs: SapianERP

**Version:** 1.0 · **Date:** July 2026
**Purpose:** The functional + technical source of truth for every module. Use it to build, to demo, and to run client discovery. Each module has: purpose, key data, workflows, screens, roles, Ethiopia-specific rules, acceptance criteria, and a **client configuration questionnaire** you reuse for every new company.

**How to read a spec:** *Configurable* = the client sets it via the onboarding wizard/settings (no code). *Custom* = needs a client-specific module. Default to configurable.

---

## 0. Core / Company Setup (`sapian_core`, `sapian_theme`)

**Purpose.** The always-installed base: company identity, users, roles, module catalog, Ethiopian defaults, branding. Every other module depends on it.

**Key data.** Company (name, TIN/VAT no., address, logo, fiscal year start, base currency=ETB, languages en/am); User (name, email, role/group, 2FA); Module catalog entry (module, enabled?, config JSON); Branding (colors, logo, login page).

**Workflows.**
- *Onboarding wizard:* company details → choose language(s) → choose modules → set fiscal year & currency → create first admin → seed Ethiopian defaults (chart of accounts, taxes, payroll tables).
- *Module toggle:* enable/disable a catalog module; enabling installs/activates it and its Ethiopian defaults.
- *Role assignment:* assign users to standard security groups per module.

**Screens.** Onboarding wizard (stepper); Settings → Modules (toggle grid); Settings → Company; Users & Roles; Branding.

**Roles.** System Administrator (full), Company Admin (config + users), plus per-module roles defined in each module below.

**Ethiopia-specific.** ETB currency; en/am language toggle; Ethiopian fiscal year (Hamle–Sene) as a selectable default; Ethiopian-calendar display option.

**Acceptance criteria.** A new company can be created end-to-end via the wizard; enabling a module makes it appear with Ethiopian defaults; a non-admin cannot see admin settings; language toggle switches UI to Amharic where translated.

**Client questionnaire.** Legal name & TIN? VAT-registered? Fiscal year start? Languages needed (English/Amharic/both)? Which modules? Who are the admins? Branding assets (logo, colors)?

---

## 1. Inventory & Warehouse (`sapian_inventory`, extends `stock`)

**Purpose.** Single source of truth for stock across warehouses down to shelf/bin, with batch/expiry control and full traceability — the DAT Phase-1 urgent scope, generalized.

**Key data.** Warehouse; Location (hierarchical: warehouse → zone → shelf/bin); Product (with tracking = lot); Lot/Batch (number, expiry date, supplier, import metadata); Stock Move (source, dest, qty, date, user); Import Record (shipment ref, supplier, clearance docs, cost, linked lots); Reordering rule (min/max).

**Workflows.**
- *Receipt:* record incoming goods against a PO → assign lot/batch + expiry → create Import Record → stock increases only via controlled receipt.
- *Internal transfer:* warehouse manager initiates move (warehouse→warehouse, or →delivery van); optional approval; every move logged (audit trail).
- *Expiry monitoring:* scheduled job flags any lot expiring within the configurable lead time (default **3 months**) → notifies responsible users/activities.
- *Delivery integration:* items allocated when an order is prepared; on-hand reduced when shipped; delivery status reflects back to inventory in real time.

**Screens.** Stock by location (drill to shelf/bin); Lot/expiry list with color-coded aging; Import Record form & history; Transfer form with approval; Reordering rules; Inventory aging report.

**Roles.** Warehouse Staff (log moves, receive), Warehouse Manager (approve transfers, adjust), Inventory Viewer (read-only). Warehouse staff **cannot** see HR/payroll data.

**Ethiopia-specific.** Pharma/EFDA option: batch/expiry mandatory, good-distribution audit trail, recall-support (find all customers who received a batch).

**Acceptance criteria.** Can locate any product to shelf/bin with exact qty; a lot within the alert window generates a notification; every stock move is attributable to a user and time; receipt increases stock and updates the PO; expired stock cannot be picked for delivery.

**Client questionnaire.** How many warehouses/locations? Track to shelf/bin? Products with expiry (which)? Expiry alert lead time? Transfer approvals required? Pharma/EFDA compliance needed? Do you run delivery vehicles as stock locations?

---

## 2. Sales & CRM (`sapian_sales`, extends `sale`, `crm`)

**Purpose.** Quotation-to-invoice sales flow, customer profiles, and pipeline for key deals.

**Key data.** Customer (contact, TIN, contract terms, **credit limit**, price list, order/invoice history); Quotation/Sale Order (lines, taxes, delivery terms); Invoice; CRM Lead/Opportunity (stage, expected value, activities, attachments).

**Workflows.**
- *Quote→Order→Invoice:* create quotation → customer approves → one-click to sale order (reserves inventory) → on delivery, auto-generate invoice → finance validates.
- *Credit control:* order confirmation checks customer credit limit; over-limit requires override role.
- *CRM pipeline:* stages Inquiry → Proposal → Negotiation → Won/Lost; reminders/follow-ups; document attachments (for tenders/NGO contracts).
- *Reporting:* sales by product line/region/rep; MoM & YoY; top customers/products.

**Screens.** Customer profile (360°: contacts, terms, history); Quotation/Order form; Pipeline kanban; Sales dashboard.

**Roles.** Sales Rep (create quotes/orders, own pipeline), Sales Manager (all pipelines, reports, overrides), Finance (validate invoices — reps cannot). *Separation of duties: reps create, finance validates.*

**Ethiopia-specific.** Ethiopian VAT invoice layout (VAT 15% breakdown, buyer TIN, bilingual labels); withholding handling where the customer withholds.

**Acceptance criteria.** Confirming an order reserves stock and notifies inventory/delivery; delivery triggers a correct VAT invoice; a rep cannot validate an invoice; over-credit-limit orders are blocked without override; pipeline reports match underlying data.

**Client questionnaire.** Customer types (pharmacy/hospital/retailer/…)? Use credit limits? Price lists/tiers? Need CRM pipeline for tenders? Invoice must show what fields (TIN, VAT no., bilingual)? Who may validate invoices?

---

## 3. Procurement (`sapian_purchase`, extends `purchase`)

**Purpose.** Vendor management, automated replenishment, RFQ→PO, and receipt integration.

**Key data.** Vendor (contacts, payment terms, price lists, **scorecard**: on-time %, quality issues); Purchase Request (auto or manual); RFQ (multi-vendor); Purchase Order (expected dates, linked receipts); Receipt.

**Workflows.**
- *Auto-reorder:* min/max rules trigger a Purchase Request when stock falls below threshold (or on backorder).
- *RFQ→PO:* procurement sends RFQs to multiple vendors → compare price/lead time → convert winning quote to PO.
- *Receipt loop:* goods arrive → warehouse records receipt → PO auto-updates (full/partial); inventory rises via controlled receipt only.

**Screens.** Vendor directory + scorecard; Purchase Requests queue; RFQ comparison view; PO form with receipt status.

**Roles.** Procurement Officer (create PR/RFQ/PO), Procurement Manager (approve PO above threshold), Receiver (record receipts).

**Ethiopia-specific.** Withholding tax on qualifying purchases auto-applied; import-purchase metadata links to Inventory Import Record.

**Acceptance criteria.** Low stock generates a PR; RFQ compares ≥2 vendors; PO shows accurate received vs ordered; receipt updates inventory + PO; withholding applied where configured.

**Client questionnaire.** Multi-vendor sourcing per product? Reorder thresholds per product? PO approval limits/approvers? Track vendor performance? Import purchases (customs metadata)?

---

## 4. Accounting & Finance (`l10n_et_accounting`, extends `account`)

**Purpose.** Double-entry accounting localized for Ethiopia, with tax, bank reconciliation, and management reporting. Auto-posts from operations.

**Key data.** Ethiopian **Chart of Accounts**; Journals (Sales, Purchase, Bank, Cash, Payroll, Misc); Tax records (VAT 15%, withholding %); Journal Entries; Bank statements; Fiscal periods.

**Workflows.**
- *Auto-posting:* confirming a customer invoice posts revenue + receivable; a vendor bill posts expense + payable; a stock move posts inventory/COGS; payroll posts salary expense. Operational and financial data stay consistent.
- *Bank reconciliation:* import/enter bank statements → match to recorded payments → reconcile → month-end close.
- *Tax:* invoices auto-apply correct VAT; withholding computed on qualifying transactions; generate **VAT declaration** and **withholding** summaries.
- *Reporting:* P&L and Balance Sheet, filterable by branch/department; product/category profitability; cash-flow and revenue-vs-expense charts.

**Screens.** Journal dashboard; Invoice/bill forms; Bank reconciliation workspace; Tax report; P&L/BS report; Finance dashboard.

**Roles.** Accountant (entries, reconciliation), Finance Manager (validate, close periods, tax filing), Auditor (read-only + audit trail).

**Ethiopia-specific.** VAT **15%**; VAT registration threshold **ETB 1,000,000** turnover (flag/advise); withholding tax (commonly **2%**) on qualifying purchases; reverse-VAT on imported services; Ethiopian GAAP or IFRS selectable; Ethiopian fiscal year; rate tables are **versioned config** with effective dates.

**Acceptance criteria.** Each operational transaction posts the correct double entry; VAT on an invoice equals 15% of taxable base; VAT declaration totals reconcile to journals; bank reconciliation balances; P&L and BS tie out; changing a future tax rate does not alter historical entries.

**Client questionnaire.** VAT-registered (rate/exemptions)? Withholding applicable (rate)? IFRS or Ethiopian GAAP? Branches/cost centers to report by? Which banks (statement formats)? Existing chart of accounts to map? Opening balances date?

---

## 5. HR & Payroll (`sapian_hr`, `l10n_et_payroll`, extends `hr*`)

**Purpose.** Employee lifecycle, attendance/leave, Ethiopian payroll, and appraisals — one source of truth for HR, integrated with accounting.

**Key data.** Employee (personal, position, department, supervisor, hire date, **citizen flag**, documents, org chart); Attendance; Leave (type, balance, request, approval); Salary structure (allowances, deductions); Payslip; PAYE band table (versioned); Pension config; Appraisal (KPIs, reviews).

**Workflows.**
- *Attendance & leave:* attendance via kiosk/portal (optional biometric import); employee requests leave → routes to manager → balance updated.
- *Payroll run:* one-click monthly batch → pulls attendance (absences/overtime) → computes gross, **PAYE**, **pension**, allowances/deductions → net pay → payslips → payroll register → **bank/Telebirr salary export**.
- *Accounting post:* payroll posts salary-expense entries to the Payroll journal.
- *Appraisals:* schedule reviews, set KPIs/goals, record feedback (self-service, optional 360°).
- *Offboarding:* HR termination revokes system access automatically.

**Screens.** Employee file + org chart; Attendance/leave calendar & balances; Payroll run wizard; Payslip; Appraisal form.

**Roles.** Employee (self-service: own leave/attendance/payslip), Manager (approve team leave, appraisals), HR Officer (records, payroll), HR Manager (approve payroll, structures). Payroll data restricted to HR + the employee.

**Ethiopia-specific (verify before each go-live).**
- **PAYE 2026:** progressive, **6 brackets**, tax-free up to **ETB 2,000/month**, top rate **35%** above **ETB 14,000/month**.
- **Pension:** **7% employee + 11% employer**, max insurable earning **ETB 15,000/month**, Ethiopian citizens (citizen flag governs applicability).
- Overtime/allowance rules per Ethiopian labor law; payslip in local format; Ethiopian-calendar pay periods optional.

**Acceptance criteria.** A payslip's PAYE and pension match hand-calculated golden values for sample salaries; net pay = gross − PAYE − pension − other deductions + allowances; payroll posts correct accounting entries; a non-HR user cannot open payroll; termination removes access; changing next year's PAYE table leaves prior payslips unchanged.

**Client questionnaire.** Headcount & departments? Salary components (allowances/deductions)? Overtime policy? Attendance method (manual/kiosk/biometric)? Leave types & accrual? All employees Ethiopian citizens (pension)? Salary payout via bank and/or Telebirr? Appraisal cycle?

---

## 6. Website & Online Portal (`sapian_website`, `sapian_portal`, extends `website`, `portal`)

**Purpose.** A branded public site plus self-service portal for customers/partners — the DAT Phase-2 scope, generalized.

**Key data.** Website pages/content (staff-editable); Inquiry/Request form submissions (→ Sales/CRM); Partner directory entries (logo, region, contacts); Portal user (linked to customer, sees own orders/invoices/documents).

**Workflows.**
- *Content management:* staff edit pages via the website builder (news, profile, leadership).
- *Request form:* external party submits a request (e.g., medicine/product request) → creates a lead/quotation linked to inventory availability.
- *Portal self-service:* customers log in to see order status, invoices, documents.
- *Partner directory:* managed in ERP, published to the site automatically.

**Screens.** Public site (profile, services, directory, request form); Portal home (my orders/invoices/documents).

**Roles.** Website Editor (content), Portal User (own records only, strictly scoped by record rules).

**Ethiopia-specific.** Bilingual (English/Amharic) site & forms; Telebirr payment option on portal invoices (via Integrations).

**Acceptance criteria.** Staff can edit content without a developer; a submitted request appears as a lead/quotation with availability checked; a portal user sees only their own records; directory updates in ERP reflect on the site.

**Client questionnaire.** Need a public website (or portal only)? Bilingual? What request/inquiry forms? Should customers self-serve orders/invoices? Online payment (Telebirr) on the portal? Partner directory content?

---

## 7. Delivery & Fleet (optional, `sapian_delivery`, extends `fleet`, `stock`)

**Purpose.** Plan and track deliveries and vehicles for companies that run their own distribution (like DAT).

**Key data.** Vehicle (record, capacity, maintenance); Delivery/Trip (orders, route, driver, status); Delivery status events.

**Workflows.** Plan a trip (group orders) → allocate stock → dispatch (reduce on-hand) → status updates (in transit/delivered) sync to inventory and order status in real time.

**Roles.** Dispatcher (plan/assign), Driver (status updates via portal/app), Fleet Manager (vehicles, maintenance).

**Acceptance criteria.** Dispatching decrements inventory; delivery status is visible on the order and (if enabled) the customer portal; vehicle records track maintenance.

**Client questionnaire.** Own delivery fleet? Route planning needed? Driver status updates (how)? Track vehicle maintenance/costs?

---

## 8. Cross-cutting: Dashboards & Reporting (`sapian_dashboards`)

**Purpose.** Role-based real-time dashboards for decision-makers (DAT objective: real-time visibility).

**Content.** Executive: sales performance, inventory status/aging, financial metrics (P&L snapshot, cash), HR indicators. Per-role home dashboards (warehouse, sales, finance, HR). Charts and drill-downs.

**Acceptance criteria.** Dashboards reflect live data; each role sees only permitted metrics; loads within acceptable time on the production instance.

**Client questionnaire.** Which KPIs matter to management? Who sees what? Any board/regulator report formats required?

---

## 9. Cross-cutting: Integrations (`sapian_telebirr`, `sapian_sms`, `l10n_et_einvoice`)

- **Telebirr payments:** collect (portal/POS) and reconcile mobile-money payments; also salary payout export. Keys via env; sandbox + live. *Confirm current API/terms per client.*
- **SMS notifications:** order confirmations, out-for-delivery, payment reminders via SMS gateway / Ethio Telecom. Templated, bilingual.
- **Email:** SMTP for confirmations and system notifications.
- **E-invoicing:** structured invoice export + adapter for the Ministry of Revenue e-invoicing mandate. *Confirm mandate applicability + API per client before committing.*
- **Devices:** barcode scanners (inventory), biometric attendance (HR) via adapter interfaces.

**Acceptance criteria (each integration).** Runs in sandbox first; failures are logged and retried; no secrets in code; a client can enable/disable and configure it without code changes.

**Client questionnaire.** Accept Telebirr? SMS notifications (which events)? SMTP details? Subject to e-invoicing? Barcode/biometric hardware?

---

## 10. Security roles matrix (baseline, per doc 03 for detail)

| Role | Inventory | Sales/CRM | Procurement | Accounting | HR/Payroll | Admin |
|------|-----------|-----------|-------------|------------|------------|-------|
| Warehouse Staff | R/W | – | receive | – | – | – |
| Sales Rep | R | R/W (own) | – | – | – | – |
| Procurement Officer | R | – | R/W | – | – | – |
| Accountant | R | R (invoices) | R (bills) | R/W | – | – |
| Finance Manager | R | validate | R | R/W + close | – | – |
| HR Officer | – | – | – | – | R/W | – |
| Manager (line) | R (team) | R (team) | – | – | approve team leave | – |
| Company Admin | R | R | R | R | R | config/users |
| System Admin | full | full | full | full | full | full |

*Least privilege by default; every custom model ships with access rules. Payroll and finance are the most restricted.*

---

## 11. Universal acceptance (matches the DAT final acceptance test)

A full "day-in-the-life" integration passes: procurement reorders → PO → receipt (inventory up, correct lot/expiry) → sales quote → order (stock reserved) → delivery (inventory down) → VAT invoice → payment (incl. Telebirr) → accounting entries posted → payroll run for the month → salary entries posted → dashboards reflect all of it — with each step attributable, permission-checked, and audit-logged.
