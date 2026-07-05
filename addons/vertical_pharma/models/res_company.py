# -*- coding: utf-8 -*-
"""Per-company pharma compliance policy (configuration, not code)."""

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..reference import pharma_calc


class ResCompany(models.Model):
    _inherit = "res.company"

    pharma_expiry_alert_days = fields.Integer(
        string="Expiry Alert Horizon (days)",
        default=pharma_calc.DEFAULT_ALERT_HORIZON_DAYS,
        help="Batches enter the 'nearing expiry' state and the daily digest "
        "this many days before their expiration date (DAT proposal default: "
        "3 months = 90 days).",
    )
    pharma_expired_delivery_policy = fields.Selection(
        selection=[("warn", "Warn (log on the delivery)"), ("block", "Block")],
        string="Expired Lot Delivery Policy",
        default="block",
        required=True,
        help="What happens when a delivery contains an expired lot. 'Block' "
        "(default) refuses validation; 'Warn' validates but logs an audit "
        "message on the delivery.",
    )

    @api.constrains("pharma_expiry_alert_days")
    def _check_pharma_expiry_alert_days(self):
        """A non-positive horizon would silently disable alerting."""
        for company in self:
            if company.pharma_expiry_alert_days <= 0:
                raise ValidationError(self.env._("The expiry alert horizon must be positive."))
