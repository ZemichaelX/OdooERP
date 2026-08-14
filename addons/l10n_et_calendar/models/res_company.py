# -*- coding: utf-8 -*-
"""The two company settings the brief asks for, and nothing else.

Both are per-company because a group can hold an Ethiopian trading company and
an export arm that invoices in Gregorian, and CLAUDE.md rule 3 says company
settings are per company rather than global.
"""

from odoo import api, fields, models

from ..reference import et_calendar as cal


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_et_date_format = fields.Selection(
        selection=[
            ("latin", "Latin — Hamle 1, 2017"),
            ("amharic", "Amharic — ሐምሌ 1 ቀን 2017 ዓ.ም."),
            ("numeric", "Numeric — 01/11/2017"),
        ],
        string="Ethiopian Date Display",
        default="latin",
        required=True,
        help=(
            "How Ethiopian dates are written on screen and on documents. This "
            "is a display choice only: the stored value is always the "
            "canonical year-month-day form, so changing this setting rewrites "
            "nothing."
        ),
    )
    l10n_et_report_calendar = fields.Selection(
        selection=[
            ("gregorian", "Gregorian only"),
            ("ethiopian", "Ethiopian only"),
            ("both", "Both, Ethiopian beside Gregorian"),
        ],
        string="Calendar on Documents",
        default="both",
        required=True,
        help=(
            "Which calendar prints on invoices and purchase orders. 'Both' is "
            "the default because a document that a supplier, a customer and "
            "the Ministry of Revenue all read is safest carrying both."
        ),
    )

    @api.model
    def _l10n_et_month_selection(self, amharic=False):
        """The 13 months, for any UI that needs to offer them.

        Wrapped for translation here — the reference library ships the names as
        data in two scripts and no English, precisely so this layer owns the
        translation. See `_l10n_et_format` for why a lookup rather than a
        literal is the right trade here, and what it costs.
        """
        names = cal.MONTHS_AMHARIC if amharic else cal.MONTHS_LATIN
        return [(str(index + 1), self.env._(name)) for index, name in enumerate(names)]
