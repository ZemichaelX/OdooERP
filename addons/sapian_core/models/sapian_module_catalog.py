# -*- coding: utf-8 -*-
"""Module catalog: a per-company registry of product modules that can be toggled on/off.

Enabling a catalog entry is the no-code lever a consultant uses during onboarding to
turn a product module on for a client (see docs/06_CUSTOMIZATION_GUIDE.md, Layer 1).
Actual installation of the underlying Odoo module is triggered by the onboarding wizard;
this model records the client's intended configuration and per-module settings.
"""

from odoo import api, fields, models


class SapianModuleCatalog(models.Model):
    _name = "sapian.module.catalog"
    _description = "SapianERP Module Catalog Entry"
    _order = "sequence, name"

    name = fields.Char(string="Module", required=True, translate=True)
    technical_name = fields.Char(
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
    enabled = fields.Boolean(default=False)
    sequence = fields.Integer(default=10)
    description = fields.Text(translate=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    _technical_name_company_uniq = models.Constraint(
        "unique(technical_name, company_id)",
        "A module can only appear once per company in the catalog.",
    )

    def action_toggle_enabled(self):
        """Flip the enabled flag. In a full build this also queues installation of the
        underlying Odoo module via the onboarding wizard."""
        for entry in self:
            entry.enabled = not entry.enabled
        return True

    # The standard sellable set (docs/plan-2026/05): seeded per company on demand
    # so the onboarding wizard always has entries to offer.
    STANDARD_CATALOG = [
        ("Inventory", "stock", "supply_chain", "core"),
        ("Sales", "sale_management", "sales", "core"),
        ("Purchase", "purchase", "supply_chain", "core"),
        ("Employees", "hr", "hr", "core"),
        ("Ethiopian Accounting", "l10n_et_base", "finance", "core"),
        ("Ethiopian Payroll", "l10n_et_payroll", "hr", "common"),
        ("Ethiopian Statutory Reports", "l10n_et_reports", "finance", "common"),
    ]

    @api.model
    def _ensure_default_catalog(self, company):
        """Seed the standard catalog entries for ``company`` (idempotent).

        Called by the onboarding wizard so a fresh company immediately has the
        sellable module set to pick from; existing entries are never touched.
        """
        existing = set(
            self.search([("company_id", "=", company.id)]).mapped("technical_name")
        )
        for sequence, (name, technical_name, category, tier) in enumerate(
            self.STANDARD_CATALOG, start=10
        ):
            if technical_name not in existing:
                self.create(
                    {
                        "name": name,
                        "technical_name": technical_name,
                        "category": category,
                        "tier": tier,
                        "sequence": sequence,
                        "company_id": company.id,
                    }
                )
        return self.search([("company_id", "=", company.id)])
