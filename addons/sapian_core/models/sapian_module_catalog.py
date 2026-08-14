# -*- coding: utf-8 -*-
"""Module catalog: a per-company registry of product modules that can be toggled on/off.

Enabling a catalog entry is the no-code lever a consultant uses during onboarding to
turn a product module on for a client (see docs/06_CUSTOMIZATION_GUIDE.md, Layer 1).
Actual installation of the underlying Odoo module is triggered by the onboarding wizard;
this model records the client's intended configuration and per-module settings.
"""

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError


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
    requires_ids = fields.Many2many(
        "sapian.module.catalog",
        "sapian_module_catalog_requires_rel",
        "entry_id",
        "required_id",
        string="Includes",
        help="Catalog entries that come with this one. Picking this module in "
        "the onboarding wizard automatically picks these too.",
    )
    required_by_ids = fields.Many2many(
        "sapian.module.catalog",
        "sapian_module_catalog_requires_rel",
        "required_id",
        "entry_id",
        string="Included by",
        readonly=True,
    )

    # WHY A MANY2MANY AND NOT A CHAR OF TECHNICAL NAMES
    #
    # A char would be simpler to seed and would tolerate naming a module whose
    # entry does not exist yet. Both of those are the argument AGAINST it: this
    # field decides what gets installed on a client's database, and a typo in a
    # free-text list fails silently at the only moment that matters. A relation
    # cannot point at an entry that is not there, the ORM keeps it consistent
    # when an entry is deleted, and the wizard can traverse it directly instead
    # of re-resolving strings. `tier` already showed what happens when catalog
    # meaning lives in loosely-typed data.
    #
    # WHY THIS IS NOT A MANIFEST DEPENDENCY, and please do not move it back
    #
    # A manifest describes what the CODE needs; this describes what a CUSTOMER
    # buys. l10n_et_payroll deliberately does NOT depend on sapian_core — a
    # dependency audit found zero references, and declaring it put the SapianERP
    # tile in every database that installed payroll. "Payroll+HR ships with the
    # SapianERP core" is a packaging decision, and packaging decisions belong in
    # data a consultant can change per client, not in a manifest that forces the
    # same answer on everyone. If you are here because payroll installed without
    # core, the fix is a `requires` row, not a manifest edit.

    _technical_name_company_uniq = models.Constraint(
        "unique(technical_name, company_id)",
        "A module can only appear once per company in the catalog.",
    )

    @api.constrains("requires_ids", "company_id")
    def _check_requires_same_company(self):
        """`requires` may not cross companies.

        Every other field on this model is per-company; a relation that leaked
        across would let one client's catalog decide another client's installs.
        """
        for entry in self:
            foreign = entry.requires_ids.filtered(
                lambda r, e=entry: r.company_id != e.company_id
            )
            if foreign:
                raise ValidationError(
                    self.env._(
                        "%(entry)s requires catalog entries belonging to another "
                        "company: %(others)s. The catalog is per-company.",
                        entry=entry.display_name,
                        others=", ".join(foreign.mapped("display_name")),
                    )
                )

    @api.constrains("requires_ids")
    def _check_requires_no_cycle(self):
        """A requires chain may not loop.

        Not decoration: `_expand_requires` walks this relation to decide what to
        install, so a cycle is either an infinite loop or — worse — a traversal
        that silently stops early and installs less than the customer bought.
        The traversal below is written to terminate regardless, so this
        constraint is what turns a bad configuration into a refusal at the
        moment someone creates it, rather than a surprise at provisioning.
        """
        for entry in self:
            seen = set()
            frontier = entry.requires_ids
            while frontier:
                if entry in frontier:
                    raise ValidationError(
                        self.env._(
                            "%(entry)s cannot require itself, directly or through "
                            "a chain of other entries.",
                            entry=entry.display_name,
                        )
                    )
                seen |= set(frontier.ids)
                frontier = frontier.mapped("requires_ids").filtered(lambda r: r.id not in seen)

    def _expand_requires(self):
        """Return these entries plus everything they include, transitively.

        The closure, not one hop: if Payroll includes Core and Core ever
        includes something else, the customer bought that too. Terminates on a
        cycle by construction (a `seen` set), so a mis-seeded catalog degrades
        to "installs too little" rather than hanging a provisioning run — the
        constraint above is what stops it being mis-seeded in the first place.
        """
        result = self.browse()
        frontier = self
        while frontier:
            result |= frontier
            frontier = frontier.mapped("requires_ids") - result
        return result

    @api.model
    def _reachable_module_names(self, module_name):
        """Every module reachable from ``module_name``'s manifest, transitively.

        THE CONTRACT THIS EXISTS TO KEEP, said once here instead of copied into
        every module that provisions a tenant.

        `sapian.onboarding.wizard.action_apply` installs whatever it is handed
        that is still uninstalled. That is correct during real onboarding, and
        it is fatal for a scripted tenant build: `button_immediate_install`
        commits and replaces the registry underneath the running script. Odoo
        refuses outright when it cannot take the `ir_cron` lock, which surfaces
        as the deeply unhelpful "Odoo is currently processing a scheduled
        action".

        So a provisioner must hand the wizard ONLY entries that are already
        installed — which, for a module being provisioned, means entries
        reachable from its own manifest. Then the install step is a guaranteed
        no-op.

        This was learned twice. `sapian_demo_trader` used to pick by TIER,
        which coincided with its dependency set only while the catalog held 15
        curated entries; seeding all 38 broke the coincidence and it was fixed
        to select on the property itself. `sapian_dress_rehearsal` handed the
        wizard the WHOLE catalog and was not fixed at the same time, so it
        tried to install 28 modules mid-provision and the rehearsal script
        stopped running at all — invisibly, because the wizard SKIPS
        installation in test mode, so its tests stayed green.

        Hence: one helper, used by both.
        """
        module_model = self.env["ir.module.module"].sudo()
        frontier = module_model.search([("name", "=", module_name)])
        reachable = set()
        while frontier:
            reachable.update(frontier.mapped("name"))
            names = frontier.mapped("dependencies_id.name")
            frontier = module_model.search(
                [("name", "in", names), ("name", "not in", list(reachable))]
            )
        return reachable

    def _filter_safe_to_pick(self, module_name):
        """The subset of these entries a ``module_name`` provisioner may pick.

        Everything else stays seeded and un-picked, which is the point: the
        catalog shows what is enabled alongside what is available.
        """
        reachable = self._reachable_module_names(module_name)
        return self.filtered(lambda entry: entry.technical_name in reachable)

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
        # technical_name is required, so this is "all entries" with an explicit
        # domain (the catalog is a small per-company table; pylint-odoo W8163
        # rightly refuses a bare search([])).
        entries = (
            self.sudo()
            .with_context(active_test=False)
            .search([("technical_name", "!=", False)])
        )
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
    #
    # Tiers drive onboarding pre-selection (default_get pre-ticks core):
    #   core     — installed for essentially every client (the sellable baseline)
    #   common   — Ethiopian add-ons most clients take
    #   optional — standard Odoo Community apps offered on demand; no Ethiopian
    #              customization layer, so left un-ticked until a client asks.
    # The optional block makes the extra Community apps installable through
    # onboarding instead of only via the raw Apps menu; each technical_name is a
    # stock Odoo 19 Community module.
    STANDARD_CATALOG = [
        # ---- core: the SapianERP product itself -----------------------------
        ("SapianERP Core", "sapian_core", "platform", "core"),
        ("Ethiopian Accounting", "l10n_et_base", "finance", "core"),
        ("Ethiopian Payroll", "l10n_et_payroll", "hr", "core"),
        # Named to match the app tile the client will actually see. The menu was
        # renamed from "Ethiopian Statutory Reports" when l10n_et_reports became
        # a top-level app; a prospect picking a module here and then hunting for
        # a differently-named tile is a self-inflicted demo bug.
        ("Ethiopian Compliance", "l10n_et_reports", "finance", "core"),
        # ---- common: what a typical deployment takes ------------------------
        ("Invoicing", "account", "finance", "common"),
        ("Sales", "sale_management", "sales", "common"),
        ("Purchase", "purchase", "supply_chain", "common"),
        ("Inventory", "stock", "supply_chain", "common"),
        ("Employees", "hr", "hr", "common"),
        ("Contacts", "contacts", "sales", "common"),
        ("CRM", "crm", "sales", "common"),
        ("Calendar", "calendar", "platform", "common"),
        ("Discuss", "mail", "platform", "common"),
        ("Dashboards", "board", "platform", "common"),
        ("Project", "project", "services", "common"),
        ("Expenses", "hr_expense", "hr", "common"),
        ("Time Off", "hr_holidays", "hr", "common"),
        ("Attendances", "hr_attendance", "hr", "common"),
        ("Point of Sale", "point_of_sale", "sales", "common"),
        # ---- optional: offered on demand ------------------------------------
        ("Manufacturing", "mrp", "supply_chain", "optional"),
        ("Fleet", "fleet", "platform", "optional"),
        ("Repairs", "repair", "supply_chain", "optional"),
        ("Maintenance", "maintenance", "supply_chain", "optional"),
        ("Lunch", "lunch", "hr", "optional"),
        ("Recruitment", "hr_recruitment", "hr", "optional"),
        ("To-do", "project_todo", "services", "optional"),
        ("Restaurant (POS)", "pos_restaurant", "sales", "optional"),
        ("Data Cleaning", "data_recycle", "platform", "optional"),
        ("Website", "website", "marketing", "optional"),
        ("eCommerce", "website_sale", "sales", "optional"),
        ("eLearning", "website_slides", "marketing", "optional"),
        ("Events", "website_event", "marketing", "optional"),
        ("Live Chat", "im_livechat", "marketing", "optional"),
        ("Email Marketing", "mass_mailing", "marketing", "optional"),
        ("SMS Marketing", "mass_mailing_sms", "marketing", "optional"),
        ("Surveys", "survey", "marketing", "optional"),
        ("Marketing Card", "marketing_card", "marketing", "optional"),
        ("Pharma Vertical", "vertical_pharma", "supply_chain", "optional"),
    ]

    # Product bundles: "buying this means getting that".
    #
    # {technical_name: (technical_names it comes with, ...)}
    #
    # ONE entry on purpose. This is not a place to restate manifest
    # dependencies — Odoo already installs those, and duplicating them here
    # would rot the moment a manifest changed. It records only decisions a
    # CUSTOMER would recognise, and there is exactly one today: the standalone
    # Payroll+HR product ships with the SapianERP core, which is why
    # l10n_et_payroll's manifest no longer names sapian_core.
    #
    # Adding a row here is a product decision, not a technical one.
    STANDARD_REQUIRES = {
        "l10n_et_payroll": ("sapian_core",),
    }

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
        entries = self.search([("company_id", "=", company.id)])

        # Wire the product bundles. A SECOND pass on purpose: a requires row
        # points at another entry, which may have been created moments ago in
        # the loop above, so the links cannot be set inline. Idempotent — only
        # missing links are added, and an operator who deliberately removed one
        # for a client is not overruled on the next upgrade.
        by_name = {entry.technical_name: entry for entry in entries}
        for technical_name, required_names in self.STANDARD_REQUIRES.items():
            entry = by_name.get(technical_name)
            if not entry:
                continue
            wanted = self.browse()
            for required in required_names:
                target = by_name.get(required)
                if target:
                    wanted |= target
            missing = wanted - entry.requires_ids
            if missing:
                entry.requires_ids = [Command.link(target.id) for target in missing]
        return entries
