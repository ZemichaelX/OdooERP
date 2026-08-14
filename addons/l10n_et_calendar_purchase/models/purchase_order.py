# -*- coding: utf-8 -*-
"""The purchase bridge: two mirror declarations, and nothing else.

Both sources here are **Datetime** fields, where the invoice bridge's are Dates.
That difference is handled inside `l10n.et.date.mixin` — it reads the source
field's own type and converts a Datetime through Ethiopian local time before
taking the day — precisely so that a bridge stays a declaration. Doing it here
would put a one-day error in a file that is supposed to contain no logic.
"""

from odoo import models

from odoo.addons.l10n_et_calendar.models.l10n_et_date_mixin import l10n_et_mirror_field


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "l10n.et.date.mixin"]

    _l10n_et_date_map = {
        "date_order": "l10n_et_date_order",
        "date_planned": "l10n_et_date_planned",
    }

    l10n_et_date_order = l10n_et_mirror_field("Order Deadline (ET)")
    l10n_et_date_planned = l10n_et_mirror_field("Expected Arrival (ET)")
