# 01 — Complete Extraction: DAT International Trading PLC ERP Proposal

> Source: "ERP Implementation Proposal – DAT International Trading PLC", v1.0, issued Aug 2025 (27 pages).
> Every substantive detail from the proposal is captured here. This is the factual baseline the product plan builds on.

## 1. Project identity

| Field | Value |
|---|---|
| Project name | DAT ERP Implementation |
| Client | DAT International Trading PLC (leading Ethiopian pharmaceutical importer/distributor) |
| Prepared by | Zemichael Muluken |
| Vendor | Sapian Technologies PLC, in partnership with CodeLight Software Engineering PLC |
| Contact | +251 919 125 193 · zemichael@sapiantech.com |
| Issue date | Aug 2025 · Version 1.0 |
| Platform | Odoo (open-source / Community edition by default; Enterprise licensing explicitly excluded from pricing) |

## 2. Client profile & business context

- DAT imports medicines in bulk from global partners, stores them in its own warehouses, and distributes to hospitals and pharmacies using its own fleet of trucks.
- Growth has created complexity in data management, regulatory compliance, and operational workflows; processes rely on manual effort or disparate software → data inconsistencies and inefficiencies.

**Stated needs:**
1. Centralized stock management — single source of truth across multiple warehouses, visibility down to shelf level.
2. Expiry & batch tracking — batch numbers + expiration dates per product, alerts to prevent selling/holding expired stock.
3. Streamlined delivery & fleet coordination — plan/monitor deliveries, optimize truck routes, track shipments.
4. Regulatory documentation & audit readiness — import documents, quality checks, sales records; regulator-ready reports.
5. Scalability — growing transaction volumes, new business lines/branches without performance loss.

## 3. Vision & objectives

**Vision:** a centralized, fully digitized ERP as the company's digital backbone — visibility, accountability, real-time decisions.

**Objectives:**
- Unify medicine tracking: end-to-end traceability from importation → warehouse → customer delivery; every batch tracked.
- Prevent stockouts & expired products: proactive alerts + automated reordering; advance notice of low stock and upcoming expiry.
- Streamline communication/workflow: one platform for procurement, warehouse, sales, delivery, finance, HR; confirmed sales order auto-notifies inventory & delivery; customers get order status updates.
- Real-time dashboards: sales performance, inventory status, financial metrics, HR indicators.
- Automate routine tasks: HR (leave, payroll), Finance (journal entries, tax computation), Sales (quotation→invoice), Procurement (PRs, supplier RFQs).

## 4. Scope of work (in-scope activities)

- Requirements gathering & process mapping per department.
- Configuration of standard Odoo modules + custom features/workflows where needed.
- Integration setup: email (SMTP), SMS notifications, Ethio Telecom APIs.
- Iterative testing and user feedback at the end of each phase.
- Cloud deployment with security hardening and backups.
- End-user & administrator training + user manuals.
- Go-live support. Out-of-scope changes handled via change orders.

## 5. Project deliverables

1. Fully functional ERP (web browser access, optional mobile app) covering inventory, sales, procurement, finance, HR, etc.
2. Complete data migration: opening balances, master records (products, suppliers, customers, employees).
3. User training & documentation: on-site/virtual sessions, training manuals, quick reference guides tailored to the configured system.
4. Hosting & deployment setup: production server, databases, backup routines, VPN/secure remote access if required.
5. Custom dashboards & reports: e.g., inventory aging, sales performance dashboards, financial statements.
6. Deliverables complete only after testing and formal client acceptance.

## 6. Software deliverables

- **Configured Odoo modules:** Inventory, Sales, CRM, Procurement, Accounting, HRM (Ethiopian chart of accounts, lot tracking, etc.).
- **Custom workflows/features:** e.g., a Medicine Request workflow for hospitals via the website; tailored approval flow for internal stock transfers.
- **Website & customer portal:** public site on Odoo website builder (CMS), medicine request form, partner directory; branded front-end.
- **User access roles & permissions:** role-based access, least privilege, mirrors org hierarchy (examples: sales creates quotations but only finance validates invoices; warehouse can't see HR data).
- **Configuration documentation / admin manual:** module settings, custom code, admin tasks (users, master data).
- Built on Odoo's latest stable version; extensible (new apps, integrations).

## 7. Testing services & deliverables

- **Module functional testing** during development (e.g., PO → receipt → stock level update); prompt bug fixes.
- **User Acceptance Testing (UAT)** at end of each phase; vendor provides UAT scripts/test cases; UAT sign-off gates the next phase.
- **Performance/load testing** on production server: simulated concurrent users/transactions (multiple simultaneous sales orders/deliveries).
- **Bug fixes & optimization:** logged, prioritized, resolved pre-go-live; target zero critical bugs at launch.
- **Final acceptance testing:** end-to-end "day-in-the-life" scenario across all modules; client sign-off = go-live readiness.
- All test results and issue logs shared with the client.

## 8. Module-by-module functional detail

### 8.1 Inventory Management (Phase 1 — flagged URGENT)
- Stock tracking by location: multi-warehouse, down to shelf/bin; exact quantities by location.
- Batch & expiry tracking: lot numbers + expiry on all incoming stock; **automatic alerts 3 months before expiry**.
- Import records & history: supplier, batch numbers, quantities, cost, import clearance documents per shipment; batch↔import linkage for audits/recalls.
- Internal transfers & stock moves: warehouse→warehouse/van transfers, optional approval enforcement, full audit trail.
- Integration with delivery operations: allocation on order prep, on-hand reduction at shipment, real-time delivery status reflected in inventory.

### 8.2 Website & Online Portal (Phase 2)
- Public company profile site: mission, services, leadership; staff-editable via Odoo website builder (news, announcements, photos).
- Medicine request submission form: feeds ERP directly → generates inquiry/quotation in Sales, linked to inventory availability.
- Partner directory: global suppliers & local distributors with logos, regions, contacts; managed from the ERP, auto-updates on site.

### 8.3 Sales & CRM (Phase 3)
- Customer profiles & order history: contacts, contract terms, credit limits, full order/invoice history.
- Quotation-to-invoice workflow: quote → one-click sales order → auto-invoice on delivery; inventory reserved on SO confirmation.
- CRM pipeline for key deals: stages (Inquiry → Proposal → Negotiation → Won/Lost), reminders, attachments — for hospital networks/NGO tenders.
- Sales reporting: monthly sales, best-sellers, top customers; by product line/region/rep; YTD & MoM comparisons; graphical dashboards.

### 8.4 Procurement (Phase 4)
- Vendor database & price lists: contacts, payment terms, per-supplier price lists; supplier performance metrics (on-time delivery, quality issues).
- Automated purchase requests: min/max reordering rules trigger PRs on low stock/backorder; officer reviews → RFQ or PO.
- RFQ & PO generation: multi-supplier RFQs, quote comparison (price, lead time), conversion to PO with expected dates.
- Integration with inventory receipts: receipt updates PO (full/partial); stock increases only via controlled receipts.

### 8.5 Accounting & Finance (Phase 5)
- Multi-journal double-entry system: Ethiopian chart of accounts & tax accounts; auto journal entries from all modules; Sales/Purchase/Bank/Cash/Payroll journals; **IFRS or Ethiopian GAAP support**.
- Bank reconciliation: statement import, matching against recorded payments; faster month-end close.
- Tax configuration & reporting: **Ethiopian VAT** on sales/purchases, **withholding taxes**; auto-applied tax codes; VAT declarations and withholding summaries.
- Profitability dashboards: P&L, balance sheet filterable by branch/department; profitability by product/category (COGS linked to inventory); revenue vs. expense and cash-flow charts.

### 8.6 HRM & Payroll (Phase 6)
- Employee records & org structure: personal details, position, department, supervisor, hire date; org chart; attached contracts/ID scans; all HR actions tied to the employee file.
- Attendance & leave: biometric device integration if available (or manual/kiosk entry); leave requests with manager approval routing; leave balance accrual tracking.
- Automated payroll: salary structures with allowances, deductions, **PAYE income tax, pension contributions per Ethiopian labor law**; one-click monthly payslips pulling attendance (absence/overtime); payroll registers, pay summaries, payslip printing, bank transfer list export.
- Performance & appraisal: scheduled reviews, KPIs/goals, manager evaluations, history for promotion/training decisions; optional self-service feedback and 360° reviews.

**Cross-module integration examples:** confirmed payroll posts salary-expense journal entries; employee departure in HR can auto-update user access rights.

## 9. Technology stack

| Layer | Choice |
|---|---|
| ERP backend | Odoo (Python framework) |
| Frontend | HTML5, JavaScript, Bootstrap CSS (Odoo web client + website builder) |
| Database | PostgreSQL |
| Hosting | Cloud — DigitalOcean or AWS (client's choice), Linux server |
| Integrations | SMTP email; SMS gateway / Ethio Telecom SMS API; optional barcode scanners; optional **Telebirr** payments |

## 10. Timeline (14 weeks, 7 phases)

| Phase | Focus | Duration |
|---|---|---|
| 1 | Inventory Management | 6 weeks |
| 2 | Website & Online Portal | 2 weeks |
| 3 | Sales & CRM | 2 weeks |
| 4 | Procurement | 1 week |
| 5 | Accounting & Finance | 1 week |
| 6 | HRM & Payroll | 1 week |
| 7 | Testing & Go-Live | 1 week |

- Phases may overlap in practice; durations assume sequential execution.
- Phase-end demo + UAT sign-off gates progression.
- **Milestones:** Week 0 kickoff · Week 2 website live (internal) · Week 8 core ERP (Inventory, Sales) in UAT · Week 14 go-live.
- Weekly/bi-weekly progress meetings; risks communicated immediately.
- Final week: comprehensive training, final data migration, switch-over.

## 11. Pricing (fixed price, ETB, excl. Odoo Enterprise licenses & VAT)

| Phase / Module | Price (ETB) |
|---|---|
| Inventory Management | 200,000 |
| Website & Online Portal | 100,000 |
| Sales & CRM | 300,000 |
| Procurement | 300,000 |
| Accounting & Finance | 300,000 |
| HRM & Payroll | 300,000 |
| **Total implementation** | **2,200,000** |

**Terms & assumptions:**
- 30% down payment at contract signing; remainder tied to milestones/phase deliveries.
- Hosting fees excluded — estimated 5,000–10,000 ETB/month, payable by client directly to provider.
- On-site training in Addis Ababa included; travel elsewhere billed at actuals.
- Scope changes via change orders.

## 12. Security & compliance commitments

- Role-based access control; sensitive functions (financial approval, payroll data) restricted.
- Two-factor authentication (2FA), especially for admin/remote accounts.
- Daily automated DB backups stored off-site; uptime monitoring; anomaly/downtime alerts.
- Pharmaceutical regulation compliance: batch tracking + expiry monitoring per good distribution practice; reports for authorities (e.g., **Ethiopian Food and Drug Authority**); audit trails on stock moves, purchases, sales.
- Data privacy: GDPR-inspired practices — access controls, minimal retention; GDPR support (export/deletion) if EU data involved.
- Secure development & deployment: security review of customizations, no plain-text sensitive data, HTTPS everywhere, server hardening (firewall, fail2ban).

## 13. Optional maintenance & support plan

- Term: 6 or 12 months, extendable; same monthly rate either way.
- **Cost: 20,000 ETB/month**, fixed for first year post-go-live.
- Includes: 2 dedicated support engineers familiar with the implementation; real-time bug fixes; Odoo patch/security updates; user assistance; minor enhancements & extra reports.
- **SLA:** response within 1 business day for major issues; immediate response for critical (system down); minor requests in 1–2 days.
- Knowledge transfer to client's internal IT during support period.

## 14. Odoo platform features the proposal leans on

- Lot/serial traceability with automated expiry alerts.
- Automated reordering rules + vendor price-list management (buy from cheapest qualified supplier).
- CRM pipeline for tenders/key accounts.
- Double-entry accounting synchronized with every stock move, invoice, payment; bank reconciliation.
- Integrated HR→Payroll→Attendance→(Timesheets) with in-Odoo payroll computation (tax, pension) — no external payroll tool.

## 15. Vendor credentials cited

- Sapian Technologies + CodeLight: nationwide electronic voucher distribution for Ethio Telecom & Safaricom — 35 master agents, 11,000+ retail agents, 2B+ voucher transactions.
- Prior delivery areas: ERP (Odoo & custom), inventory/supply chain, financial & HR platforms, mobile/web apps, e-commerce, healthcare/logistics/fintech.
- Team: software engineers, implementation consultants, UI/UX designers, support staff; Odoo localization experience (Ethiopian tax law, accounting standards, HR regulations).
- Project lead: Zemichael Muluken, Senior ERP Consultant & PM (software development + UX background).

## 16. Next-steps process defined in the proposal

1. Review & approve proposal → 2. Contract + NDA → 3. 30% initial payment → 4. Kickoff meeting (teams, plan, roles, communication channels, preliminary data collection) → 5. Begin Phase 1 (Inventory, urgent).

---

## 17. What this proposal teaches us for the *product* (analysis, not from the PDF)

1. **Phase 1 urgency was inventory** — Ethiopian trading companies feel stock pain first. Lead sales demos with inventory + expiry traceability.
2. **The 6-module set (Inventory, Website/Portal, Sales/CRM, Procurement, Accounting, HR/Payroll) is the reusable core** of a productized offering.
3. **Localization is the moat:** Ethiopian CoA, VAT & withholding, PAYE/pension payroll, EFDA reporting, Telebirr/SMS/Ethio Telecom integrations — none come with stock Odoo.
4. **Fixed-price per module** (100k–300k ETB) is a packaging model clients accept; support at 20k ETB/month is the recurring-revenue seed.
5. **Phase-gated UAT sign-offs and per-phase training** were sales-winning process promises — bake them into the standard delivery methodology.
