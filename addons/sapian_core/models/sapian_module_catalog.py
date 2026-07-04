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
    enabled = fields.Boolean(
        default=False,
        help="Mirrors whether the module is actually installed: re-synced from "
        "the installed state on every sapian_core upgrade and set by the "
        "onboarding wizard when it installs modules. It is a status, not a "
        "switch — install additional modules via the onboarding wizard (or "
        "Apps); managed per-company uninstall from the catalog is deferred.",
    )
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

    @api.model
    def _sync_enabled_from_installed(self):
        """Make `enabled` reflect reality: an entry is enabled exactly when its
        Odoo module is installed. Runs on every module install/upgrade (data
        `<function>`), so the catalog can never drift from the Apps state —
        the drift is exactly what confused users after upgrades."""
        # 'to upgrade'/'to install' count as installed: the sync runs DURING
        # the module-loading graph (data <function>), where modules later in
        # the graph still carry their transient state — treating them as absent
        # is exactly the post-upgrade drift this sync exists to prevent.
        installed = set(
            self.env["ir.module.module"]
            .sudo()
            .search([("state", "in", ("installed", "to upgrade", "to install"))])
            .mapped("name")
        )
        entries = self.sudo().with_context(active_test=False).search([])
        for entry in entries:
            should_be = entry.technical_name in installed
            if entry.enabled != should_be:
                entry.enabled = should_be
        return True

    def action_sync_enabled(self):
        """List-header button: re-sync the flags on demand."""
        self._sync_enabled_from_installed()
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
        existing = set(self.search([("company_id", "=", company.id)]).mapped("technical_name"))
        installed = set(
            self.env["ir.module.module"]
            .sudo()
            .search([("state", "in", ("installed", "to upgrade", "to install"))])
            .mapped("name")
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
                        # Truthful from birth: enabled mirrors installed state.
                        "enabled": technical_name in installed,
                    }
                )
        return self.search([("company_id", "=", company.id)])
