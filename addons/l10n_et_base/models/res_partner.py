# -*- coding: utf-8 -*-
"""Ethiopian partner compliance fields (TIN, VAT reg. no., business licence).

TIN format validation delegates to the tested reference calculator
(reference/et_tax_calc.py) — the single source of truth; do not re-implement the
format rules here (CLAUDE.md rule #10).
"""

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..reference import et_tax_calc


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_et_tin = fields.Char(
        string="TIN (Ethiopia)",
        size=13,
        index=True,
        help="Ministry of Revenue Taxpayer Identification Number: 10 digits. "
        "Stored normalized (separators stripped).",
    )
    l10n_et_vat_reg_no = fields.Char(
        string="VAT Registration No.",
        help="VAT registration certificate number (distinct from the TIN).",
    )
    l10n_et_business_licence_no = fields.Char(
        string="Business Licence No.",
        help="Trade/business licence number. Suppliers without a valid licence "
        "attract the punitive withholding rate.",
    )
    l10n_et_business_licence_expiry = fields.Date(
        string="Licence Expiry",
        help="Expiry date of the business licence. An expired licence counts as "
        "missing for withholding purposes.",
    )
    l10n_et_is_foreign_digital = fields.Boolean(
        string="Foreign Digital Service Provider",
        help="Bills from this partner attract the foreign digital services "
        "withholding rate (no domestic threshold).",
    )
    l10n_et_name_amharic = fields.Char(
        string="Name (Amharic)",
        help="Legal name in Amharic, for bilingual documents.",
    )
    l10n_et_has_valid_licence = fields.Boolean(
        string="Valid Business Licence",
        compute="_compute_l10n_et_has_valid_licence",
        help="Licence number present and not expired as of today.",
    )
    l10n_et_wht_compliant = fields.Boolean(
        string="WHT Compliant",
        compute="_compute_l10n_et_wht_compliant",
        help="Valid TIN and valid business licence: qualifies for the standard "
        "withholding rate instead of the punitive one.",
    )

    @api.model
    def _commercial_fields(self):
        """Compliance identifiers belong to the commercial entity and propagate to
        its contacts (like ``vat`` in core)."""
        return super()._commercial_fields() + [
            "l10n_et_tin",
            "l10n_et_vat_reg_no",
            "l10n_et_business_licence_no",
            "l10n_et_business_licence_expiry",
            "l10n_et_is_foreign_digital",
        ]

    @api.depends("l10n_et_business_licence_no", "l10n_et_business_licence_expiry")
    def _compute_l10n_et_has_valid_licence(self):
        """A licence is valid if present and (no expiry set or expiry >= today).

        Not stored: the value depends on today's date.
        """
        today = fields.Date.context_today(self)
        for partner in self:
            partner.l10n_et_has_valid_licence = bool(partner.l10n_et_business_licence_no) and (
                not partner.l10n_et_business_licence_expiry
                or partner.l10n_et_business_licence_expiry >= today
            )

    @api.depends(
        "l10n_et_tin",
        "l10n_et_business_licence_no",
        "l10n_et_business_licence_expiry",
    )
    def _compute_l10n_et_wht_compliant(self):
        """Standard-rate eligibility: valid TIN format AND valid licence."""
        for partner in self:
            partner.l10n_et_wht_compliant = (
                et_tax_calc.validate_tin(partner.l10n_et_tin).valid
                and partner.l10n_et_has_valid_licence
            )

    @api.constrains("l10n_et_tin")
    def _check_l10n_et_tin(self):
        """Reject TINs that fail the reference format validation."""
        for partner in self:
            if partner.l10n_et_tin:
                result = et_tax_calc.validate_tin(partner.l10n_et_tin)
                if not result.valid:
                    raise ValidationError(
                        self.env._(
                            "Invalid Ethiopian TIN %(tin)r for %(partner)s: " "%(reason)s",
                            tin=partner.l10n_et_tin,
                            partner=partner.display_name,
                            reason=result.reason,
                        )
                    )

    @api.model
    def _l10n_et_normalize_tin_vals(self, vals):
        """Normalize a TIN in ``vals`` in place (strip separators) when it is valid.

        Invalid values are left untouched so the constraint reports them verbatim.
        """
        tin = vals.get("l10n_et_tin")
        if tin:
            result = et_tax_calc.validate_tin(tin)
            if result.valid:
                vals["l10n_et_tin"] = result.normalized

    def _l10n_et_sync_vat_from_tin(self):
        """Copy the TIN into core ``vat`` wherever ``vat`` is still empty.

        ``vat`` is the field the FRAMEWORK reads. Every core template guards its
        tax-ID line on it — the shared external layout in 17 places, plus the
        invoice, the quotation and the POS receipt — so a tenant with a TIN but no
        ``vat`` prints no identifier on any document it sends. Measured before this
        existed: a customer invoice PDF carried neither the seller's TIN nor the
        buyer's, on a renderer that could draw both.

        ``l10n_et_tin`` stays the system of record: it is validated, indexed and
        propagated to contacts, and Ethiopia's separate VAT registration number
        lives in ``l10n_et_vat_reg_no``, which one core ``vat`` field could never
        also hold. This is a one-way mirror, not a merge.

        NEVER overwrites a non-empty ``vat``. A value somebody typed is a decision;
        this only fills a blank.

        Cannot recurse: the write below carries only ``vat``, and ``write`` re-syncs
        only when ``l10n_et_tin`` is in the values it was given.
        """
        for partner in self:
            if partner.l10n_et_tin and not partner.vat:
                partner.write({"vat": partner.l10n_et_tin})

    @api.model
    def _l10n_et_backfill_vat_from_tin(self):
        """Fill ``vat`` on partners that already exist. Returns those moved.

        A template or module change never reaches a database that already has its
        data — the same trap as the expense-account default. Called from the
        post-init hook and the 19.0.1.6.0 migration. Idempotent: a second run
        reports nothing, because the first left no empty ``vat`` behind a TIN.
        """
        partners = self.search(
            [("l10n_et_tin", "!=", False), "|", ("vat", "=", False), ("vat", "=", "")]
        )
        partners._l10n_et_sync_vat_from_tin()
        return partners

    @api.model_create_multi
    def create(self, vals_list):
        """Store TINs normalized regardless of how they were typed/imported."""
        for vals in vals_list:
            self._l10n_et_normalize_tin_vals(vals)
        partners = super().create(vals_list)
        partners._l10n_et_sync_vat_from_tin()
        return partners

    def write(self, vals):
        """Store TINs normalized regardless of how they were typed/imported."""
        self._l10n_et_normalize_tin_vals(vals)
        result = super().write(vals)
        if vals.get("l10n_et_tin"):
            self._l10n_et_sync_vat_from_tin()
        return result
