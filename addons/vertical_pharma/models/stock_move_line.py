# -*- coding: utf-8 -*-
"""GS1 DataMatrix scan capture on receipt lines (scanner-first UX)."""

from datetime import datetime, time

from odoo import api, fields, models

from ..reference import pharma_calc


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    pharma_gs1_scan = fields.Char(
        string="GS1 Scan",
        help="Scan the pack's GS1 DataMatrix here: batch and expiry are filled "
        "in automatically (AIs 01 GTIN / 17 expiry / 10 batch / 21 serial). "
        "The field clears itself after a successful parse.",
    )

    @api.onchange("pharma_gs1_scan")
    def _onchange_pharma_gs1_scan(self):
        """Parse the scan into lot name + expiration date; reject mis-scans
        loudly (a wrong silent lot is a recall nightmare)."""
        if not self.pharma_gs1_scan:
            return None
        try:
            result = pharma_calc.parse_gs1_datamatrix(self.pharma_gs1_scan)
        except ValueError as error:
            self.pharma_gs1_scan = False
            return {
                "warning": {
                    "title": self.env._("Unreadable GS1 code"),
                    "message": self.env._(
                        "The scanned code could not be parsed: %(error)s",
                        error=error,
                    ),
                }
            }
        if result.batch:
            self.lot_name = result.batch
        if result.expiry:
            self.expiration_date = datetime.combine(result.expiry, time(12, 0))
        self.pharma_gs1_scan = False
        return None
