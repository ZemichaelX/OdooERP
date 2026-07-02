# -*- coding: utf-8 -*-
"""Module catalog: a per-company registry of product modules that can be toggled on/off.

Enabling a catalog entry is the no-code lever a consultant uses during onboarding to
turn a product module on for a client (see docs/06_CUSTOMIZATION_GUIDE.md, Layer 1).
Actual installation of the underlying Odoo module is triggered by the onboarding wizard;
this model records the client's intended configuration and per-module settings.
"""
from odoo import api, fields, models, _


class SapianModuleCatalog(models.Model):
    _name = "sapian.module.catalog"
    _description = "SapianERP Module Catalog Entry"
    _order = "sequence, name"

    name = fields.Char(string="Module", required=True, translate=True)
    technical_name = fields.Char(
        string="Technical Name",
        required=True,
        help="The Odoo technical module name installed when this entry is enabled "
        "(e.g. 'stock', 'sale', 'l10n_et_payroll').",
    )
    category = fields.Selection(
        selection=[
            ("finance", "Finance & Accounting"),
            ("supply_chain", "Supply Chain & Operations"),
            ("sales", "Sales & Customer"),
            ("hr", "Human Resources"),
            ("services", "Services & Projects"),
            ("marketing", "Marketing & Communication"),
            ("platform", "Platform & Cross-cutting"),
        ],
        default="platform",
        required=True,
    )
    tier = fields.Selection(
        selection=[("core", "Core"), ("common", "Common"), ("optional", "Optional/Vertical")],
        default="common",
        required=True,
        help="How central the module is to a typical deployment.",
    )
    enabled = fields.Boolean(string="Enabled", default=False)
    sequence = fields.Integer(default=10)
    description = fields.Text(translate=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            "technical_name_company_uniq",
            "unique(technical_name, company_id)",
            "A module can only appear once per company in the catalog.",
        ),
    ]

    def action_toggle_enabled(self):
        """Flip the enabled flag. In a full build this also queues installation of the
        underlying Odoo module via the onboarding wizard."""
        for entry in self:
            entry.enabled = not entry.enabled
        return True

    @api.model
    def name_get(self):
        return [(rec.id, _("%s") % rec.name) for rec in self]
