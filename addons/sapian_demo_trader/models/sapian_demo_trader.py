# -*- coding: utf-8 -*-
"""Provisioning of the 'Selam General Trading PLC' demo tenant.

The company is onboarded through the REAL sapian.onboarding.wizard (dogfooding
the Epic C wizard), then one July-2026 month of trading data is created through
the REAL business flows (quotation → delivery → invoice, PO → receipt → bill,
payroll batch), so the tenant doubles as the sales demo with every compliance
feature visibly firing:

- 15% VAT on sales and purchases (Proc 1341/2024)
- 3% WHT on a compliant supplier, 30% punitive on a domestic no-TIN supplier
  (red MISSING row on the WHT summary), 15% on a foreign digital provider
  ("N/A (foreign)" TIN column)
- payroll with a taxable-overtime case and one employee missing a POESSA
  pension ID (fix-before-filing banner on the pension schedule)

Hand-computed month totals (tests enforce): output VAT 8,400 on 56,000; input
VAT 11,250 on 75,000; net VAT −2,850 credit; WHT 1,560 + 4,500 + 1,200 = 7,260;
payroll gross 23,800, PAYE 3,900, pension 1,526/2,398, net 18,374.

All dates are pinned inside July 2026 so every statutory report has one clean
period window with exact GL tie-outs, independent of the wall clock.
"""

from odoo import Command, api, models

DEMO_COMPANY_NAME = "Selam General Trading PLC"
PERIOD_FROM = "2026-07-01"
PERIOD_TO = "2026-07-31"


class SapianDemoTrader(models.AbstractModel):
    _name = "sapian.demo.trader"
    _description = "SapianERP Demo Trader Provisioning"

    @api.model
    def _provision_demo_tenant(self, company_name=DEMO_COMPANY_NAME):
        """Provision the full demo tenant (idempotent by company name).

        Returns the demo company. Called from demo data at install and reused
        verbatim by the golden E2E tests (with a different name, inside the
        test transaction — no module installation happens because this module's
        dependencies already cover every catalog pick).
        """
        existing = self.env["res.company"].search([("name", "=", company_name)], limit=1)
        if existing:
            return existing
        company = self._onboard_company(company_name)
        # stock only auto-creates warehouses for new companies in TEST mode
        # (stock/models/res_company.py); at demo-load time we must create it
        # ourselves or SO confirmation finds no delivery rule.
        warehouse_model = self.env["stock.warehouse"].sudo()
        if not warehouse_model.search_count([("company_id", "=", company.id)]):
            warehouse_model.create({"company_id": company.id})
        env = self.env(context=dict(self.env.context, allowed_company_ids=company.ids))
        demo = env["sapian.demo.trader"].with_company(company)
        products = demo._create_products()
        partners = demo._create_partners()
        employees = demo._create_employees()
        demo._run_sales_flow(partners, products)
        demo._run_purchase_flow(partners, products)
        demo._create_direct_bills(partners, products)
        demo._run_payroll(employees)
        demo._create_report_periods()
        return company

    @api.model
    def _onboard_company(self, company_name):
        """Create a bare company and push it through the onboarding wizard —
        the wizard applies profile, branding, catalog and Ethiopian defaults.

        No module installation can occur here: this module's dependencies
        already include every standard catalog pick, so the wizard's install
        step is a guaranteed no-op (no registry replacement mid-provision).
        """
        company = self.env["res.company"].create({"name": company_name})
        catalog = self.env["sapian.module.catalog"]._ensure_default_catalog(company)
        wizard = (
            self.env["sapian.onboarding.wizard"]
            .with_company(company)
            .create(
                {
                    "company_id": company.id,
                    "company_name": company_name,
                    "tin": "0088776655",
                    "street": "Africa Avenue (Bole Road)",
                    "city": "Addis Ababa",
                    "fiscal_year": "ethiopian",
                    "primary_color": "#1a7f5a",
                    "module_catalog_ids": [Command.set(catalog.ids)],
                }
            )
        )
        wizard.action_apply()
        return company

    def _create_products(self):
        """ETB-priced local products (bilingual names) + an ETB pricelist."""
        self.env["product.pricelist"].create(
            {
                "name": "ETB Retail Pricelist",
                "currency_id": self.env.ref("base.ETB").id,
                "company_id": self.env.company.id,
            }
        )
        product_model = self.env["product.product"]
        return {
            "teff": product_model.create(
                {
                    "name": "Teff Flour 25kg — የጤፍ ዱቄት",
                    "type": "consu",
                    "list_price": 3200,
                    "standard_price": 2600,
                }
            ),
            "coffee": product_model.create(
                {
                    "name": "Ethiopian Coffee Beans 5kg — የቡና ፍሬ",
                    "type": "consu",
                    "list_price": 4500,
                    "standard_price": 3600,
                }
            ),
            "oil": product_model.create(
                {
                    "name": "Sunflower Cooking Oil 20L",
                    "type": "consu",
                    "list_price": 5800,
                    "standard_price": 5000,
                }
            ),
            "consulting": product_model.create(
                {
                    "name": "Business Consulting — የንግድ ምክር",
                    "type": "service",
                    "list_price": 15000,
                }
            ),
        }

    def _create_partners(self):
        """Customers + the three supplier compliance profiles."""
        partner_model = self.env["res.partner"]
        ethiopia = self.env.ref("base.et")
        return {
            "fasika": partner_model.create(
                {
                    "name": "Fasika Supermarket — ፋሲካ ሱፐርማርኬት",
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": "Addis Ababa",
                    "l10n_et_tin": "0022334455",
                    "l10n_et_name_amharic": "ፋሲካ ሱፐርማርኬት",
                }
            ),
            "zemen": partner_model.create(
                {
                    "name": "Zemen Distribution PLC — ዘመን ዲስትሪቢውሽን",
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": "Adama",
                    "l10n_et_tin": "0033445566",
                }
            ),
            # Compliant supplier: TIN + valid licence → standard 3% WHT.
            "awash": partner_model.create(
                {
                    "name": "Awash Agro Industry PLC — አዋሽ አግሮ",
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "l10n_et_tin": "0011223344",
                    "l10n_et_business_licence_no": "AA/5678/2015",
                    "l10n_et_business_licence_expiry": "2030-06-30",
                }
            ),
            # Domestic supplier WITHOUT a TIN → punitive 30% + MISSING row.
            "habesha": partner_model.create(
                {
                    "name": "Habesha General Services — ሐበሻ አገልግሎት",
                    "is_company": True,
                    "country_id": ethiopia.id,
                }
            ),
            # Foreign digital provider → 15% WHT, "N/A (foreign)" TIN column.
            "cloudserve": partner_model.create(
                {
                    "name": "CloudServe Digital Inc.",
                    "is_company": True,
                    "country_id": self.env.ref("base.us").id,
                    "l10n_et_is_foreign_digital": True,
                }
            ),
        }

    def _create_employees(self):
        """Three employees: the two payroll golden cases + one below-threshold
        employee deliberately missing her POESSA pension ID."""
        company = self.env.company
        ethiopia = self.env.ref("base.et")
        bank = self.env["res.bank"].create(
            {"name": "Commercial Bank of Ethiopia", "bic": "CBETETAA"}
        )
        employee_model = self.env["hr.employee"]

        def employee(name, wage, tin, pension_id, account_number):
            record = employee_model.create(
                {
                    "name": name,
                    "company_id": company.id,
                    "country_id": ethiopia.id,
                    "l10n_et_tin": tin,
                    "l10n_et_pension_id": pension_id,
                }
            )
            # sudo: wage/bank fields are HR-group restricted; provisioning runs
            # as the superuser anyway, sudo keeps it explicit.
            record.sudo().version_id.write({"wage": wage})
            if record.work_contact_id:
                account = self.env["res.partner.bank"].create(
                    {
                        "partner_id": record.work_contact_id.id,
                        "bank_id": bank.id,
                        "acc_number": account_number,
                    }
                )
                record.sudo().bank_account_ids = [Command.link(account.id)]
            return record

        return {
            "almaz": employee(
                "Almaz Tadesse — አልማዝ ታደሰ",
                10000,
                "0012121212",
                "POESSA-001122",
                "1000200030001",
            ),
            "bekele": employee(
                "Bekele Worku — በቀለ ወርቁ",
                10000,
                "0013131313",
                "POESSA-003344",
                "1000200030002",
            ),
            # Missing POESSA ID → fix-before-filing banner on the schedule.
            "chaltu": employee(
                "Chaltu Deme — ጫልቱ ደሜ",
                1800,
                "0014141414",
                False,
                "1000200030003",
            ),
        }

    def _validate_pickings(self, pickings):
        """Set full quantities and validate (delivery/receipt)."""
        for picking in pickings:
            picking.action_assign()
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
                move.picked = True
            picking.button_validate()

    def _run_sales_flow(self, partners, products):
        """Two quotation → delivery → invoice flows with 15% VAT.

        Output VAT golden: 32,000 + 24,000 = 56,000 base → 8,400 VAT.
        """
        order_model = self.env["sale.order"]
        # Fasika: 10 × Teff @ 3,200 = 32,000 + 4,800 VAT = 36,800.
        order_fasika = order_model.create(
            {
                "partner_id": partners["fasika"].id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": products["teff"].id,
                            "product_uom_qty": 10,
                            "price_unit": 3200,
                        }
                    )
                ],
            }
        )
        # Zemen: consulting 15,000 + 2 × coffee @ 4,500 = 24,000 + 3,600 VAT.
        order_zemen = order_model.create(
            {
                "partner_id": partners["zemen"].id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": products["consulting"].id,
                            "product_uom_qty": 1,
                            "price_unit": 15000,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": products["coffee"].id,
                            "product_uom_qty": 2,
                            "price_unit": 4500,
                        }
                    ),
                ],
            }
        )
        for order in order_fasika | order_zemen:
            order.action_confirm()
            self._validate_pickings(order.picking_ids)
            invoices = order._create_invoices()
            invoices.write({"invoice_date": "2026-07-10"})
            invoices.action_post()

    def _run_purchase_flow(self, partners, products):
        """PO → receipt → vendor bill: 20 × Teff @ 2,600 = 52,000 from the
        compliant supplier → 3% WHT 1,560 + 7,800 input VAT."""
        order = self.env["purchase.order"].create(
            {
                "partner_id": partners["awash"].id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": products["teff"].id,
                            "product_qty": 20,
                            "price_unit": 2600,
                        }
                    )
                ],
            }
        )
        order.button_confirm()
        self._validate_pickings(order.picking_ids)
        order.action_create_invoice()
        bill = order.invoice_ids
        bill.write({"invoice_date": "2026-07-15"})
        bill.action_post()

    def _create_direct_bills(self, partners, products):
        """Two direct vendor bills: the punitive-WHT and foreign-digital paths.

        Habesha (no TIN), services 15,000 → 30% WHT 4,500 + 2,250 input VAT.
        CloudServe (foreign digital), 8,000 → 15% WHT 1,200 + 1,200 input VAT.
        """
        move_model = self.env["account.move"]
        for partner, price, date in (
            (partners["habesha"], 15000, "2026-07-18"),
            (partners["cloudserve"], 8000, "2026-07-20"),
        ):
            bill = move_model.create(
                {
                    "move_type": "in_invoice",
                    "partner_id": partner.id,
                    "invoice_date": date,
                    "company_id": self.env.company.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": products["consulting"].id,
                                "quantity": 1,
                                "price_unit": price,
                            }
                        )
                    ],
                }
            )
            bill.action_post()

    def _run_payroll(self, employees):
        """July payroll: both golden cases + below-threshold; posted + bank file."""
        run = self.env["l10n.et.payroll.run"].create(
            {
                "company_id": self.env.company.id,
                "date_from": PERIOD_FROM,
                "date_to": PERIOD_TO,
                "employee_ids": [Command.set([emp.id for emp in employees.values()])],
            }
        )
        run.action_generate_payslips()
        overtime_slip = run.payslip_ids.filtered(
            lambda slip: slip.employee_id == employees["bekele"]
        )
        self.env["l10n.et.payslip.input"].create(
            {
                "payslip_id": overtime_slip.id,
                "name": "Overtime July",
                "category": "earning",
                "taxable": True,
                "amount": 2000.0,
            }
        )
        run.action_confirm()
        run.action_export_bank_file()
        return run

    def _create_report_periods(self):
        """The July statutory report records, ready to print in the demo."""
        period = {
            "company_id": self.env.company.id,
            "date_from": PERIOD_FROM,
            "date_to": PERIOD_TO,
        }
        self.env["l10n.et.vat.declaration"].create(dict(period))
        self.env["l10n.et.wht.summary"].create(dict(period))
