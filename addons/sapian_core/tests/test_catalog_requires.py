# -*- coding: utf-8 -*-
"""The catalog's `requires` relation: product bundles, and the loop that must not exist.

WHY THIS EXISTS AT ALL
----------------------
`l10n_et_payroll` deliberately does not depend on `sapian_core` — a dependency
audit found zero code references, and declaring it put the SapianERP app tile in
every database that installed payroll. But "the Payroll+HR product ships with
the SapianERP core" is still true; it is a PACKAGING fact, not a code fact. It
lives here, in per-company data a consultant can change, instead of in a
manifest that forces one answer on every client.

So this file guards the thing that replaced a manifest dependency. If it stops
holding, a payroll client silently gets no core.
"""

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCatalogRequires(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Requires Co"})
        cls.entries = cls.env["sapian.module.catalog"]._ensure_default_catalog(cls.company)

    def _entry(self, technical_name):
        entry = self.entries.filtered(lambda e: e.technical_name == technical_name)
        self.assertTrue(entry, "no catalog entry for %s" % technical_name)
        return entry

    # ---- the bundle itself --------------------------------------------------

    def test_payroll_includes_core_in_the_seeded_catalog(self):
        """The one product bundle we actually ship."""
        payroll = self._entry("l10n_et_payroll")
        core = self._entry("sapian_core")
        self.assertIn(
            core,
            payroll.requires_ids,
            "Ethiopian Payroll must include SapianERP Core. This is the bundle "
            "that replaced l10n_et_payroll's manifest dependency on sapian_core "
            "— if it is gone, a payroll-only client gets no core.",
        )

    def test_seeding_is_idempotent(self):
        """Re-running the seed must not duplicate the link."""
        payroll = self._entry("l10n_et_payroll")
        before = payroll.requires_ids.ids
        self.env["sapian.module.catalog"]._ensure_default_catalog(self.company)
        self.assertEqual(
            sorted(payroll.requires_ids.ids),
            sorted(before),
            "re-seeding changed the requires links; it must be idempotent",
        )

    # ---- the closure --------------------------------------------------------

    def test_expand_requires_is_transitive(self):
        """Two hops, not one — the customer bought the whole chain."""
        a, b, c = (
            self.env["sapian.module.catalog"].create(
                {
                    "name": "Chain %s" % label,
                    "technical_name": "chain_%s" % label,
                    "company_id": self.company.id,
                }
            )
            for label in ("a", "b", "c")
        )
        a.requires_ids = [Command.link(b.id)]
        b.requires_ids = [Command.link(c.id)]
        self.assertEqual(a._expand_requires(), a | b | c)

    # ---- the wizard honours it ---------------------------------------------

    def test_wizard_auto_ticks_a_required_entry(self):
        """Picking Ethiopian Payroll alone must yield Payroll AND Core.

        Asserted through the ONCHANGE, which is what a consultant actually
        triggers by clicking, rather than by calling the model helper directly —
        the helper being right proves nothing about the screen.
        """
        payroll = self._entry("l10n_et_payroll")
        core = self._entry("sapian_core")

        wizard = self.env["sapian.onboarding.wizard"].create(
            {"company_id": self.company.id, "company_name": self.company.name}
        )
        wizard.module_catalog_ids = [Command.set(payroll.ids)]
        self.assertNotIn(
            core,
            wizard.module_catalog_ids,
            "precondition: core must NOT be picked yet, or this test proves nothing",
        )

        wizard._onchange_module_catalog_ids()

        self.assertIn(
            core,
            wizard.module_catalog_ids,
            "picking Ethiopian Payroll did not auto-tick SapianERP Core",
        )
        self.assertIn(payroll, wizard.module_catalog_ids, "the picked module was lost")

    def test_wizard_expansion_is_not_only_an_onchange(self):
        """A wizard driven without the UI still gets the bundle.

        An onchange fires in the browser and nowhere else. Provisioning scripts,
        RPC callers and tests never trigger one, and the bundle is not optional
        just because nobody clicked.
        """
        payroll = self._entry("l10n_et_payroll")
        core = self._entry("sapian_core")
        wizard = self.env["sapian.onboarding.wizard"].create(
            {"company_id": self.company.id, "company_name": self.company.name}
        )
        # Set the field the way a script would: no onchange anywhere.
        wizard.module_catalog_ids = [Command.set(payroll.ids)]
        expanded = wizard.module_catalog_ids._expand_requires()
        self.assertIn(
            core,
            expanded,
            "action_apply expands through _expand_requires; if this fails, the "
            "non-UI path installs payroll without core",
        )

    # ---- the loop -----------------------------------------------------------

    def test_a_direct_cycle_is_rejected(self):
        first = self.env["sapian.module.catalog"].create(
            {"name": "Loop A", "technical_name": "loop_a", "company_id": self.company.id}
        )
        second = self.env["sapian.module.catalog"].create(
            {"name": "Loop B", "technical_name": "loop_b", "company_id": self.company.id}
        )
        first.requires_ids = [Command.link(second.id)]
        with self.assertRaises(ValidationError):
            second.requires_ids = [Command.link(first.id)]

    def test_an_indirect_cycle_is_rejected(self):
        """Three hops. A constraint that only catches A->B->A is half a guard."""
        a, b, c = (
            self.env["sapian.module.catalog"].create(
                {
                    "name": "Ring %s" % label,
                    "technical_name": "ring_%s" % label,
                    "company_id": self.company.id,
                }
            )
            for label in ("a", "b", "c")
        )
        a.requires_ids = [Command.link(b.id)]
        b.requires_ids = [Command.link(c.id)]
        with self.assertRaises(ValidationError):
            c.requires_ids = [Command.link(a.id)]

    def test_self_reference_is_rejected(self):
        entry = self.env["sapian.module.catalog"].create(
            {"name": "Selfy", "technical_name": "selfy", "company_id": self.company.id}
        )
        with self.assertRaises(ValidationError):
            entry.requires_ids = [Command.link(entry.id)]

    def test_the_cycle_guard_discriminates(self):
        """The same shape WITHOUT a loop must be accepted.

        A constraint that rejected everything would pass all three tests above
        while making the field useless. This builds the identical diamond —
        a->b, a->c, b->d, c->d — which is not a cycle, and asserts it is allowed
        and that the closure resolves. If this fails, the guard is not detecting
        loops, it is just refusing links.
        """
        a, b, c, d = (
            self.env["sapian.module.catalog"].create(
                {
                    "name": "Diamond %s" % label,
                    "technical_name": "diamond_%s" % label,
                    "company_id": self.company.id,
                }
            )
            for label in ("a", "b", "c", "d")
        )
        a.requires_ids = [Command.link(b.id), Command.link(c.id)]
        b.requires_ids = [Command.link(d.id)]
        c.requires_ids = [Command.link(d.id)]
        self.assertEqual(
            a._expand_requires(),
            a | b | c | d,
            "a diamond is not a cycle; the guard must allow it and the closure "
            "must visit d exactly once",
        )

    def test_requires_cannot_cross_companies(self):
        other_company = self.env["res.company"].create({"name": "Other Co"})
        other_entries = self.env["sapian.module.catalog"]._ensure_default_catalog(other_company)
        mine = self._entry("sapian_core")
        theirs = other_entries.filtered(lambda e: e.technical_name == "sapian_core")
        with self.assertRaises(ValidationError):
            mine.requires_ids = [Command.link(theirs.id)]
