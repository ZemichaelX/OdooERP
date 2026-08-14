# -*- coding: utf-8 -*-
"""The catalog/dependency invariant, machine-checked.

Module installation is forbidden while the registry is loading and inside
tests, so every catalog entry the provisioner PICKS must already be installed
when the wizard runs — i.e. it must be reachable from this module's manifest
dependencies. That rule spans two modules and was previously enforced only by a
comment; adding a catalog entry without its dependency silently broke the demo
build.

The invariant is over the PICKED entries, not the whole catalog. The demo picks
catalog entries that are reachable dependencies of this module; everything else
is seeded and left un-picked, so those apps stay visible as
available-and-not-enabled without being installed — which is the point, since
installing them put Manufacturing, Fleet, Repair, Project and Website in the
demo tenant's main menu bar.

The pick used to be by TIER (core+common), which coincided with the dependency
set only while the catalog held 15 curated entries. Seeding the full 38-app
catalogue broke the coincidence: `common` now holds crm, project,
point_of_sale, calendar, contacts, board and the hr_* apps, none of them
dependencies here. The demo now selects on the property itself, so this test
asserts a fact rather than a coincidence.
"""

from odoo.tests import TransactionCase, tagged

from odoo.addons.sapian_core.models.sapian_module_catalog import (
    SapianModuleCatalog,
)


@tagged("post_install", "-at_install")
class TestCatalogDependencies(TransactionCase):
    def _reachable_dependencies(self):
        """Every module reachable from sapian_demo_trader's manifest.

        Walks the graph: a catalog app pulled in indirectly (e.g. 'stock' via
        'sale_management') satisfies the invariant just as well.
        """
        module_model = self.env["ir.module.module"]
        demo_module = module_model.search([("name", "=", "sapian_demo_trader")], limit=1)
        self.assertTrue(demo_module, "sapian_demo_trader must be present")
        reachable = set()
        frontier = demo_module
        while frontier:
            reachable.update(frontier.mapped("name"))
            names = frontier.mapped("dependencies_id.name")
            frontier = module_model.search(
                [("name", "in", names), ("name", "not in", list(reachable))]
            )
        return reachable

    def test_every_picked_catalog_app_is_a_dependency(self):
        """Picked catalog module names ⊆ this module's transitive dependencies.

        Asserted against what the provisioner ACTUALLY picks — the same helper
        it calls — not against a tier list that merely used to agree with it.
        """
        catalogued = {entry[1] for entry in SapianModuleCatalog.STANDARD_CATALOG}
        installable = self.env["sapian.demo.trader"]._demo_installable_names()
        picked = catalogued & installable
        self.assertTrue(picked, "the demo must pick at least one catalog app")
        missing = sorted(picked - self._reachable_dependencies())
        self.assertFalse(
            missing,
            "These PICKED sapian_core catalog apps are not dependencies of "
            "sapian_demo_trader, so demo provisioning would try to install them "
            "mid-load and fail: %s" % ", ".join(missing),
        )

    def test_unpicked_catalog_apps_are_not_dependencies(self):
        """The other half of the slimming, and the half that regresses quietly.

        Picking fewer catalog entries does not remove anything on its own — the
        manifest is what installs a module. If an `optional` app creeps back
        into the dependency list, it reappears in the demo tenant's main menu
        bar, which is in every frame of a screen recording, while every other
        test in the suite still passes.
        """
        catalogued = {entry[1] for entry in SapianModuleCatalog.STANDARD_CATALOG}
        unpicked = catalogued - self.env["sapian.demo.trader"]._demo_installable_names()
        self.assertTrue(unpicked, "the catalog must still offer un-picked apps")
        leaked = sorted(unpicked & self._reachable_dependencies())
        self.assertFalse(
            leaked,
            "These catalog apps are NOT picked by the demo but are still "
            "installed by its manifest, so they show up in the demo tenant's "
            "menu bar: %s" % ", ".join(leaked),
        )

    def test_unpicked_apps_are_offered_not_hidden(self):
        """Every catalog entry is still seeded — the un-picked ones are visible
        and not enabled, the honest answer to "so it does manufacturing?"."""
        company = self.env["res.company"].create({"name": "Catalog Visibility PLC"})
        catalog = self.env["sapian.module.catalog"]._ensure_default_catalog(company)
        self.assertEqual(len(catalog), len(SapianModuleCatalog.STANDARD_CATALOG))
        installable = self.env["sapian.demo.trader"]._demo_installable_names()
        unpicked = catalog.filtered(lambda entry: entry.technical_name not in installable)
        self.assertTrue(unpicked, "un-picked apps must still appear in the catalog")
        # `enabled` is a status, not a switch: it mirrors the installed state.
        # Compared against what is actually installed rather than asserted to
        # be empty, so the test stays true on a developer database that happens
        # to have one of these apps installed for unrelated reasons.
        installed = set(
            self.env["ir.module.module"]
            .search(
                [
                    ("name", "in", unpicked.mapped("technical_name")),
                    ("state", "=", "installed"),
                ]
            )
            .mapped("name")
        )
        self.assertEqual(
            set(unpicked.filtered("enabled").mapped("technical_name")),
            installed,
            "un-picked catalog apps must report enabled exactly when installed",
        )
