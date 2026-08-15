# -*- coding: utf-8 -*-
"""Effective-dated Ethiopian social welfare levy configuration.

Council of Ministers Regulation No. 519/2022, "Social Welfare Levy on Imported
Goods": 3% of the aggregate CIF value of imported goods, effective 6 August
2022 (gazetted 22 August 2022).

The rate and the commencement date are CONFIGURATION DATA (CLAUDE.md rule 4).
A future rate change is a NEW record with a new ``effective_from`` — it must
never rewrite imports cleared under the old rate. The arithmetic lives in the
pure-Python reference calculator (reference/et_tax_calc.py); this model stores
and serves the parameters, exactly as l10n.et.wht.config does.

WHAT THIS MODEL WILL NOT LET YOU DO
-----------------------------------
The levy is a COST, not a recoverable receivable, and that is enforced here
rather than documented here: ``_check_tax_posts_to_a_cost_account`` refuses a
configuration whose tax posts to a receivable or any other asset account.

A competitor's published tax guide describes this as an "Import Advance Income
Tax, 3% of CIF, offset against income tax". No authority for such a tax was
found — it is absent from PwC's Ethiopian import-tax page and from the Art. 92
withholding categories. Wiring it that way would capitalise 3% of every
consignment an importer brings in as an asset that will never be recovered.
The constraint exists so that reading cannot be introduced by editing a
configuration record.

THE COMMENCEMENT DATE IS NOT AN ETHIOPIAN MONTH BOUNDARY
--------------------------------------------------------
6 August 2022 is **Hamle 30, 2014 EC** — the last day of the month, one day
before Nehase 1 (7 August 2022). Every Ethiopian effective date this project
has verified against a proclamation lands on day 1. Unlike the two seeds that
are already flagged, this one is not obviously a transcription error: the
regulation states 6 August 2022 and was gazetted on 22 August, and a regulation
may lawfully commence mid-month. It is enumerated in
tests_fast/test_et_statutory_dates_land_on_month_1.py and left FAILING (xfail,
strict) so the question stays visible and dated. It is deliberately NOT
"corrected" here.
"""

from datetime import date

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..reference import et_tax_calc

#: Template xml id of the levy tax shipped by this module.
TEMPLATE_TAX_XMLID = "l10n_et_base_tax_swl_import_3"

DEFAULT_SOURCE_NOTE = (
    "Social welfare levy 3% of the aggregate CIF value of imported goods. "
    "Council of Ministers Regulation No. 519/2022, effective 6 August 2022, "
    "gazetted 22 August 2022. IN ADDITION to customs duty, excise, VAT and "
    "surtax; NOT creditable against income tax (it is a cost); does NOT form "
    "part of the base for computing any other import tax. No threshold. "
    "Exempt: diplomatic privilege; goods already subject to import surtax "
    "under Regulation 133/2007; goods excluded by Ministry of Finance "
    "directive. Re-verify against the Negarit Gazeta before go-live."
)

#: Account types a levy tax must never post to. The levy is an expense of
#: importing; anything in this set would present it as recoverable.
FORBIDDEN_TAX_ACCOUNT_TYPES = {
    "asset_receivable",
    "asset_current",
    "asset_non_current",
    "asset_prepayments",
    "asset_fixed",
    "asset_cash",
}


class L10nEtSocialWelfareLevyConfig(models.Model):
    _name = "l10n.et.social.welfare.levy.config"
    _description = "Ethiopian Social Welfare Levy Configuration (effective-dated)"
    _order = "effective_from desc"

    name = fields.Char(compute="_compute_name", store=True)
    effective_from = fields.Date(
        required=True,
        help="First date (inclusive) on which this configuration applies. "
        "Regulation 519/2022 commences on 6 August 2022.",
    )
    effective_to = fields.Date(
        help="Last date (inclusive) on which this configuration applies. "
        "Leave empty for open-ended.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        help="Configuration is per company; never leaks across companies.",
    )
    rate = fields.Float(
        string="Levy Rate (fraction)",
        required=True,
        default=et_tax_calc.DEFAULT_SWL_RATE,
        help="Levy rate as a fraction of CIF, e.g. 0.03 for 3%.",
    )
    source_note = fields.Char(
        required=True,
        default=DEFAULT_SOURCE_NOTE,
        help="Legal source of these figures. Displayed so every go-live "
        "re-verifies against gazetted text.",
    )
    tax_id = fields.Many2one(
        "account.tax",
        string="Social Welfare Levy Tax",
        check_company=True,
        domain=[("type_tax_use", "=", "purchase")],
        help="Tax record used for the levy. Empty = the tax shipped by this "
        "module's chart template.",
    )

    @api.depends("rate", "effective_from", "effective_to")
    def _compute_name(self):
        for config in self:
            config.name = self.env._(
                "Social Welfare Levy %(rate).0f%% from %(date_from)s%(date_to)s",
                rate=config.rate * 100,
                date_from=config.effective_from or "?",
                date_to=config.effective_to and self.env._(" to %s", config.effective_to) or "",
            )

    @api.constrains("effective_from", "effective_to", "company_id")
    def _check_no_overlap(self):
        """The applicable configuration must be unambiguous for any import date."""
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
                        "Social welfare levy configurations must not overlap in "
                        "time for the same company."
                    )
                )

    @api.constrains("rate")
    def _check_rate(self):
        for config in self:
            if not 0 <= config.rate <= 1:
                raise ValidationError(
                    self.env._("The levy rate is a fraction: use 0.03 for 3%, not 3.")
                )

    @api.constrains("tax_id")
    def _check_tax_posts_to_a_cost_account(self):
        """The levy is a COST. Refuse a tax that books it as an asset.

        This is the one rule in this file that is enforced rather than
        described. The competitor reading — "Import Advance Income Tax, offset
        against income tax" — would post the levy to a receivable, capitalising
        3% of every consignment as an asset that is never recovered. A
        constraint means that reading cannot be introduced by editing a record.
        """
        for config in self:
            for line in config.tax_id.invoice_repartition_line_ids:
                account = line.account_id
                if account and account.account_type in FORBIDDEN_TAX_ACCOUNT_TYPES:
                    raise ValidationError(
                        self.env._(
                            "The social welfare levy posts to %(account)s, which is "
                            "a %(kind)s account. The levy is NOT creditable against "
                            "income tax — it is a cost of the import — so it must "
                            "post to an expense account. Booking it as an asset "
                            "capitalises 3%% of every consignment as a receivable "
                            "that will never be recovered.",
                            account=account.display_name,
                            kind=account.account_type,
                        )
                    )

    @api.model
    def _get_config(self, company, on_date=None):
        """Return the configuration effective for ``company`` on ``on_date``."""
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
    def _l10n_et_resolve_config(self, company, on_date):
        """Return ``(config, skip_note)`` — never fails open.

        Same three outcomes as the WHT engine's resolver, and for the same
        reasons: out of scope is silent, no configuration at all is an error,
        and a document predating the earliest record gets a note rather than a
        block so historical imports can be migrated.
        """
        if not company.l10n_et_tax_engine_active:
            return self.browse(), None
        config = self._get_config(company, on_date)
        if config:
            return config, None
        earliest = self.search(
            [("company_id", "=", company.id)], order="effective_from asc", limit=1
        )
        if not earliest:
            raise UserError(
                self.env._(
                    "No Ethiopian social welfare levy configuration exists for "
                    "%(company)s. Configure it under Accounting › Configuration › "
                    "Ethiopian Social Welfare Levy, or turn off the Ethiopian Tax "
                    "Engine on the company if Ethiopian import levies do not apply "
                    "there.",
                    company=company.display_name,
                )
            )
        return self.browse(), self.env._(
            "No Ethiopian social welfare levy configuration is effective for "
            "%(date)s, so no levy was applied. The earliest configured date is "
            "%(earliest)s.",
            date=on_date,
            earliest=earliest.effective_from,
        )

    def compute_levy(self, cif_value, on_date=None, exemption=None):
        """The levy on one import, computed by the reference calculator.

        This method does no arithmetic of its own — it hands this record's
        effective-dated parameters to `et_tax_calc.compute_social_welfare_levy`
        and returns its result, so the Odoo layer and the fast golden tests
        cannot diverge (CLAUDE.md rule 10).
        """
        self.ensure_one()
        return et_tax_calc.compute_social_welfare_levy(
            cif_value,
            on_date=on_date,
            exemption=exemption,
            rate=self.rate,
            effective_from=self.effective_from,
        )

    @api.model
    def _l10n_et_seed_all_companies(self):
        """Data-file/migration hook: seed every active company's levy config."""
        # sudo: a data/migration hook must see EVERY company's existing records,
        # not just those the loading user's rule exposes — otherwise it "finds
        # none" and creates a duplicate.
        seeder = self.sudo()
        for company in self.env["res.company"].sudo().search([("active", "=", True)]):
            seeder._l10n_et_ensure_default(company)
        return True

    @api.model
    def _l10n_et_ensure_default(self, company):
        """Seed the Reg. 519/2022 configuration for ``company`` if it has none.

        The date is the regulation's own commencement date, NOT the date the
        client started using the software: an import cleared in 2023 was subject
        to the levy whether or not this module existed then, and a migrated
        historical bill must compute the same figure the customs declaration
        did.
        """
        if not self.search_count([("company_id", "=", company.id)]):
            self.create(
                {
                    "company_id": company.id,
                    "effective_from": date(2022, 8, 6),
                    "source_note": DEFAULT_SOURCE_NOTE,
                }
            )

    def _l10n_et_get_tax(self):
        """The account.tax to apply — configured, or the chart template's.

        Returns an EMPTY RECORDSET when neither exists, never None:
        `chart_template.ref(..., raise_if_not_found=False)` returns None, and a
        caller reaching for `.name` on that gets an AttributeError instead of
        the "no Ethiopian tax on this company" it was actually looking at.
        """
        tax = self.tax_id
        if not tax:
            tax = (
                self.env["account.chart.template"]
                .with_company(self.company_id)
                .ref(TEMPLATE_TAX_XMLID, raise_if_not_found=False)
            )
        return tax or self.env["account.tax"]
