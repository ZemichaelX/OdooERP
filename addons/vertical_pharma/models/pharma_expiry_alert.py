# -*- coding: utf-8 -*-
"""Per-company expiry-digest markers.

A2/A5: the old single ``pharma_alerted`` boolean on the lot meant a batch was
digested exactly ONCE, ever — so a batch flagged while merely *nearing* expiry
was never re-surfaced when it actually *expired*, and a lot shared across
companies (receipt-created lots carry no ``company_id``) was de-duplicated
across all of them by one shared flag.

Each marker records that a given (lot, company, escalation state) has already
appeared in a digest. The digest re-alerts when the state changes
(nearing → expired) because that is a different key, and it is per company, so
a shared lot alerts independently in each company that stocks it.
"""

from odoo import fields, models


class PharmaExpiryAlert(models.Model):
    _name = "pharma.expiry.alert"
    _description = "Pharma Expiry Digest Marker"
    _order = "alert_date desc, id desc"

    lot_id = fields.Many2one(
        "stock.lot",
        required=True,
        ondelete="cascade",
        index=True,
        help="The batch that was reported in a digest.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        help="The company the digest reported this batch for (markers are "
        "per company: a shared lot alerts independently per company).",
    )
    pharma_state = fields.Selection(
        selection=[
            ("nearing_expiry", "Nearing Expiry"),
            ("expired", "Expired"),
        ],
        required=True,
        help="The escalation state that was reported. A later transition to a "
        "new state (nearing → expired) has a different key and re-alerts.",
    )
    alert_date = fields.Date(default=fields.Date.context_today)

    _lot_company_state_uniq = models.Constraint(
        "unique(lot_id, company_id, pharma_state)",
        "A batch is reported once per state per company.",
    )
