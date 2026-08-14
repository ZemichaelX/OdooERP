# -*- coding: utf-8 -*-
"""The invoice bridge: two mirror declarations, and nothing else.

There is deliberately no logic in this file. Everything a mirrored date needs —
the compute, the storage, the index, the read-only behaviour, and the
Date-versus-Datetime handling — lives in `l10n.et.date.mixin`. If this bridge
ever seems to need a method, that is a signal the mixin is missing something,
not an invitation to write it here: a rule implemented twice in two bridges is a
rule that will diverge.
"""

from odoo import models

from odoo.addons.l10n_et_calendar.models.l10n_et_date_mixin import l10n_et_mirror_field


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.et.date.mixin"]

    _l10n_et_date_map = {
        "invoice_date": "l10n_et_invoice_date",
        "invoice_date_due": "l10n_et_invoice_date_due",
    }

    l10n_et_invoice_date = l10n_et_mirror_field("Invoice Date (ET)")
    l10n_et_invoice_date_due = l10n_et_mirror_field("Due Date (ET)")
