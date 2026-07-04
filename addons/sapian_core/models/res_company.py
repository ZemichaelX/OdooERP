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
    sapian_onboarding_done = fields.Boolean(
        string="Onboarding Completed",
        default=False,
        help="Set when the SapianERP onboarding wizard completes successfully for "
        "this company; the onboarding menu then routes to the module catalog "
        "instead of reopening the wizard.",
    )
