# -*- coding: utf-8 -*-
"""Dress-rehearsal tenant provisioning: one realistic month (August 2026) of
business on a fresh company, built through the REAL flows so the books can be
proved afterwards by an independent exam (see ..._exam.py).

Everything is deterministic and dated inside August 2026 so the statutory
period reports have one clean window and the exam's hand-computed expectations
hold whatever the wall clock says. The company is onboarded through the actual
sapian.onboarding.wizard (dogfooding Epic C).

Data volume (per the rehearsal brief):
- 25 sales orders (mixed products; 3 partial deliveries → backorders; 1 return
  + credit note), invoiced on the ORDERED quantity so VAT is decoupled from the
  physical delivery the stock check verifies.
- 12 purchases: 10 goods POs (receipts feed stock; mix above/below the 20,000
  WHT threshold) + 2 direct service bills (a no-TIN domestic supplier → 30%
  punitive, a foreign digital provider → 15%).
- 1 payroll run, 5 employees, incl. one transport allowance above the 2,200/25%
  cap and one pension-exempt foreigner.
- Several bank payments + one vendor CASH payment near the 50,000 cap.
- 1 inventory adjustment (shrinkage on Teff).
"""

from datetime import date

from odoo import Command, api, models

COMPANY_NAME = "Rehearsal Trading PLC"
PERIOD_FROM = date(2026, 8, 1)
PERIOD_TO = date(2026, 8, 31)


def _d(day):
    """An August-2026 date for the given day-of-month."""
    return date(2026, 8, day)


class SapianDressRehearsal(models.AbstractModel):
    _name = "sapian.dress.rehearsal"
    _description = "SapianERP Dress-Rehearsal Provisioning"

    # ------------------------------------------------------------------ entry
    @api.model
    def _provision(self, company_name=COMPANY_NAME):
        """Provision the whole rehearsal tenant and return the company.

        Not idempotent by design: each rehearsal is a fresh company (the script
        drops the DB; the tests run in a rolled-back transaction), so the exam
        always sees exactly one clean month.
        """
        company = self._onboard_company(company_name)
        self._ensure_warehouse(company)
        env = self.env(context=dict(self.env.context, allowed_company_ids=company.ids))
        demo = env["sapian.dress.rehearsal"].with_company(company)
        data = {}
        data["products"] = demo._create_products()
        data["customers"] = demo._create_customers()
        data["suppliers"] = demo._create_suppliers()
        data["employees"] = demo._create_employees()
        data["purchases"] = demo._run_purchases(data["suppliers"], data["products"])
        data["sales"] = demo._run_sales(data["customers"], data["products"])
        data["adjustment"] = demo._run_inventory_adjustment(data["products"])
        data["payroll"] = demo._run_payroll(data["employees"])
        demo._run_payments(data["sales"], data["purchases"], data["suppliers"])
        demo._create_report_periods()
        return company

    @api.model
    def _provision_shell(self, company_name):
        """Onboard a company with just the master data (no month of
        transactions) — enough for the role walkthroughs to drive fresh
        receive/bill/payroll actions. Returns the company."""
        company = self._onboard_company(company_name)
        self._ensure_warehouse(company)
        env = self.env(context=dict(self.env.context, allowed_company_ids=company.ids))
        demo = env["sapian.dress.rehearsal"].with_company(company)
        demo._create_products()
        demo._create_customers()
        demo._create_suppliers()
        demo._create_employees()
        return company

    # ----------------------------------------------------------- onboarding
    @api.model
    def _onboard_company(self, company_name):
        """Create a bare company and push it through the onboarding wizard."""
        company = self.env["res.company"].create({"name": company_name})
        catalog = self.env["sapian.module.catalog"]._ensure_default_catalog(company)
        wizard = (
            self.env["sapian.onboarding.wizard"]
            .with_company(company)
            .create(
                {
                    "company_id": company.id,
                    "company_name": company_name,
                    "tin": "0090807060",
                    "street": "Bole Sub-city, Woreda 03",
                    "city": "Addis Ababa",
                    "fiscal_year": "ethiopian",
                    "primary_color": "#2b6cb0",
                    "module_catalog_ids": [Command.set(catalog.ids)],
                }
            )
        )
        wizard.action_apply()
        return company

    @api.model
    def _ensure_warehouse(self, company):
        """stock auto-creates a warehouse for a new company only in test mode;
        at script-load time we create it ourselves."""
        warehouse_model = self.env["stock.warehouse"].sudo()
        if not warehouse_model.search_count([("company_id", "=", company.id)]):
            warehouse_model.create({"company_id": company.id})

    # --------------------------------------------------------- master data
    def _create_products(self):
        """Four storable goods + one service, ETB-priced, invoiced on order."""
        product_model = self.env["product.product"]
        catalogue = {
            "teff": ("Teff Flour 25kg — የጤፍ ዱቄት", "consu", True, 3000, 2000),
            "coffee": ("Ethiopian Coffee 5kg — ቡና", "consu", True, 5000, 3500),
            "oil": ("Cooking Oil 20L — የምግብ ዘይት", "consu", True, 4000, 3000),
            "sugar": ("Sugar 50kg — ስኳር", "consu", True, 2000, 1400),
            "consulting": ("Business Consulting — የንግድ ምክር", "service", False, 10000, 0),
        }
        products = {}
        for key, (name, ptype, storable, price, cost) in catalogue.items():
            products[key] = product_model.create(
                {
                    "name": name,
                    "type": ptype,
                    "is_storable": storable,
                    "invoice_policy": "order",
                    "list_price": price,
                    "standard_price": cost,
                }
            )
        return products

    def _create_customers(self):
        """Four Ethiopian customers with TINs."""
        partner_model = self.env["res.partner"]
        ethiopia = self.env.ref("base.et")
        specs = [
            ("Ambassel Retail PLC — አምባሰል", "Addis Ababa", "0021212121"),
            ("Bahir Dar Wholesale — ባህር ዳር", "Bahir Dar", "0022222222"),
            ("Dire Trading — ድሬ", "Dire Dawa", "0023232323"),
            ("Mekelle Distributors — መቀሌ", "Mekelle", "0024242424"),
        ]
        return [
            partner_model.create(
                {
                    "name": name,
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": city,
                    "l10n_et_tin": tin,
                }
            )
            for name, city, tin in specs
        ]

    def _create_suppliers(self):
        """The three WHT compliance profiles."""
        partner_model = self.env["res.partner"]
        ethiopia = self.env.ref("base.et")
        return {
            # Compliant: TIN + valid licence → standard 3% WHT on goods > 20,000.
            "compliant": partner_model.create(
                {
                    "name": "Awash Agro Supply PLC — አዋሽ",
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": "Adama",
                    "l10n_et_tin": "0011002200",
                    "l10n_et_business_licence_no": "AA/1122/2016",
                    "l10n_et_business_licence_expiry": "2030-06-30",
                }
            ),
            # Domestic, no TIN → 30% punitive WHT + MISSING on the summary.
            "no_tin": partner_model.create(
                {
                    "name": "Habesha Facilities Services — ሐበሻ",
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": "Addis Ababa",
                }
            ),
            # Foreign digital provider → 15% WHT, "N/A (foreign)" TIN column.
            "foreign": partner_model.create(
                {
                    "name": "CloudServe Digital Inc.",
                    "is_company": True,
                    "country_id": self.env.ref("base.us").id,
                    "l10n_et_is_foreign_digital": True,
                }
            ),
        }

    def _create_employees(self):
        """Five employees exercising every payroll path (see the exam for the
        hand-computed expectations)."""
        company = self.env.company
        ethiopia = self.env.ref("base.et")
        employee_model = self.env["hr.employee"]

        def employee(name, wage, country, tin, pension_id):
            record = employee_model.create(
                {
                    "name": name,
                    "company_id": company.id,
                    "country_id": country.id,
                    "l10n_et_tin": tin,
                    "l10n_et_pension_id": pension_id,
                }
            )
            record.sudo().version_id.write({"wage": wage})
            return record

        usa = self.env.ref("base.us")
        return {
            # basic 6,000 + transport 3,000 (25% of 6,000 = 1,500 binds < 2,200).
            "transport": employee(
                "Almaz Bekele — አልማዝ", 6000, ethiopia, "0101010101", "PID-01"
            ),
            "mid": employee("Bruk Alemu — ብሩክ", 12000, ethiopia, "0102020202", "PID-02"),
            "low": employee("Chala Diro — ጫላ", 3500, ethiopia, "0103030303", "PID-03"),
            "high": employee("Dagmawi Haile — ዳግማዊ", 20000, ethiopia, "0104040404", "PID-04"),
            # Foreign national → pension-exempt.
            "foreigner": employee("Emily Foster", 15000, usa, "0105050505", "PID-05"),
        }

    # --------------------------------------------------------------- buys
    def _run_purchases(self, suppliers, products):
        """10 goods POs (receipts feed stock) + 2 direct service bills.

        Goods bases (× cost) drive WHT: > 20,000 → 3%; <= 20,000 → none.
        """
        goods_plan = [
            # (product, qty, unit_cost, day)  base = qty × unit_cost
            (products["teff"], 100, 2000, 3),  # 200,000 → 3%
            (products["coffee"], 60, 3500, 3),  # 210,000 → 3%
            (products["oil"], 80, 3000, 4),  # 240,000 → 3%
            (products["sugar"], 100, 1400, 4),  # 140,000 → 3%
            (products["teff"], 5, 2000, 5),  # 10,000 → none (<= 20,000)
            (products["sugar"], 4, 1400, 5),  # 5,600 → none
            (products["teff"], 50, 2000, 6),  # 100,000 → 3%
            (products["coffee"], 30, 3500, 6),  # 105,000 → 3%
            (products["oil"], 40, 3000, 7),  # 120,000 → 3%
            (products["teff"], 25, 2000, 7),  # 50,000 → 3%
        ]
        purchases = {"goods": [], "service": []}
        for product, qty, cost, day in goods_plan:
            purchases["goods"].append(
                self._one_goods_purchase(suppliers["compliant"], product, qty, cost, day)
            )
        # Direct service bills: no stock, straight to a posted vendor bill.
        purchases["service"].append(
            self._one_service_bill(suppliers["no_tin"], products["consulting"], 40000, 8)
        )
        purchases["service"].append(
            self._one_service_bill(suppliers["foreign"], products["consulting"], 20000, 8)
        )
        return purchases

    def _one_goods_purchase(self, supplier, product, qty, unit_cost, day):
        """PO → receipt → posted vendor bill for one goods line."""
        order = self.env["purchase.order"].create(
            {
                "partner_id": supplier.id,
                "date_order": _d(day),
                "order_line": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": qty,
                            "price_unit": unit_cost,
                            "date_planned": _d(day),
                        }
                    )
                ],
            }
        )
        order.button_confirm()
        self._validate_pickings(order.picking_ids, _d(day))
        order.action_create_invoice()
        bill = order.invoice_ids
        bill.invoice_date = _d(day)
        bill.action_post()
        return bill

    def _one_service_bill(self, supplier, product, amount, day):
        """A direct posted vendor bill for a service (no stock)."""
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": supplier.id,
                "invoice_date": _d(day),
                "company_id": self.env.company.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "price_unit": amount,
                        }
                    )
                ],
            }
        )
        bill.action_post()
        return bill

    # -------------------------------------------------------------- sells
    def _run_sales(self, customers, products):
        """25 sales orders, invoiced on order. Orders 6/12/18 partially deliver
        (backorder 1 unit); order 20 is fully delivered then returns 2 units
        with a credit note."""
        order_keys = ["teff", "coffee", "oil", "sugar", "consulting"]
        invoices = self.env["account.move"]
        deliveries = []
        return_info = None
        for i in range(25):
            product = products[order_keys[i % 5]]
            customer = customers[i % 4]
            qty = 2 + (i % 4)  # 2..5
            day = 10 + (i % 18)  # spread across the month
            order = self.env["sale.order"].create(
                {
                    "partner_id": customer.id,
                    "date_order": _d(day),
                    "order_line": [
                        Command.create(
                            {
                                "product_id": product.id,
                                "product_uom_qty": qty,
                                "price_unit": product.list_price,
                            }
                        )
                    ],
                }
            )
            order.action_confirm()
            if order.picking_ids:
                partial = 1 if i in (6, 12, 18) else 0
                deliveries.append(self._deliver(order.picking_ids, qty - partial, _d(day + 1)))
            invoice = order._create_invoices()
            invoice.invoice_date = _d(day + 1)
            invoice.action_post()
            invoices |= invoice
            if i == 20:
                return_info = self._return_sale(order, invoice, 2, _d(day + 2))
        return {"invoices": invoices, "deliveries": deliveries, "return": return_info}

    def _deliver(self, pickings, qty, when):
        """Deliver ``qty`` of a single-line picking (partial → backorder)."""
        picking = pickings[0]
        picking.action_assign()
        move = picking.move_ids[0]
        move.quantity = qty
        move.picked = True
        picking._action_done()
        picking.date_done = when
        picking.move_line_ids.write({"date": when})
        return picking

    def _return_sale(self, order, invoice, qty, when):
        """Return ``qty`` units to stock and issue a credit note for them."""
        delivered = order.picking_ids.filtered(lambda p: p.state == "done")
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=delivered[0].id, active_model="stock.picking")
            .create({})
        )
        for line in wizard.product_return_moves:
            line.quantity = qty
        action = wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])
        self._deliver(return_picking, qty, when)
        # Credit note for the returned units.
        reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(
                {
                    "journal_id": invoice.journal_id.id,
                    "date": when,
                }
            )
        )
        result = reversal.reverse_moves()
        credit_note = self.env["account.move"].browse(result["res_id"])
        # The reversal marks the note auto-post ('at_date') because the scripted
        # period is ahead of the container clock; we post it now, in period.
        credit_note.auto_post = "no"
        # Keep only the returned quantity on the credit note.
        credit_note.invoice_line_ids.quantity = qty
        credit_note.invoice_date = when
        credit_note.action_post()
        return {"return_picking": return_picking, "credit_note": credit_note, "qty": qty}

    # ------------------------------------------------------- adjustment
    def _run_inventory_adjustment(self, products):
        """Shrinkage: remove 5 units of Teff from on-hand."""
        product = products["teff"]
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        location = warehouse.lot_stock_id
        quant = self.env["stock.quant"]._gather(product, location)[:1]
        on_hand = quant.quantity if quant else 0.0
        target = on_hand - 5
        adjust = (
            self.env["stock.quant"]
            .with_context(inventory_mode=True)
            .create(
                {
                    "product_id": product.id,
                    "location_id": location.id,
                    "inventory_quantity": target,
                }
            )
        )
        adjust.action_apply_inventory()
        return {"product": product, "delta": -5}

    # ---------------------------------------------------------- payroll
    def _run_payroll(self, employees):
        """One confirmed August payroll run. The transport employee gets a
        transport allowance line (3,000) tied to the statutory allowance type,
        so the exempt/taxable split comes from CONFIG, not a manual flag."""
        run = self.env["l10n.et.payroll.run"].create(
            {
                "company_id": self.env.company.id,
                "date_from": PERIOD_FROM,
                "date_to": PERIOD_TO,
                "employee_ids": [Command.set([e.id for e in employees.values()])],
            }
        )
        run.action_generate_payslips()
        transport_type = self.env["l10n.et.allowance.type"].search(
            [("company_id", "=", self.env.company.id), ("code", "=", "transport")],
            limit=1,
        )
        slip = run.payslip_ids.filtered(lambda s: s.employee_id == employees["transport"])
        self.env["l10n.et.payslip.input"].create(
            {
                "payslip_id": slip.id,
                "name": "Transport Allowance",
                "category": "earning",
                "allowance_type_id": transport_type.id,
                "amount": 3000.0,
            }
        )
        run.action_confirm()
        return run

    # --------------------------------------------------------- payments
    def _run_payments(self, sales, purchases, suppliers):
        """Bank settlement of several invoices/bills + one vendor CASH payment
        near the 50,000 cap (48,000 → posts clean, under the cap)."""
        bank = self._journal("bank")
        cash = self._journal("cash")
        if not cash:
            cash = self.env["account.journal"].create(
                {
                    "name": "Cash",
                    "type": "cash",
                    "code": "CSH",
                    "company_id": self.env.company.id,
                }
            )
        # Settle the first five customer invoices by bank.
        for invoice in sales["invoices"][:5]:
            self._register_payment(invoice, bank)
        # Settle the first three goods bills by bank.
        for bill in purchases["goods"][:3]:
            self._register_payment(bill, bank)
        # One vendor cash payment near the cap (48,000 < 50,000 → no breach).
        self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": suppliers["compliant"].id,
                "amount": 48000.0,
                "date": _d(28),
                "journal_id": cash.id,
                "company_id": self.env.company.id,
            }
        ).action_post()

    def _journal(self, journal_type):
        return self.env["account.journal"].search(
            [("company_id", "=", self.env.company.id), ("type", "=", journal_type)],
            limit=1,
        )

    def _register_payment(self, move, journal):
        """Register a full payment for ``move`` through the standard wizard."""
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=move.ids
        ).create(
            {
                "journal_id": journal.id,
                "payment_date": _d(27),
            }
        ).action_create_payments()

    # ----------------------------------------------------------- reports
    def _create_report_periods(self):
        """The August statutory report records, ready to print and to tie out."""
        period = {
            "company_id": self.env.company.id,
            "date_from": PERIOD_FROM,
            "date_to": PERIOD_TO,
        }
        self.env["l10n.et.vat.declaration"].create(dict(period))
        self.env["l10n.et.wht.summary"].create(dict(period))

    # ------------------------------------------------------------ helper
    def _validate_pickings(self, pickings, when):
        """Fully validate receipts (full quantities)."""
        for picking in pickings:
            picking.action_assign()
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
                move.picked = True
            picking._action_done()
            picking.date_done = when
            picking.move_line_ids.write({"date": when})
