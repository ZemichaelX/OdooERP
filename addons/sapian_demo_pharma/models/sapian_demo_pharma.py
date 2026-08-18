# -*- coding: utf-8 -*-
"""Provisioning of the 'Tena Pharma Import PLC' demo tenant.

A small Ethiopian pharma importer with everything the vertical_pharma pitch
needs on screen, created through the REAL warehouse flows (receipt →
delivery) so nothing is staged:

- six medicines (Amharic + English names) with realistic 730-day shelf lives,
  so a live receive during the pitch auto-fills a sane expiry — never an
  instantly-expired lot
- batches at all three expiry stages: fresh Amoxicillin/Paracetamol/
  Metformin/Amlodipine stock, Coartem CO-88 nearing expiry (+45 days) and
  ORS OR-15 already expired (−10 days)
- the daily expiry digest already fired: ONE activity listing CO-88 and
  OR-15, anchored on the most urgent batch — show the alert, don't describe it
- one import dossier IMP/... from Global Pharma GmbH with landed costs
  (goldens: 1,850,000 + 210,000 + 396,500 + 55,000 = 2,511,500 ETB) linked to
  the main receipt, so every fresh batch traces to its import file
- the recall golden: B-123 delivered to Hiwot Pharmacy (120, ~today−20) and
  Kadisco Pharmacy (80, ~today−12) — exhausting the batch so Bethel Clinic's
  order (60, ~today−8) FEFO-reserves B-124 instead. The B-123 recall report
  lists exactly two customers with phone + city; Bethel proves precision by
  exclusion.

Expiry-sensitive dates are relative to the provisioning day so the demo
states hold whenever the tenant is (re)built.
"""

from datetime import datetime, time, timedelta

from odoo import Command, api, fields, models

DEMO_COMPANY_NAME = "Tena Pharma Import PLC"


class SapianDemoPharma(models.AbstractModel):
    _name = "sapian.demo.pharma"
    _description = "SapianERP Demo Pharma Provisioning"

    @api.model
    def _provision_demo_pharma(self, company_name=DEMO_COMPANY_NAME):
        """Provision the pharma demo tenant (idempotent by company name).

        Returns the demo company. Called from demo data at install and reused
        verbatim by the golden tests (with a different name, inside the test
        transaction).
        """
        existing = self.env["res.company"].search([("name", "=", company_name)], limit=1)
        if existing:
            return existing
        company = self._create_company(company_name)
        env = self.env(context=dict(self.env.context, allowed_company_ids=company.ids))
        demo = env["sapian.demo.pharma"].with_company(company)
        warehouse = demo._ensure_warehouse(company)
        medicines = demo._create_medicines(company)
        partners = demo._create_partners()
        demo._receive_import_file(warehouse, medicines, partners)
        demo._receive_ageing_stock(warehouse, medicines, partners)
        demo._run_recall_history(warehouse, medicines, partners)
        # Fire the digest NOW so the pitch shows the alert itself: one activity
        # listing the nearing (CO-88) and expired (OR-15) batches.
        env["stock.lot"]._pharma_run_expiry_digest()
        return company

    @api.model
    def _create_company(self, company_name):
        """The importer company (ETB, Addis Ababa), visible to the admin."""
        currency = self.env.ref("base.ETB")
        if not currency.active:
            # sudo: activating a currency is a system-level demo setup step.
            currency.sudo().active = True
        company = self.env["res.company"].create(
            {
                "name": company_name,
                "currency_id": currency.id,
                "country_id": self.env.ref("base.et").id,
                "city": "Addis Ababa",
                "street": "Haile Gebrselassie Avenue",
                "phone": "+251 11 555 0100",
                # This pitch tenant demonstrates stock/expiry/recall discipline
                # and is provisioned WITHOUT a chart of accounts, so the WHT
                # engine has no Ethiopian taxes to resolve and would raise on
                # the first vendor bill someone posts during a demo. Turning the
                # engine off is a statement about the missing fiscal setup, not
                # about Tena's tax obligations. Proper fix (deferred, see
                # CHANGELOG): give Tena the 'et' chart so the landed-cost
                # dossier has books to land in.
                "l10n_et_tax_engine_active": False,
            }
        )
        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        if admin:
            # Allowed, not default: the trader tenant stays the landing company.
            admin.sudo().write({"company_ids": [Command.link(company.id)]})
        return company

    @api.model
    def _ensure_warehouse(self, company):
        """stock only auto-creates warehouses for new companies in TEST mode
        (stock/models/res_company.py); at demo-load time create it ourselves."""
        warehouse_model = self.env["stock.warehouse"].sudo()
        warehouse = warehouse_model.search([("company_id", "=", company.id)], limit=1)
        return warehouse or warehouse_model.create({"company_id": company.id})

    def _create_medicines(self, company):
        """Six pharma-flagged medicines. 730-day shelf life: a live receive in
        a pitch auto-fills expiry two years out, never an expired lot."""
        product_model = self.env["product.product"]
        catalogue = {
            "amoxicillin": ("Amoxicillin 500mg Capsules — አሞክሲሲሊን", 12.50, 8.00),
            "paracetamol": ("Paracetamol 500mg Tablets — ፓራሲታሞል", 3.20, 1.90),
            "coartem": ("Coartem 20/120mg Tablets — ኮአርቴም", 95.00, 68.00),
            "ors": ("ORS Sachets 27.9g — ኦ.አር.ኤስ", 9.00, 5.50),
            "metformin": ("Metformin 500mg Tablets — ሜትፎርሚን", 6.75, 4.20),
            "amlodipine": ("Amlodipine 5mg Tablets — አምሎዲፒን", 8.40, 5.10),
        }
        return {
            key: product_model.create(
                {
                    "name": name,
                    "type": "consu",
                    "is_storable": True,
                    "is_pharma": True,
                    "expiration_time": 730,
                    "list_price": price,
                    "standard_price": cost,
                    "company_id": company.id,
                }
            )
            for key, (name, price, cost) in catalogue.items()
        }

    def _create_partners(self):
        """The foreign supplier + three customers with the contact details the
        recall report exists to print (phone, city)."""
        partner_model = self.env["res.partner"]
        ethiopia = self.env.ref("base.et")
        return {
            "global_pharma": partner_model.create(
                {
                    "name": "Global Pharma GmbH",
                    "is_company": True,
                    "country_id": self.env.ref("base.de").id,
                    "city": "Hamburg",
                    "phone": "+49 40 555 0199",
                }
            ),
            "hiwot": partner_model.create(
                {
                    "name": "Hiwot Pharmacy — ሕይወት ፋርማሲ",
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": "Addis Ababa",
                    "phone": "+251 11 123 4567",
                }
            ),
            "kadisco": partner_model.create(
                {
                    "name": "Kadisco Pharmacy — ካዲስኮ ፋርማሲ",
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": "Adama",
                    "phone": "+251 22 555 8899",
                }
            ),
            "bethel": partner_model.create(
                {
                    "name": "Bethel Clinic — ቤቴል ክሊኒክ",
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": "Hawassa",
                    "phone": "+251 46 220 7711",
                }
            ),
        }

    def _expiry(self, days_from_today):
        """Expiry datetime ``days_from_today`` out (noon, wall-clock safe)."""
        today = fields.Date.context_today(self)
        return datetime.combine(today + timedelta(days=days_from_today), time(12, 0))

    def _receive(self, warehouse, partner, batches, days_ago, dossier=None):
        """One receipt for ``batches`` = [(product, lot_name, qty, expiry_days)],
        back-dated ``days_ago``; optionally tied to an import dossier.

        One move per PRODUCT (Odoo merges same-product moves on confirm
        anyway), with one move line per batch of that product."""
        suppliers = self.env.ref("stock.stock_location_suppliers")
        demand = {}
        for product, _lot, qty, _days in batches:
            demand[product] = demand.get(product, 0) + qty
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.in_type_id.id,
                "partner_id": partner.id,
                "location_id": suppliers.id,
                "location_dest_id": warehouse.lot_stock_id.id,
                "pharma_dossier_id": dossier.id if dossier else False,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "location_id": suppliers.id,
                            "location_dest_id": warehouse.lot_stock_id.id,
                        }
                    )
                    for product, qty in demand.items()
                ],
            }
        )
        picking.action_confirm()
        picking.move_ids.move_line_ids.unlink()
        for move in picking.move_ids:
            for product, lot_name, qty, expiry_days in batches:
                if product != move.product_id:
                    continue
                self.env["stock.move.line"].create(
                    {
                        "move_id": move.id,
                        "picking_id": picking.id,
                        "product_id": product.id,
                        "quantity": qty,
                        "lot_name": lot_name,
                        "expiration_date": self._expiry(expiry_days),
                        "location_id": suppliers.id,
                        "location_dest_id": warehouse.lot_stock_id.id,
                    }
                )
            move.picked = True
        # skip_expired: confirm product_expiry's popup for already-expired
        # batches (the ageing-stock receipt).
        picking.with_context(skip_expired=True).button_validate()
        self._backdate(picking, days_ago)
        return picking

    def _deliver(self, warehouse, partner, product, qty, days_ago):
        """A FEFO-reserved, validated delivery, back-dated ``days_ago``."""
        customers = self.env.ref("stock.stock_location_customers")
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.out_type_id.id,
                "partner_id": partner.id,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": customers.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "location_id": warehouse.lot_stock_id.id,
                            "location_dest_id": customers.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.picked = True
        picking.button_validate()
        self._backdate(picking, days_ago)
        return picking

    def _backdate(self, picking, days_ago):
        """Give the done picking a realistic historical date."""
        moment = self._expiry(-days_ago)
        picking.write({"date_done": moment})
        picking.move_line_ids.write({"date": moment})

    def _receive_import_file(self, warehouse, medicines, partners):
        """The dossier-linked receipt: every fresh batch traces to IMP/...

        Landed-cost golden: 1,850,000 + 210,000 + 396,500 + 55,000 = 2,511,500.
        """
        dossier = self.env["pharma.import.dossier"].create(
            {
                "supplier_id": partners["global_pharma"].id,
                "eta_date": fields.Date.context_today(self) - timedelta(days=32),
                "status": "received",
                "amount_goods": 1850000,
                "amount_freight": 210000,
                "amount_customs": 396500,
                "amount_clearance": 55000,
                "note": "Cleared at Modjo dry port. BL, packing list and EFDA "
                "import permit attached in the chatter.",
            }
        )
        self._receive(
            warehouse,
            partners["global_pharma"],
            [
                (medicines["amoxicillin"], "B-123", 200, 400),
                (medicines["amoxicillin"], "B-124", 150, 550),
                (medicines["paracetamol"], "PC-501", 400, 600),
                (medicines["metformin"], "MF-77", 300, 650),
                (medicines["amlodipine"], "AM-12", 250, 700),
            ],
            days_ago=30,
            dossier=dossier,
        )
        return dossier

    def _receive_ageing_stock(self, warehouse, medicines, partners):
        """Older stock at the two alert stages: Coartem CO-88 nearing expiry
        (+45 days inside the 90-day horizon), ORS OR-15 expired (−10 days)."""
        return self._receive(
            warehouse,
            partners["global_pharma"],
            [
                (medicines["coartem"], "CO-88", 120, 45),
                (medicines["ors"], "OR-15", 80, -10),
            ],
            days_ago=200,
        )

    def _run_recall_history(self, warehouse, medicines, partners):
        """The recall golden: Hiwot 120 + Kadisco 80 exhaust B-123 (200), so
        Bethel's 60 FEFO-reserves B-124 — recall precision by exclusion."""
        amoxicillin = medicines["amoxicillin"]
        self._deliver(warehouse, partners["hiwot"], amoxicillin, 120, days_ago=20)
        self._deliver(warehouse, partners["kadisco"], amoxicillin, 80, days_ago=12)
        self._deliver(warehouse, partners["bethel"], amoxicillin, 60, days_ago=8)
