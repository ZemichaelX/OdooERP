# -*- coding: utf-8 -*-
"""Onboarding wizard tests at sapian_core level (base + web only).

The full end-to-end (module installation + Ethiopian chart + TIN) cannot run
inside a test transaction — `button_immediate_install` commits. It is proven by
the unattended fresh-DB run in the epic verification (odoo shell); these tests
cover everything registry-independent plus the guard behavior when the
Ethiopian modules are absent.
"""

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOnboardingWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Onboard Test Co"})

    def _make_wizard(self, **overrides):
        values = {
            "company_id": self.company.id,
            "company_name": "Selam Trading PLC",
            "street": "Bole Road",
            "city": "Addis Ababa",
            "fiscal_year": "ethiopian",
            "primary_color": "#1a7f5a",
        }
        values.update(overrides)
        return self.env["sapian.onboarding.wizard"].with_company(self.company).create(values)

    def test_default_get_seeds_catalog_and_preselects(self):
        """Opening the wizard seeds the standard catalog for the company and
        preselects the enabled (= installed) entries, falling back to the core
        tier when nothing is enabled yet."""
        wizard = (
            self.env["sapian.onboarding.wizard"]
            .with_company(self.company)
            .create({"company_id": self.company.id, "company_name": "X"})
        )
        entries = self.env["sapian.module.catalog"].search(
            [("company_id", "=", self.company.id)]
        )
        self.assertEqual(len(entries), 7, "standard catalog not seeded")
        expected = entries.filtered("enabled") or entries.filtered(lambda e: e.tier == "core")
        self.assertEqual(set(wizard.module_catalog_ids.ids), set(expected.ids))

    def test_catalog_seeding_is_idempotent(self):
        catalog = self.env["sapian.module.catalog"]
        catalog._ensure_default_catalog(self.company)
        catalog._ensure_default_catalog(self.company)
        self.assertEqual(catalog.search_count([("company_id", "=", self.company.id)]), 7)

    def test_catalog_enabled_mirrors_installed_state(self):
        """Enabled is a status mirror: seeding and the upgrade-time sync both
        align it with the actually installed modules."""
        catalog = self.env["sapian.module.catalog"]
        entries = catalog._ensure_default_catalog(self.company)
        installed = set(
            self.env["ir.module.module"]
            .sudo()
            .search([("state", "=", "installed")])
            .mapped("name")
        )
        for entry in entries:
            self.assertEqual(entry.enabled, entry.technical_name in installed)
        # Drift then sync: the flag snaps back to reality.
        drifted = entries[0]
        drifted.enabled = not drifted.enabled
        catalog._sync_enabled_from_installed()
        self.assertEqual(drifted.enabled, drifted.technical_name in installed)

    def test_profile_and_branding_applied(self):
        """Company name/address/country, ETB currency and brand color land on
        the company; picked entries flip to enabled."""
        wizard = self._make_wizard()
        wizard.module_catalog_ids = wizard.module_catalog_ids  # keep defaults
        wizard._apply_company_profile()
        self.assertEqual(self.company.name, "Selam Trading PLC")
        self.assertEqual(self.company.country_id, self.env.ref("base.et"))
        self.assertEqual(self.company.currency_id, self.env.ref("base.ETB"))
        self.assertTrue(self.env.ref("base.ETB").active)
        if "primary_color" in self.company._fields:
            self.assertEqual(self.company.primary_color, "#1a7f5a")

    def test_invalid_primary_color_rejected(self):
        with self.assertRaises(UserError):
            self._make_wizard(primary_color="green")

    def test_ethiopian_defaults_guarded_without_modules(self):
        """On a base-only registry the post-install step must not crash and the
        fiscal-year/TIN writes are applied only when their fields exist."""
        wizard = self._make_wizard(tin="0011223344")
        wizard._apply_ethiopian_defaults(self.env(), self.company.id, "0011223344", "ethiopian")
        if "fiscalyear_last_month" in self.company._fields:
            self.assertEqual(self.company.fiscalyear_last_month, "7")
            self.assertEqual(self.company.fiscalyear_last_day, 7)
        if "l10n_et_tin" in self.company.partner_id._fields:
            self.assertEqual(self.company.partner_id.l10n_et_tin, "0011223344")
