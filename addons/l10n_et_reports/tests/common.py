# -*- coding: utf-8 -*-
"""Shared fixture: the Epic 3 demo document set rebuilt on a test company.

Hand-computed goldens (July 2026 period, all posted with default 15% VAT):
- 50,000 goods bill, compliant supplier → input VAT 7,500 + WHT 3% 1,500
- 15,000 services bill, no-TIN supplier → input VAT 2,250 + WHT 30% 4,500
- 8,000 foreign digital bill → input VAT 1,200 + WHT 15% 1,200
- 10,000 sale invoice → output VAT 1,500
Totals: output base 10,000 / tax 1,500; input base 73,000 / tax 10,950;
net VAT −9,450 (credit); WHT by rate {3%: 1,500, 30%: 4,500, 15%: 1,200},
grand total 7,200.
"""

from odoo import Command

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class L10nEtReportsCommon(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("et")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]

        cls.partner_compliant = cls.env["res.partner"].create(
            {
                "name": "Compliant Supplier PLC",
                "is_company": True,
                "l10n_et_tin": "0011223344",
                "l10n_et_business_licence_no": "AA/1234/2016",
            }
        )
        cls.partner_no_tin = cls.env["res.partner"].create(
            {"name": "No-TIN Supplier", "is_company": True}
        )
        cls.partner_foreign = cls.env["res.partner"].create(
            {
                "name": "Foreign Digital Provider",
                "is_company": True,
                "l10n_et_is_foreign_digital": True,
            }
        )
        cls.product_goods = cls.env["product.product"].create(
            {"name": "Goods", "type": "consu"}
        )
        cls.product_service = cls.env["product.product"].create(
            {"name": "Service", "type": "service"}
        )

        cls._post_move("in_invoice", cls.partner_compliant, cls.product_goods, 50000)
        cls._post_move("in_invoice", cls.partner_no_tin, cls.product_service, 15000)
        cls._post_move("in_invoice", cls.partner_foreign, cls.product_service, 8000)
        cls._post_move("out_invoice", cls.partner_compliant, cls.product_goods, 10000)

    @classmethod
    def _post_move(cls, move_type, partner, product, price, invoice_date="2026-07-05"):
        """Create + post a document with DEFAULT taxes (15% VAT auto-applies;
        the l10n_et_base WHT engine adds withholding on posting)."""
        move = cls.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": partner.id,
                "invoice_date": invoice_date,
                "company_id": cls.company.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "price_unit": price,
                        }
                    )
                ],
            }
        )
        move.action_post()
        return move

    def _make_report(self, model_name):
        """A July-2026 period report for the test company."""
        return self.env[model_name].create(
            {
                "company_id": self.company.id,
                "date_from": "2026-07-01",
                "date_to": "2026-07-31",
            }
        )
