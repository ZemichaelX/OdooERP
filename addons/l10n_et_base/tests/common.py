# -*- coding: utf-8 -*-
"""Shared fixtures for the l10n_et_base integration tests: an ET-chart company,
three partners (compliant / no TIN / foreign digital) and goods/service products."""

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class L10nEtBaseCommon(AccountTestInvoicingCommon):
    """Company on the Ethiopian chart template with the compliance fixtures."""

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
                "l10n_et_business_licence_expiry": "2035-12-31",
            }
        )
        cls.partner_no_tin = cls.env["res.partner"].create(
            {
                "name": "No-TIN Supplier",
                "is_company": True,
            }
        )
        cls.partner_foreign_digital = cls.env["res.partner"].create(
            {
                "name": "Foreign Digital Provider",
                "is_company": True,
                "l10n_et_is_foreign_digital": True,
            }
        )
        cls.product_goods = cls.env["product.product"].create(
            {
                "name": "Test Goods",
                "type": "consu",
            }
        )
        cls.product_service = cls.env["product.product"].create(
            {
                "name": "Test Service",
                "type": "service",
            }
        )

    @classmethod
    def _create_bill(cls, partner, lines, invoice_date="2026-07-01", post=True, with_vat=False):
        """Create (and post) a vendor bill.

        ``lines`` is a list of (product, price_unit). Taxes are cleared by
        default so WHT amounts can be asserted in isolation; ``with_vat`` keeps
        the default taxes instead.
        """
        line_vals = []
        for product, price_unit in lines:
            vals = {
                "product_id": product.id,
                "quantity": 1,
                "price_unit": price_unit,
            }
            if not with_vat:
                vals["tax_ids"] = []
            line_vals.append((0, 0, vals))
        move = cls.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "invoice_date": invoice_date,
                "company_id": cls.company.id,
                "invoice_line_ids": line_vals,
            }
        )
        if post:
            move.action_post()
        return move

    @staticmethod
    def _wht_lines(move):
        """The move's WHT tax lines (tax lines whose tax carries a WHT kind)."""
        return move.line_ids.filtered(lambda line: line.tax_line_id.l10n_et_wht_kind)
