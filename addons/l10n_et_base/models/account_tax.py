# -*- coding: utf-8 -*-
"""Ethiopian metadata on taxes: WHT kind marker and the rate's legal source note."""

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_et_wht_kind = fields.Selection(
        selection=[
            ("goods", "Goods"),
            ("service", "Services"),
            ("foreign_digital", "Foreign Digital Services"),
            ("punitive", "Punitive (missing TIN/licence)"),
        ],
        string="Ethiopian WHT Kind",
        help="Marks this tax as an Ethiopian withholding tax handled by the automatic "
        "WHT engine on vendor bills. Leave empty on ordinary taxes.",
    )
    l10n_et_source_note = fields.Char(
        string="Rate Source",
        help="Legal source of this rate (proclamation/directive). Re-verify against "
        "the Ministry of Revenue before each go-live.",
    )
