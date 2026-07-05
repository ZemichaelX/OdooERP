# -*- coding: utf-8 -*-
"""Lot escalation states (fresh → nearing expiry → expired) and the daily
expiry digest. The state math lives in reference/pharma_calc.py."""

from odoo import api, fields, models
from odoo.tools import html_escape

from ..reference import pharma_calc


class StockLot(models.Model):
    _inherit = "stock.lot"

    is_pharma = fields.Boolean(related="product_id.is_pharma")
    pharma_state = fields.Selection(
        selection=[
            (pharma_calc.STATE_FRESH, "Fresh"),
            (pharma_calc.STATE_NEARING, "Nearing Expiry"),
            (pharma_calc.STATE_EXPIRED, "Expired"),
        ],
        string="Expiry Status",
        compute="_compute_pharma_state",
        help="Escalation state against the company's alert horizon. Not stored: "
        "it depends on today's date.",
    )
    pharma_alerted = fields.Boolean(
        string="In Expiry Digest",
        default=False,
        copy=False,
        help="Set once the lot has appeared in a daily expiry digest so it is "
        "never reported twice.",
    )

    @api.depends("expiration_date", "product_id.is_pharma", "company_id")
    def _compute_pharma_state(self):
        """Delegate to the reference calculator with the company horizon."""
        today = fields.Date.context_today(self)
        for lot in self:
            if not lot.is_pharma:
                lot.pharma_state = False
                continue
            company = lot.company_id or self.env.company
            lot.pharma_state = pharma_calc.expiry_state(
                lot.expiration_date and lot.expiration_date.date(),
                today,
                company.pharma_expiry_alert_days or pharma_calc.DEFAULT_ALERT_HORIZON_DAYS,
            )

    @api.model
    def _pharma_run_expiry_digest(self):
        """Daily cron: ONE digest activity per company listing every pharma lot
        with stock that entered the alert horizon (or expired) and has not been
        reported yet. The activity lands on the most urgent batch (earliest
        expiry), assigned to an inventory manager, and notifies by email per
        the user's notification settings."""
        today = fields.Date.context_today(self)
        for company in self.env["res.company"].search([("active", "=", True)]):
            horizon = company.pharma_expiry_alert_days or pharma_calc.DEFAULT_ALERT_HORIZON_DAYS
            # Lots created from receipts usually carry NO company (Odoo shares
            # them unless the product itself is company-specific), so match on
            # where the stock actually sits: qty is evaluated in this company.
            candidates = self.sudo().search(
                [
                    ("company_id", "in", (False, company.id)),
                    ("product_id.is_pharma", "=", True),
                    ("pharma_alerted", "=", False),
                    ("expiration_date", "!=", False),
                ]
            )
            lots = candidates.filtered(
                lambda lot: lot.with_company(company).product_qty > 0
                and pharma_calc.expiry_state(lot.expiration_date.date(), today, horizon)
                != pharma_calc.STATE_FRESH
            )
            if not lots:
                continue
            manager = next(
                (
                    user
                    for user in self.env.ref("stock.group_stock_manager").all_user_ids
                    if user.active and company in user.company_ids
                ),
                self.env.ref("base.user_admin"),
            )
            lots = lots.sorted(key=lambda l10t: l10t.expiration_date)
            rows = "".join(
                "<li>%s — %s: expires %s (%s, %s on hand)</li>"
                % (
                    html_escape(lot.name),
                    html_escape(lot.product_id.display_name),
                    lot.expiration_date.date(),
                    dict(lot._fields["pharma_state"].selection).get(lot.pharma_state),
                    lot.with_company(company).product_qty,
                )
                for lot in lots
            )
            # ONE activity per company, anchored on the most urgent batch.
            lots[0].activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=manager.id,
                summary=self.env._(
                    "Pharma expiry digest: %(count)s batch(es) entering the "
                    "%(days)s-day horizon",
                    count=len(lots),
                    days=horizon,
                ),
                note=self.env._(
                    "Batches nearing expiry or expired:%(rows)s",
                    rows=f"<ul>{rows}</ul>",
                ),
            )
            lots.write({"pharma_alerted": True})
        return True

    def _pharma_recall_lines(self):
        """Every done outgoing move line that shipped this batch — the data
        behind the recall report: who received it, when, how much."""
        self.ensure_one()
        return self.env["stock.move.line"].search(
            [
                ("lot_id", "=", self.id),
                ("state", "=", "done"),
                ("picking_code", "=", "outgoing"),
            ],
            order="date asc",
        )

    def _pharma_dossiers(self):
        """The import dossier(s) this batch came in under (via its receipts)."""
        self.ensure_one()
        lines = self.env["stock.move.line"].search(
            [
                ("lot_id", "=", self.id),
                ("state", "=", "done"),
                ("picking_code", "=", "incoming"),
            ]
        )
        return lines.picking_id.pharma_dossier_id
