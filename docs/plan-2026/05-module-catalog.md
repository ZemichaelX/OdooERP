# 05 — Module Catalog

The sellable unit. Every client engagement = pick modules from this catalog (via the onboarding wizard / proposal generator). Modules marked ⭐ were in the DAT proposal; the rest are the standard additions requested.

## Tier 1 — Core (every deployment)

| Module | Source | Notes |
|---|---|---|
| Contacts / Partners | Odoo | Customers, vendors, Amharic name field (`l10n_et_base`) |
| ⭐ Inventory / Warehouse | Odoo | Multi-warehouse, bin/shelf locations, lots & expiry, internal transfers with approvals, reordering rules |
| ⭐ Sales | Odoo | Quotation → SO → delivery → invoice; credit limits; pricelists |
| ⭐ Invoicing + Accounting | Odoo + OCA (account_financial_report etc.) + `l10n_et_base` | ET chart of accounts, 15% VAT, 3% WHT, multi-journal, bank reconciliation, IFRS-style statements |
| ⭐ Purchase / Procurement | Odoo | Vendor pricelists, RFQ comparison, PO→receipt linkage, supplier performance |
| Settings/Admin: `sapian_core` + `sapian_theme` + `sapian_onboarding` | Sapian | Module catalog, branding, client config |

## Tier 2 — Standard business modules (common add-ons)

| Module | Source | Notes |
|---|---|---|
| ⭐ CRM | Odoo | Pipeline for tenders/key accounts, activities, lead capture from website |
| ⭐ HR: Employees, Leave, Attendance | Odoo + config | Org chart, contracts, ET labor-law leave rules (16d + accrual), overtime classes (1.5/1.75/2/2.5×), biometric import |
| ⭐ Payroll (Ethiopian) | `l10n_et_payroll` (proprietary) | PAYE 1395/2025 bands, pension 7/11, allowances/deductions, payslips, bank transfer export, payroll journal posting |
| ⭐ Website + CMS | Odoo | Company site, blog/news, forms feeding CRM/Sales |
| ⭐ Customer portal | Odoo | Order status, invoices, statements; request forms |
| Expenses | Odoo | Employee expenses with approval + WHT awareness |
| Project + Timesheets | Odoo | Services firms; billable hours → invoicing |
| Helpdesk-lite | OCA (helpdesk_mgmt) | Community substitute for Enterprise Helpdesk |
| Documents-lite | OCA (dms) | Attachments organization; import/clearance docs |
| Approvals | OCA / custom config | Generic approval flows (transfers, POs above threshold, discounts) |
| Fleet | Odoo | Vehicles, fuel, maintenance — pairs with delivery |
| Maintenance | Odoo | Equipment servicing |
| Purchase requisitions | OCA | Internal PR → RFQ flow (the DAT "purchase request" step) |

## Tier 3 — Advanced / premium (subscription-priced)

| Module | Source | Notes |
|---|---|---|
| `l10n_et_reports` | Proprietary | VAT declaration, WHT summary, pension remittance file, payroll tax filing, Ethiopian-calendar period reports |
| `l10n_et_calendar` | Proprietary (build on OCA ethiopic_calendar/pycalcal) | Ge'ez calendar display, EC↔GC conversion, EC fiscal periods |
| `l10n_et_einvoice` | Proprietary | QR-compliant receipts (Directive 188/2024); ITAS e-invoice connector when rollout dates firm |
| `sapian_payments` | Proprietary | Telebirr, Chapa, M-PESA ET, ArifPay payment providers (portal + POS) |
| `sapian_sms` | Proprietary | SMS notifications (order status, expiry alerts, payslip notice) via Ethio Telecom/gateway |
| POS + fiscal compliance | Odoo POS + `vertical_retail` | Fiscal device / QR receipt flow |
| Manufacturing (MRP) | Odoo | BOMs, work orders, costing |
| Quality | OCA | Incoming inspection (pairs with pharma) |
| eCommerce | Odoo | Online store w/ local payments |
| BI dashboards | OCA spreadsheet/dashboard + custom | Management cockpit: sales, stock aging, cash, HR KPIs |
| Multi-branch / multi-company | Odoo config | Branch P&L, inter-branch transfers |
| Marketing (email/SMS campaigns) | Odoo + `sapian_sms` | Campaigns to customer base |
| Recruitment, Appraisal ⭐ | Odoo | Hiring pipeline; KPI-based reviews (DAT asked for appraisals) |
| Subscriptions/contracts | OCA (contract) | Recurring invoicing — also how we bill our own AMC |

## Vertical packs (proprietary differentiators)

### `vertical_pharma` ⭐ (from the DAT blueprint)
- Batch/lot + expiry enforcement on all moves; **configurable expiry alert horizon (default 3 months)** with SMS/email digest; FEFO picking.
- Import shipment records: supplier, batches, quantities, costs, clearance documents; batch↔shipment traceability for recalls/audits.
- EFDA GS1 traceability: 2D DataMatrix (GTIN+serial+batch+expiry) capture & EFDA API/XML export.
- Medicine request portal workflow: hospital/clinic submits → availability check → quotation in Sales.
- Partner directory (suppliers/distributors) published to website.
- Delivery run management: van loading, delivery orders per route, proof of delivery, status → inventory in real time.

### `vertical_trading`
- Landed cost allocation (freight, insurance, customs duty, bank charges) per shipment; LC/import file tracking; customs (eSW) document checklist; multi-currency purchases with NBE rate feed.

### `vertical_retail`
- POS with offline tolerance; QR/fiscal receipt compliance; Telebirr/cash/bank split payments; shift/cashier controls; barcode-first flows.

### `vertical_services` (later)
- Project billing, retainers, timesheet approval, donor/grant reporting dimension for NGOs.

### `vertical_manufacturing` (later)
- MRP + standard costing + scrap tracking, configured for light manufacturing.

## Catalog mechanics (how selling works)

- `sapian.module.catalog` model (in `sapian_core`) lists every sellable module: name, description (EN/AM), tier, price, dependencies, install hook. The onboarding wizard and the proposal generator both read this catalog — **one source of truth for what we sell**.
- Adding/removing a module post-go-live = catalog toggle → managed install/uninstall on the tenant (with pre-flight dependency + data-loss checks).
- Package presets: Essential / Business / Enterprise + vertical = pre-ticked catalog selections (see 03 §5).
