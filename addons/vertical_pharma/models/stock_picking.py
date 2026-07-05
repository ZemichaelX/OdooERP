# -*- coding: utf-8 -*-
"""Batch discipline at the document gates: expiry mandatory on pharma
receipts, expired lots blocked (or warned) on deliveries."""

from odoo import fields, models
from odoo.exceptions import UserError

from ..reference import pharma_calc


class StockPicking(models.Model):
    _inherit = "stock.picking"

    pharma_dossier_id = fields.Many2one(
        "pharma.import.dossier",
        string="Import Dossier",
        check_company=True,
        index="btree_not_null",
        help="The import file this receipt belongs to (pharma imports).",
    )

    def button_validate(self):
        """Enforce the pharma gates before core validation."""
        self._pharma_check_receipt_expiry()
        self._pharma_check_expired_delivery()
        return super().button_validate()

    def _pharma_check_receipt_expiry(self):
        """Incoming pharma stock without an expiration date must not enter the
        warehouse (core stock already enforces the lot itself)."""
        for picking in self:
            if picking.picking_type_code != "incoming":
                continue
            # Union with the moves' lines: goods move even on a line that was
            # never linked back to the picking, so the gate must see it too.
            offending = (picking.move_line_ids | picking.move_ids.move_line_ids).filtered(
                lambda line: line.product_id.is_pharma
                and line.quantity
                and not line.expiration_date
            )
            if offending:
                raise UserError(
                    self.env._(
                        "Pharmaceutical receipts need an expiration date on "
                        "every batch. Missing on: %(products)s",
                        products=", ".join(offending.mapped("product_id.display_name")),
                    )
                )

    def _pharma_check_expired_delivery(self):
        """Expired lots must never reach a customer silently: block by default,
        warn (audit message) if the company opted for it."""
        today = fields.Date.context_today(self)
        for picking in self:
            if picking.picking_type_code != "outgoing":
                continue
            expired = (picking.move_line_ids | picking.move_ids.move_line_ids).filtered(
                lambda line: line.product_id.is_pharma
                and line.lot_id
                and line.lot_id.expiration_date
                and pharma_calc.expiry_state(
                    line.lot_id.expiration_date.date(),
                    today,
                    picking.company_id.pharma_expiry_alert_days
                    or pharma_calc.DEFAULT_ALERT_HORIZON_DAYS,
                )
                == pharma_calc.STATE_EXPIRED
            )
            if not expired:
                continue
            details = ", ".join(
                f"{line.lot_id.name} ({line.product_id.display_name}, "
                f"expired {line.lot_id.expiration_date.date()})"
                for line in expired
            )
            if picking.company_id.pharma_expired_delivery_policy == "block":
                raise UserError(
                    self.env._(
                        "Delivery blocked — expired batches: %(details)s. "
                        "Remove or replace them (company policy: block).",
                        details=details,
                    )
                )
            picking.message_post(
                body=self.env._(
                    "WARNING: this delivery ships EXPIRED batches: %(details)s "
                    "(company policy: warn).",
                    details=details,
                )
            )
