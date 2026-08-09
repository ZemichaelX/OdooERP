# -*- coding: utf-8 -*-
"""The 19.0.5.0.0 re-audit must see EVERY company, and say what it left behind.

19.0.4.0.0 iterated ``res.company.search([("active", "=", True)])``, so an
archived company was never examined — neither corrected nor warned about. Found
on a live database, where a placeholder company archived during demo
provisioning kept bands dated 2024-07-01 while the migration reported success.

Two properties are pinned here: an archived company IS corrected, and the
post-condition reports anything still carrying the superseded date.
"""

import importlib.util
import os
import sys
from datetime import date

from odoo.tests import TransactionCase, tagged

from ..models.payslip_compute import _calc

_MIGRATION = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "migrations",
    "19.0.5.0.0",
    "post-migrate.py",
)
_spec = importlib.util.spec_from_file_location("l10n_et_payroll_reaudit", _MIGRATION)
_migration = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _migration
_spec.loader.exec_module(_migration)

WRONG = date(2024, 7, 1)


@tagged("post_install", "-at_install", "l10n_et_payroll")
class TestCommencementPostCondition(TransactionCase):
    def _legacy_company(self, name, archived=False, customised=False):
        """A company whose rows look like a pre-19.0.4.0.0 database."""
        company = self.env["res.company"].create({"name": name})
        bands = self.env["l10n.et.paye.band"].with_context(active_test=False)
        bands.search(
            [
                ("company_id", "=", company.id),
                ("effective_from", "=", _calc.PAYE_979_2016_EFFECTIVE_FROM),
            ]
        ).unlink()
        rows = bands.search([("company_id", "=", company.id)])
        rows.write({"effective_from": WRONG, "effective_to": False})
        self.env["l10n.et.pension.config"].with_context(active_test=False).search(
            [("company_id", "=", company.id)]
        ).write({"effective_from": WRONG})
        if customised:
            rows.filtered(lambda band: band.lower_bound == 4000.0).deduction = 555.0
        if archived:
            company.active = False
        return company

    def _bands(self, company):
        return (
            self.env["l10n.et.paye.band"]
            .with_context(active_test=False)
            .search([("company_id", "=", company.id)])
        )

    def test_archived_company_is_corrected_not_merely_warned(self):
        """The regression: an archived company used to be invisible."""
        company = self._legacy_company("Archived Legacy PLC", archived=True)
        self.assertFalse(company.active)
        self.assertEqual(set(self._bands(company).mapped("effective_from")), {WRONG})

        _migration._correct_bands(self.env, _calc.PAYE_1395_2025_EFFECTIVE_FROM)
        _migration._correct_pension(self.env)

        starts = set(self._bands(company).mapped("effective_from"))
        self.assertEqual(
            starts,
            {_calc.PAYE_979_2016_EFFECTIVE_FROM, _calc.PAYE_1395_2025_EFFECTIVE_FROM},
            "an archived company must be corrected, not skipped",
        )
        pension = (
            self.env["l10n.et.pension.config"]
            .with_context(active_test=False)
            .search([("company_id", "=", company.id)])
        )
        self.assertEqual(pension.effective_from, date(2014, 7, 8))

    def test_post_condition_is_clean_after_a_full_correction(self):
        self._legacy_company("Clean Sweep PLC")
        _migration._correct_bands(self.env, _calc.PAYE_1395_2025_EFFECTIVE_FROM)
        _migration._correct_pension(self.env)
        leftovers = _migration._assert_nothing_left_behind(
            self.env, _calc.PAYE_1395_2025_EFFECTIVE_FROM
        )
        self.assertEqual(leftovers, [])

    def test_post_condition_reports_a_deliberate_leftover(self):
        """A customised set is legitimately not corrected — but never silent."""
        company = self._legacy_company(
            "Customised Archived PLC", archived=True, customised=True
        )
        _migration._correct_bands(self.env, _calc.PAYE_1395_2025_EFFECTIVE_FROM)
        leftovers = _migration._assert_nothing_left_behind(
            self.env, _calc.PAYE_1395_2025_EFFECTIVE_FROM
        )
        reported = [
            (label, reported_company, count)
            for label, reported_company, count, _wrong in leftovers
        ]
        self.assertIn(("PAYE band", company, len(_calc.PAYE_BANDS_1395_2025)), reported)
        # ...and the customised row itself is untouched.
        deductions = (
            self._bands(company)
            .filtered(lambda band: band.lower_bound == 4000.0)
            .mapped("deduction")
        )
        self.assertEqual(deductions, [555.0])
