# -*- coding: utf-8 -*-
"""Pharma product flag: turns on the whole batch discipline.

Flagging a product enforces lot tracking + expiration dates and moves it onto
the FEFO 'Pharmaceuticals' category, so earliest-expiry stock always leaves
first (good distribution practice per the DAT proposal §8.1)."""

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_pharma = fields.Boolean(
        string="Pharmaceutical Product",
        help="Enforces batch (lot) tracking with mandatory expiry dates, FEFO "
        "removal and expiry alerting for this product.",
    )

    @api.onchange("is_pharma")
    def _onchange_is_pharma(self):
        """Immediately reflect the discipline in the form."""
        if self.is_pharma:
            self.tracking = "lot"
            self.use_expiration_date = True

    @api.constrains("is_pharma", "tracking", "use_expiration_date")
    def _check_pharma_discipline(self):
        """A pharma product without lot tracking + expiry is a compliance hole."""
        for template in self:
            if template.is_pharma and (
                template.tracking not in ("lot", "serial") or not template.use_expiration_date
            ):
                raise ValidationError(
                    self.env._(
                        "Pharmaceutical products must be lot-tracked with "
                        "expiration dates (%(product)s).",
                        product=template.display_name,
                    )
                )

    @api.model
    def _inject_pharma_vals(self, vals):
        """Complete a value dict that flags a product as pharma so the record
        is compliant the instant it is validated (the constraint runs inside
        create/write, BEFORE any post-processing could fix things up)."""
        if vals.get("tracking") not in ("lot", "serial"):
            vals["tracking"] = "lot"
        vals["use_expiration_date"] = True
        pharma_category = self.env.ref(
            "vertical_pharma.product_category_pharma", raise_if_not_found=False
        )
        if pharma_category and "categ_id" not in vals:
            vals["categ_id"] = pharma_category.id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_pharma"):
                self._inject_pharma_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("is_pharma"):
            self._inject_pharma_vals(vals)
        if "is_pharma" in vals and not vals["is_pharma"]:
            # Un-flagging drops every existing lot out of the expiry gates and
            # the digest (both key off product.is_pharma via the related field);
            # refuse while batches exist so expired stock can't silently ship.
            offending = self.filtered(
                lambda tmpl: tmpl.is_pharma
                and self.env["stock.lot"]
                .sudo()
                .search_count([("product_id", "in", tmpl.product_variant_ids.ids)])
            )
            if offending:
                raise ValidationError(
                    self.env._(
                        "Cannot remove the pharmaceutical flag from %(products)s: "
                        "batches already exist. Their expiry compliance would be "
                        "lost. Archive the product instead.",
                        products=", ".join(offending.mapped("display_name")),
                    )
                )
        return super().write(vals)
