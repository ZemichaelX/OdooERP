# -*- coding: utf-8 -*-
"""Lot escalation states (fresh → nearing expiry → expired) and the daily
expiry digest. The state math lives in reference/pharma_calc.py."""

from odoo import api, fields, models
from odoo.exceptions import ValidationError
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
    pharma_alert_ids = fields.One2many(
        "pharma.expiry.alert",
        "lot_id",
        string="Expiry Digest Markers",
        help="Per-company record of which escalation states have already been "
        "reported for this batch (A2/A5).",
    )

    @api.constrains("expiration_date", "product_id")
    def _check_pharma_expiration_kept(self):
        """A pharma batch must always carry an expiration date: clearing it
        after receipt would slip the lot past the delivery gate and out of the
        digest (both key off a non-null expiry)."""
        for lot in self:
            if lot.is_pharma and not lot.expiration_date:
                raise ValidationError(
                    self.env._(
                        "Pharmaceutical batch %(lot)s must keep an expiration "
                        "date — it cannot be cleared.",
                        lot=lot.name or "?",
                    )
                )

    def write(self, vals):
        """Re-arm the expiry digest whenever a batch's expiry is changed: a lot
        already reported and then relabelled (corrected earlier, or extended to
        a later date) must be eligible to be reported again against the new
        date, so its digest markers are dropped (R3#6). State-driven re-alerting
        (nearing → expired) does NOT need this — it happens naturally because
        each state is a separate marker key (A2)."""
        result = super().write(vals)
        if "expiration_date" in vals and self.pharma_alert_ids:
            self.pharma_alert_ids.sudo().unlink()
        return result

    def _pharma_expiry_local_date(self):
        """The expiry as a LOCAL calendar date. ``expiration_date`` is a naive
        UTC datetime, so a batch entered as local-midnight 2026-09-25 is stored
        21:00 the day before at UTC+3; taking ``.date()`` raw would treat it as
        expiring a day early — wrong at Ethiopian time against the "last usable
        day" convention."""
        self.ensure_one()
        if not self.expiration_date:
            return None
        return fields.Datetime.context_timestamp(self, self.expiration_date).date()

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
                lot._pharma_expiry_local_date(),
                today,
                company.pharma_expiry_alert_days or pharma_calc.DEFAULT_ALERT_HORIZON_DAYS,
            )

    @api.model
    def _pharma_run_expiry_digest(self, today=None):
        """Daily cron: ONE digest activity per company listing every pharma lot
        with stock whose escalation state (nearing/expired) has not yet been
        reported FOR THAT COMPANY. The activity lands on the most urgent batch
        (earliest expiry), assigned to an inventory manager, and notifies by
        email per the user's notification settings.

        A batch is re-alerted when it transitions nearing → expired, because
        each state is a distinct per-company marker (A2/A5). ``today`` is
        injectable so a test can advance the clock without editing expiry dates
        (editing expiry re-arms via ``write`` and would mask the transition).
        """
        today = today or fields.Date.context_today(self)
        alert_model = self.env["pharma.expiry.alert"].sudo()
        quant_model = self.env["stock.quant"].sudo()
        for company in self.env["res.company"].search([("active", "=", True)]):
            horizon = company.pharma_expiry_alert_days or pharma_calc.DEFAULT_ALERT_HORIZON_DAYS
            # Lots created from receipts usually carry NO company (Odoo shares
            # them unless the product itself is company-specific), so match on
            # where the stock actually sits.
            candidates = self.sudo().search(
                [
                    ("company_id", "in", (False, company.id)),
                    ("product_id.is_pharma", "=", True),
                    ("expiration_date", "!=", False),
                ]
            )
            if not candidates:
                continue
            # On-hand quantity PER COMPANY. stock.lot.product_qty ignores the
            # company context (it sums quants wherever they physically sit), so a
            # shared lot would otherwise look in-stock in every company and get a
            # digest everywhere (A5). Scope to this company's own quants: a shared
            # lot alerts only where its stock actually is.
            qty_by_lot = {
                lot.id: total
                for lot, total in quant_model._read_group(
                    [
                        ("lot_id", "in", candidates.ids),
                        ("location_id.usage", "=", "internal"),
                        ("company_id", "=", company.id),
                    ],
                    groupby=["lot_id"],
                    aggregates=["quantity:sum"],
                )
            }
            # One query for this company's existing markers (no per-lot query).
            already = {
                (alert.lot_id.id, alert.pharma_state)
                for alert in alert_model.search(
                    [
                        ("company_id", "=", company.id),
                        ("lot_id", "in", candidates.ids),
                    ]
                )
            }
            pending = []  # (lot, state) not yet reported for this company
            for lot in candidates:
                if qty_by_lot.get(lot.id, 0.0) <= 0:
                    continue
                state = pharma_calc.expiry_state(
                    lot._pharma_expiry_local_date(), today, horizon
                )
                if state == pharma_calc.STATE_FRESH:
                    continue
                if (lot.id, state) in already:
                    continue
                pending.append((lot, state))
            if not pending:
                continue
            manager = next(
                (
                    user
                    for user in self.env.ref("stock.group_stock_manager").all_user_ids
                    if user.active and company in user.company_ids
                ),
                self.env.ref("base.user_admin"),
            )
            pending.sort(key=lambda item: item[0].expiration_date)
            state_labels = dict(self._fields["pharma_state"].selection)
            rows = "".join(
                "<li>%s — %s: expires %s (%s, %s on hand)</li>"
                % (
                    html_escape(lot.name),
                    html_escape(lot.product_id.display_name),
                    lot.expiration_date.date(),
                    state_labels.get(state),
                    qty_by_lot.get(lot.id, 0.0),
                )
                for lot, state in pending
            )
            # ONE activity per company, anchored on the most urgent batch.
            pending[0][0].activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=manager.id,
                summary=self.env._(
                    "Pharma expiry digest: %(count)s batch(es) entering the "
                    "%(days)s-day horizon",
                    count=len(pending),
                    days=horizon,
                ),
                note=self.env._(
                    "Batches nearing expiry or expired:%(rows)s",
                    rows=f"<ul>{rows}</ul>",
                ),
            )
            alert_model.create(
                [
                    {"lot_id": lot.id, "company_id": company.id, "pharma_state": state}
                    for lot, state in pending
                ]
            )
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
