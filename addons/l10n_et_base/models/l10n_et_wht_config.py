# -*- coding: utf-8 -*-
"""Effective-dated Ethiopian withholding-tax configuration.

Rates, thresholds and the punitive-gating flag are CONFIGURATION DATA (CLAUDE.md
rule #4): a future rate change is a NEW record with a new effective_from — it must
never rewrite bills posted under the old rules. The actual math lives in the pure-
Python reference calculator (reference/et_tax_calc.py); this model only stores and
serves the parameters.
"""

from datetime import date

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..reference import et_tax_calc

# Template xml ids of the WHT taxes shipped by this module, by decision kind.
TEMPLATE_TAX_XMLID_BY_KIND = {
    "goods": "l10n_et_base_tax_wht_purchase_goods_3",
    "service": "l10n_et_base_tax_wht_purchase_services_3",
    "foreign_digital": "l10n_et_base_tax_wht_purchase_foreign_digital_15",
    "punitive": "l10n_et_base_tax_wht_purchase_punitive_30",
}

DEFAULT_SOURCE_NOTE = (
    "WHT 3% goods >20,000 / services >10,000; 30% punitive when EITHER the TIN "
    "or the business licence is missing; 15% foreign digital services. "
    "Thresholds gate ALL WHT including punitive. Accountant-confirmed Jul 2026 "
    "(Proc 979/2016 art. 92 lineage + Aug 2025 rules). "
    "Corroborated by PwC's Ethiopia withholding-tax summary: domestic 3% with "
    "ETB 20,000 goods / ETB 10,000 services thresholds, 30% where no TIN."
)

# CORROBORATION, NOT AUTHORITY.
#
# PwC's Ethiopia withholding-tax summary independently confirms the figures
# already held here: the domestic rate at 3%, the thresholds at ETB 20,000
# (goods) and ETB 10,000 (services), and the no-TIN rate at 30% — matching
# DEFAULT_WHT_RATE_STANDARD, DEFAULT_WHT_THRESHOLD_GOODS,
# DEFAULT_WHT_THRESHOLD_SERVICE and DEFAULT_WHT_RATE_PUNITIVE in
# reference/et_tax_calc.py.
#
# A second source agreeing does not promote a summary table to a source of
# truth. The PROCLAMATIONS remain the authority and every rate here still needs
# re-verification against gazetted text before a go-live. What the corroboration
# buys is that the next person does not have to re-derive these four numbers
# from scratch to satisfy themselves — which is why it is written down here
# rather than in a chat log.
#
# It also does NOT license adding rates. Ethiopia withholds on dividends,
# royalties, interest, management and technical fees, and levies a social
# welfare levy; none is implemented, and none may be added from a summary table.
# Each needs rate, base, threshold, effective date and a proclamation citation
# established first (reference-calculator-first rule). Adding a rate on the
# strength of a summary is exactly the failure the core 2%/35% deactivation
# fixes.
#
# OPEN DISCREPANCY, deliberately left alone: `_l10n_et_ensure_default` seeds
# effective_from = date(2025, 8, 1), while the knowledge base records the
# domestic WHT change as effective 7 August 2025 (Nehase 1, 2017 EC). These
# cannot both be right, and 1 Aug 2025 is Hamle 25 — mid-Ethiopian-month, which
# no verified Ethiopian effective date has been. Neither artefact is changed
# here; the correct date is being established from a primary source. Until then,
# treat any WHT decision dated 1-6 Aug 2025 as unverified.
#
# (This comment said "Hamle 24" until l10n_et_calendar existed to check it. The
# conversion is Hamle 25: Nehase 1 is 7 Aug, Hamle has 30 days, so 1 Aug is
# Hamle 25. A hand-converted date in a comment about a hand-converted date
# being wrong is its own small argument for the library. The DISCREPANCY is
# unchanged — only the arithmetic describing it is corrected.)
#
# Now machine-checked: tests_fast/test_et_statutory_dates_land_on_month_1.py
# asserts that every shipped Ethiopian effective date lands on day 1, with this
# seed marked xfail(strict=True) so the open question is visible on every run
# and the marker must be deleted when the seed is corrected.


class L10nEtWhtConfig(models.Model):
    _name = "l10n.et.wht.config"
    _description = "Ethiopian Withholding Tax Configuration (effective-dated)"
    _order = "effective_from desc"

    name = fields.Char(compute="_compute_name", store=True)
    effective_from = fields.Date(
        required=True,
        help="First date (inclusive) on which this configuration applies.",
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
    rate_standard = fields.Float(
        string="Standard Rate (fraction)",
        required=True,
        default=et_tax_calc.DEFAULT_WHT_RATE_STANDARD,
        help="Domestic WHT rate as a fraction, e.g. 0.03 for 3%.",
    )
    rate_punitive = fields.Float(
        string="Punitive Rate (fraction)",
        required=True,
        default=et_tax_calc.DEFAULT_WHT_RATE_PUNITIVE,
        help="Rate applied when the supplier lacks a TIN and/or a valid business "
        "licence, e.g. 0.30 for 30%.",
    )
    rate_foreign_digital = fields.Float(
        string="Foreign Digital Rate (fraction)",
        required=True,
        default=et_tax_calc.DEFAULT_WHT_RATE_FOREIGN_DIGITAL,
        help="Rate for foreign digital service providers, e.g. 0.15 for 15%.",
    )
    threshold_goods = fields.Float(
        string="Goods Threshold (ETB)",
        required=True,
        default=et_tax_calc.DEFAULT_WHT_THRESHOLD_GOODS,
        help="Per-transaction goods base ABOVE which WHT applies (exclusive).",
    )
    threshold_service = fields.Float(
        string="Services Threshold (ETB)",
        required=True,
        default=et_tax_calc.DEFAULT_WHT_THRESHOLD_SERVICE,
        help="Per-transaction services base ABOVE which WHT applies (exclusive).",
    )
    punitive_respects_thresholds = fields.Boolean(
        string="Punitive Rate Respects Thresholds",
        default=True,
        help="If set, the 30% punitive rate only applies above the same "
        "goods/services thresholds. ACCOUNTANT-CONFIRMED Jul 2026: keep set "
        "(thresholds gate all WHT including punitive). Unset only if the "
        "authority instructs the ungated reading — flippable without a code "
        "release.",
    )
    source_note = fields.Char(
        required=True,
        default=DEFAULT_SOURCE_NOTE,
        help="Legal source of these figures. Displayed so every go-live re-verifies "
        "against gazetted proclamation text.",
    )
    tax_goods_id = fields.Many2one(
        "account.tax",
        string="Goods WHT Tax",
        check_company=True,
        domain=[("type_tax_use", "=", "purchase")],
        help="Tax record used for standard WHT on goods. Empty = the tax shipped by "
        "this module's chart template.",
    )
    tax_service_id = fields.Many2one(
        "account.tax",
        string="Services WHT Tax",
        check_company=True,
        domain=[("type_tax_use", "=", "purchase")],
        help="Tax record used for standard WHT on services. Empty = template default.",
    )
    tax_punitive_id = fields.Many2one(
        "account.tax",
        string="Punitive WHT Tax",
        check_company=True,
        domain=[("type_tax_use", "=", "purchase")],
        help="Tax record used for punitive WHT. Empty = template default.",
    )
    tax_foreign_digital_id = fields.Many2one(
        "account.tax",
        string="Foreign Digital WHT Tax",
        check_company=True,
        domain=[("type_tax_use", "=", "purchase")],
        help="Tax record used for foreign digital services WHT. Empty = template " "default.",
    )

    @api.depends("rate_standard", "effective_from", "effective_to")
    def _compute_name(self):
        """Human-readable label, e.g. 'WHT 3% from 2025-08-01'."""
        for config in self:
            config.name = self.env._(
                "WHT %(rate).0f%% from %(date_from)s%(date_to)s",
                rate=config.rate_standard * 100,
                date_from=config.effective_from or "?",
                date_to=config.effective_to and self.env._(" to %s", config.effective_to) or "",
            )

    @api.constrains("effective_from", "effective_to", "company_id")
    def _check_no_overlap(self):
        """Two configs for one company must not overlap: the applicable config must
        be unambiguous for any bill date (historical correctness)."""
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
                        "Withholding tax configurations must not overlap in "
                        "time for the same company."
                    )
                )

    @api.constrains(
        "rate_standard",
        "rate_punitive",
        "rate_foreign_digital",
        "threshold_goods",
        "threshold_service",
    )
    def _check_values(self):
        """Rates are fractions in [0, 1]; thresholds cannot be negative."""
        for config in self:
            rates = (config.rate_standard, config.rate_punitive, config.rate_foreign_digital)
            if any(not 0 <= rate <= 1 for rate in rates):
                raise ValidationError(
                    self.env._("WHT rates are fractions: use 0.03 for 3%, not 3.")
                )
            if config.threshold_goods < 0 or config.threshold_service < 0:
                raise ValidationError(self.env._("WHT thresholds cannot be negative."))

    @api.model
    def _get_config(self, company, on_date=None):
        """Return the configuration effective for ``company`` on ``on_date``.

        Empty recordset when none applies — the WHT engine then stays inert, so the
        module is safe to install on non-Ethiopian companies.
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
    def _l10n_et_resolve_config(self, company, on_date):
        """Return ``(config, skip_note)`` for an engine call — never fails open.

        Three outcomes, deliberately different (the silent empty recordset used
        to cover all three):

        * company out of scope (``l10n_et_tax_engine_active`` off) → empty
          recordset, no note: the engine stays inert, which is correct for a
          non-Ethiopian company or one with no Ethiopian fiscal setup.
        * in scope but NO configuration records at all → ``UserError``. That is
          the compliance hole this replaces: posting bills with no withholding
          and no warning must be impossible.
        * in scope, records exist, but none is effective on ``on_date`` (a
          backdated document that predates the earliest configuration) → empty
          recordset plus a note for the document's chatter. Deliberately NOT an
          error: importing historical bills whose withholding was computed and
          remitted years before this engine existed is normal delivery work,
          and a hard block would make data migration impossible.
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
                    "No Ethiopian withholding tax configuration exists for "
                    "%(company)s. Configure it under Accounting › Configuration › "
                    "Ethiopian WHT Configuration, or turn off the Ethiopian Tax "
                    "Engine on the company if Ethiopian withholding does not "
                    "apply there.",
                    company=company.display_name,
                )
            )
        return self.browse(), self.env._(
            "No Ethiopian WHT configuration is effective for %(date)s, so no "
            "withholding was applied. The earliest configured date is "
            "%(earliest)s.",
            date=on_date,
            earliest=earliest.effective_from,
        )

    @api.model
    def _l10n_et_seed_all_companies(self):
        """Data-file/migration hook: seed every active company's WHT config."""
        # sudo: a data-file/migration hook must see EVERY company's existing
        # records, not just those the loading user's allowed-companies rule
        # exposes — otherwise it "finds none" and creates a duplicate.
        seeder = self.sudo()
        for company in self.env["res.company"].sudo().search([("active", "=", True)]):
            seeder._l10n_et_ensure_default(company)
        return True

    @api.model
    def _l10n_et_ensure_default(self, company):
        """Seed the Aug-2025 default configuration for ``company`` if it has none.

        Called when the 'et' chart loads and from the module's post_init hook.
        Defaults come from the reference calculator (single source of truth) with
        the mandatory source note.
        """
        if not self.search_count([("company_id", "=", company.id)]):
            self.create(
                {
                    "company_id": company.id,
                    "effective_from": date(2025, 8, 1),
                    "source_note": DEFAULT_SOURCE_NOTE,
                }
            )

    def _l10n_et_get_tax(self, kind):
        """Return the account.tax record to apply for a WHT decision ``kind``.

        Prefers the explicitly configured tax; falls back to the tax this module
        ships in the chart template (resolved per company).
        """
        self.ensure_one()
        field_by_kind = {
            "goods": "tax_goods_id",
            "service": "tax_service_id",
            "foreign_digital": "tax_foreign_digital_id",
            "punitive": "tax_punitive_id",
        }
        tax = self[field_by_kind[kind]]
        if not tax:
            tax = (
                self.env["account.chart.template"]
                .with_company(self.company_id)
                .ref(TEMPLATE_TAX_XMLID_BY_KIND[kind], raise_if_not_found=False)
            )
        return tax

    @api.model
    def _l10n_et_base_generate_demo_documents(self):
        """Create demo bills/invoices on the ET demo company (demo data only).

        Exercises every tax path of the localization: 3% WHT on goods, 30%
        punitive WHT (supplier without TIN), 15% foreign digital WHT and a 15%
        VAT sale invoice. Guarded (needs the core `l10n_et` demo company on the
        'et' chart) and idempotent (marker reference), so demo reloads are safe.
        """
        company = self.env.ref("base.demo_company_et", raise_if_not_found=False)
        if not company or company.chart_template != "et":
            return
        # Module demo data loads BEFORE the post_init hook, and the demo company's
        # chart was loaded by core l10n_et before this module registered its
        # template extension — without the reload below the demo company has
        # neither the WHT taxes nor the configs, and posting the demo bills
        # would fail (or silently skip WHT).
        self.env["account.chart.template"]._l10n_et_base_reload_for_company(company)
        move_model = self.env["account.move"].with_company(company)
        if move_model.search_count(
            [
                ("company_id", "=", company.id),
                ("ref", "=", "L10N-ET-BASE-DEMO"),
            ]
        ):
            return

        def create_move(move_type, partner_xmlid, product_xmlid, price):
            return move_model.create(
                {
                    "move_type": move_type,
                    "partner_id": self.env.ref(f"l10n_et_base.{partner_xmlid}").id,
                    "invoice_date": "2026-07-01",
                    "ref": "L10N-ET-BASE-DEMO",
                    "company_id": company.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.env.ref(f"l10n_et_base.{product_xmlid}").id,
                                "quantity": 1,
                                "price_unit": price,
                            }
                        )
                    ],
                }
            )

        moves = (
            # goods 50,000 from a compliant supplier → 3% WHT = 1,500
            create_move("in_invoice", "demo_partner_compliant", "demo_product_goods", 50000)
            # services 15,000 from a no-TIN supplier → punitive 30% = 4,500
            | create_move("in_invoice", "demo_partner_no_tin", "demo_product_service", 15000)
            # foreign digital services 8,000 → 15% = 1,200 (no threshold)
            | create_move(
                "in_invoice", "demo_partner_foreign_digital", "demo_product_service", 8000
            )
            # sale 10,000 → default 15% VAT = 1,500
            | create_move("out_invoice", "demo_partner_compliant", "demo_product_goods", 10000)
        )
        moves.action_post()
