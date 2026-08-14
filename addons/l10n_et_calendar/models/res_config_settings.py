# -*- coding: utf-8 -*-
"""The two company settings, surfaced in Settings.

`related` + `readonly=False` is Odoo's standard way to edit a company field
from the settings screen; nothing is stored on the transient model.
"""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_et_date_format = fields.Selection(
        related="company_id.l10n_et_date_format", readonly=False
    )
    l10n_et_report_calendar = fields.Selection(
        related="company_id.l10n_et_report_calendar", readonly=False
    )
