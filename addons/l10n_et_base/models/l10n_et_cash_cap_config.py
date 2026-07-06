# -*- coding: utf-8 -*-
"""Effective-dated configuration for the Proc 1395/2025 daily cash-payment cap."""

from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..reference import et_tax_calc

DEFAULT_SOURCE_NOTE = (
    "Cash payments to one party may not exceed ETB 50,000 — single transaction "
    "or same-day aggregate, whichever hits first (Art. 81, Proc 1395/2025; "
    "accountant-verified Jul 2026)."
)

# The pre-correction default (30,000, unverified) — recognized and fixed on
# upgrade so DBs seeded before the Jul 2026 accountant review pick up the
# verified figure WITHOUT touching caps a client deliberately customized.
_SUPERSEDED_SOURCE_NOTE = (
    "Cash payments to one party may not exceed ETB 30,000 per day "
    "(Proc 1395/2025). Re-verify with the Ministry of Revenue before go-live."
)


class L10nEtCashCapConfig(models.Model):
    _name = "l10n.et.cash.cap.config"
    _description = "Ethiopian Daily Cash-Payment Cap Configuration (effective-dated)"
    _order = "effective_from desc"

    name = fields.Char(compute="_compute_name", store=True)
    effective_from = fields.Date(
        required=True,
        help="First date (inclusive) on which this cap applies.",
    )
    effective_to = fields.Date(
        help="Last date (inclusive). Leave empty for open-ended.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        help="Configuration is per company; never leaks across companies.",
    )
    cap_amount = fields.Float(
        string="Daily Cap (ETB)",
        required=True,
        default=et_tax_calc.DEFAULT_CASH_CAP,
        help="Maximum total cash payable to one party in a single day. A daily "
        "total of exactly the cap is allowed; anything above is flagged.",
    )
    enforcement = fields.Selection(
        selection=[
            ("off", "Off"),
            ("warn", "Warn (log on the payment)"),
            ("block", "Block (refuse to post)"),
        ],
        required=True,
        default="warn",
        help="What happens when a cash payment pushes the daily total to a party "
        "over the cap. 'Warn' posts an audit message on the payment; 'Block' "
        "prevents posting entirely.",
    )
    source_note = fields.Char(
        required=True,
        default=DEFAULT_SOURCE_NOTE,
        help="Legal source of the cap. Re-verify before each go-live.",
    )

    @api.depends("cap_amount", "effective_from", "enforcement")
    def _compute_name(self):
        """Human-readable label, e.g. 'Cash cap 30,000 (warn) from 2025-07-01'."""
        for config in self:
            config.name = self.env._(
                "Cash cap %(cap)s (%(mode)s) from %(date_from)s",
                cap=f"{config.cap_amount:,.0f}",
                mode=config.enforcement or "?",
                date_from=config.effective_from or "?",
            )

    @api.constrains("effective_from", "effective_to", "company_id")
    def _check_no_overlap(self):
        """The applicable cap must be unambiguous on any payment date."""
        for config in self:
            domain = [
                ("id", "!=", config.id),
                ("company_id", "=", config.company_id.id),
                ("effective_from", "<=", config.effective_to or date.max),
                "|",
                ("effective_to", "=", False),
                ("effective_to", ">=", config.effective_from),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    self.env._(
                        "Cash-cap configurations must not overlap in time "
                        "for the same company."
                    )
                )

    @api.constrains("cap_amount")
    def _check_cap_amount(self):
        """A zero/negative cap would flag every cash payment — almost certainly a
        configuration error."""
        for config in self:
            if config.cap_amount <= 0:
                raise ValidationError(self.env._("The daily cash cap must be positive."))

    @api.model
    def _get_config(self, company, on_date=None):
        """Return the cap configuration effective for ``company`` on ``on_date``.

        Empty recordset when none applies (check disabled).
        """
        on_date = on_date or fields.Date.context_today(self)
        return self.search(
            [
                ("company_id", "=", company.id),
                ("effective_from", "<=", on_date),
                "|",
                ("effective_to", "=", False),
                ("effective_to", ">=", on_date),
            ],
            order="effective_from desc",
            limit=1,
        )

    @api.model
    def _l10n_et_ensure_default(self, company):
        """Seed the Art. 81 (Proc 1395/2025) default cap for ``company`` if it
        has none."""
        if not self.search_count([("company_id", "=", company.id)]):
            self.create(
                {
                    "company_id": company.id,
                    "effective_from": date(2025, 7, 1),
                    "source_note": DEFAULT_SOURCE_NOTE,
                }
            )

    @api.model
    def _l10n_et_fix_superseded_defaults(self):
        """Upgrade hook: correct configs still carrying the pre-review 30,000
        default to the accountant-verified 50,000 (Art. 81, Proc 1395/2025).

        Only rows with BOTH the old cap and the old source note are touched —
        a deliberately customized cap (different amount or an edited note) is
        client configuration and stays untouched."""
        stale = self.search(
            [
                ("cap_amount", "=", 30000.0),
                ("source_note", "=", _SUPERSEDED_SOURCE_NOTE),
            ]
        )
        if stale:
            stale.write(
                {
                    "cap_amount": et_tax_calc.DEFAULT_CASH_CAP,
                    "source_note": DEFAULT_SOURCE_NOTE,
                }
            )
        return True
