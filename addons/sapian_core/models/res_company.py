# -*- coding: utf-8 -*-
"""Company-level SapianERP defaults.

Kept intentionally small in the starter scaffold. This is where Ethiopian defaults and
branding hooks attach (see docs/06_CUSTOMIZATION_GUIDE.md, Layer 2)."""

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sapian_enabled = fields.Boolean(
        string="SapianERP Enabled",
        default=True,
        help="Marks this company as managed by the SapianERP product layer.",
    )
    sapian_default_lang = fields.Selection(
        selection=[("en_US", "English"), ("am_ET", "Amharic"), ("both", "Bilingual (EN/AM)")],
        string="Default Interface Language",
        default="en_US",
    )
