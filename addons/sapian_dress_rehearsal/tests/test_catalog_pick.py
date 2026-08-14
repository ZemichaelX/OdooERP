# -*- coding: utf-8 -*-
"""The catalog/dependency invariant for the REHEARSAL tenant.

WHY THIS FILE EXISTS, and why its absence cost a working script.

`sapian.onboarding.wizard.action_apply` installs whatever it is handed that is
still uninstalled. In a live request that is correct. In a scripted tenant
build it is fatal: `button_immediate_install` commits and replaces the registry
under the running script, and Odoo refuses when it cannot take the `ir_cron`
lock — surfacing as "Odoo is currently processing a scheduled action".

`_onboard_company` used to hand the wizard `Command.set(catalog.ids)` — the
WHOLE catalog. That was a no-op only while the catalog held 15 curated entries
that happened to coincide with this module's dependencies. Seeding all 38
turned it into 28 uninstalled modules, and `scripts/dress_rehearsal.sh` stopped
running.

AND NOTHING CAUGHT IT. `_install_modules` skips installation when
`module_tools.current_test` is set, so every test of this module ran in the one
mode where the failure is impossible. The tests were green while the script was
dead — a success signal produced by doing nothing.

So the assertion here is not "provisioning works" (which the other tests
already claim, from inside test mode). It is the narrower, mode-independent
fact the script depends on: **every entry the provisioner hands the wizard is
already installed.**
"""

from odoo.tests import TransactionCase, tagged

from odoo.addons.sapian_core.models.sapian_module_catalog import SapianModuleCatalog

MODULE = "sapian_dress_rehearsal"


@tagged("post_install", "-at_install")
class TestRehearsalCatalogPick(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Rehearsal Pick Co"})
        cls.catalog = cls.env["sapian.module.catalog"]._ensure_default_catalog(cls.company)

    def test_the_pick_contains_no_uninstalled_module(self):
        """The whole contract, asserted directly against module state.

        This is what would have gone red the moment the catalog grew, in every
        mode, without knowing anything about wizards or registries.
        """
        picks = self.catalog._filter_safe_to_pick(MODULE)
        self.assertTrue(picks, "the rehearsal must pick at least one catalog app")
        uninstalled = self.env["ir.module.module"].search(
            [
                ("name", "in", picks.mapped("technical_name")),
                ("state", "!=", "installed"),
            ]
        )
        self.assertFalse(
            uninstalled,
            "These picked catalog apps are NOT installed, so the wizard would "
            "try to install them mid-provision and scripts/dress_rehearsal.sh "
            "would die on 'Odoo is currently processing a scheduled action': %s"
            % ", ".join(sorted(uninstalled.mapped("name"))),
        )

    def test_the_guard_discriminates(self):
        """The whole catalog — what the code used to pass — must FAIL it.

        Without this, a `_filter_safe_to_pick` that silently returned an empty
        set, or one that happened to be correct because everything in the
        catalog was installed on this database, would look identical to a
        working guard.
        """
        everything = self.catalog
        uninstalled = self.env["ir.module.module"].search(
            [
                ("name", "in", everything.mapped("technical_name")),
                ("state", "!=", "installed"),
            ]
        )
        self.assertTrue(
            uninstalled,
            "The entire catalog is installed on this database, so the check "
            "above cannot distinguish a correct pick from no filtering at all. "
            "Re-run on a database that does not have every app installed.",
        )
        self.assertLess(
            len(self.catalog._filter_safe_to_pick(MODULE)),
            len(everything),
            "the filter returned the whole catalog — it is not filtering",
        )

    def test_the_pick_is_a_subset_of_this_module_s_dependencies(self):
        """Selected on the property itself, not on tier or on a hand list."""
        reachable = self.env["sapian.module.catalog"]._reachable_module_names(MODULE)
        catalogued = {entry[1] for entry in SapianModuleCatalog.STANDARD_CATALOG}
        picked = set(self.catalog._filter_safe_to_pick(MODULE).mapped("technical_name"))
        self.assertTrue(picked <= reachable, "picked entries outside the dependency graph")
        self.assertTrue(picked <= catalogued, "picked something that is not a catalog entry")
        self.assertTrue(
            catalogued - picked,
            "the catalog must still offer un-picked apps — that is what makes "
            "it a catalog rather than an install list",
        )

    def test_every_rehearsal_sale_order_has_a_real_salesperson(self):
        """Not OdooBot. The rehearsal tenant is kept for click-through, and the
        Sales app's default `user_id = uid` filter turns an unassigned order
        into an empty list, which Odoo covers with US sample data."""
        salesperson = self.env["sapian.dress.rehearsal"]._rehearsal_salesperson()
        self.assertTrue(salesperson, "no salesperson configured")
        self.assertNotEqual(
            salesperson,
            self.env.ref("base.user_root"),
            "OdooBot is not a salesperson; the Sales app would show nothing",
        )
        self.assertTrue(salesperson.active, "the salesperson must be an active user")
