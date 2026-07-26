# -*- coding: utf-8 -*-
"""The catalog/dependency invariant, machine-checked.

The demo hands the onboarding wizard the WHOLE catalog, and module installation
is forbidden while demo data loads. So every app in sapian_core's
STANDARD_CATALOG must already be installed by then — i.e. it must be reachable
from this module's manifest dependencies. That rule spans two modules and was
previously enforced only by a comment; adding a catalog entry without its
dependency silently broke `-i sapian_demo_trader --with-demo`.
"""

from odoo.tests import TransactionCase, tagged

from odoo.addons.sapian_core.models.sapian_module_catalog import (
    SapianModuleCatalog,
)


@tagged("post_install", "-at_install")
class TestCatalogDependencies(TransactionCase):
    def test_every_catalog_app_is_a_dependency(self):
        """Catalog module names ⊆ this module's transitive dependencies."""
        module_model = self.env["ir.module.module"]
        demo_module = module_model.search([("name", "=", "sapian_demo_trader")], limit=1)
        self.assertTrue(demo_module, "sapian_demo_trader must be present")

        # Walk the dependency graph: a catalog app pulled in indirectly (e.g.
        # 'stock' via 'sale_management') satisfies the invariant just as well.
        reachable = set()
        frontier = demo_module
        while frontier:
            reachable.update(frontier.mapped("name"))
            names = frontier.mapped("dependencies_id.name")
            frontier = module_model.search(
                [("name", "in", names), ("name", "not in", list(reachable))]
            )

        catalog_names = {entry[1] for entry in SapianModuleCatalog.STANDARD_CATALOG}
        missing = sorted(catalog_names - reachable)
        self.assertFalse(
            missing,
            "These sapian_core catalog apps are not dependencies of "
            "sapian_demo_trader, so demo provisioning would try to install them "
            "mid-load and fail: %s" % ", ".join(missing),
        )
