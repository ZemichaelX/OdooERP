# -*- coding: utf-8 -*-
"""Seeded PAYE generations select by the payslip's date, in the ORM.

The fast goldens (tests_fast/test_et_paye_generations.py) pin the calculator;
this pins the records: a company must own BOTH generations, each with the right
window, so `get_active_bands` and therefore `compute_for` return the schedule
that was actually in force on the payslip's period end.

Boundary: Income Tax (Amendment) Proclamation 1395/2025 commenced 8 July 2025.
7 July 2025 is still Proclamation 979/2016.
"""

from datetime import date

from odoo.tests import TransactionCase, tagged

from ..models.payslip_compute import _calc


@tagged("post_install", "-at_install", "l10n_et_payroll")
class TestPayeGenerations(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Generations Test PLC"})

    def _compute_paye(self, on_date, basic_salary=6000.0):
        return (
            self.env["l10n.et.payslip.compute"]
            .with_company(self.company)
            .compute_for(basic_salary=basic_salary, on_date=on_date)["paye"]
        )

    def test_both_generations_are_seeded(self):
        bands = self.env["l10n.et.paye.band"].search([("company_id", "=", self.company.id)])
        starts = set(bands.mapped("effective_from"))
        self.assertEqual(
            starts,
            {_calc.PAYE_979_2016_EFFECTIVE_FROM, _calc.PAYE_1395_2025_EFFECTIVE_FROM},
        )
        self.assertEqual(
            len(bands), len(_calc.PAYE_BANDS_979_2016) + len(_calc.PAYE_BANDS_1395_2025)
        )

    def test_old_generation_is_closed_the_day_before_the_new_one(self):
        old = self.env["l10n.et.paye.band"].search(
            [
                ("company_id", "=", self.company.id),
                ("effective_from", "=", _calc.PAYE_979_2016_EFFECTIVE_FROM),
            ]
        )
        self.assertTrue(old)
        self.assertEqual(set(old.mapped("effective_to")), {date(2025, 7, 7)})
        current = self.env["l10n.et.paye.band"].search(
            [
                ("company_id", "=", self.company.id),
                ("effective_from", "=", _calc.PAYE_1395_2025_EFFECTIVE_FROM),
            ]
        )
        self.assertFalse(any(current.mapped("effective_to")))

    def test_june_2025_payslip_uses_979_2016(self):
        """The defect: this used to compute 700 on bands that did not exist yet."""
        self.assertAlmostEqual(self._compute_paye(date(2025, 6, 30)), 935.0, places=2)

    def test_august_2025_payslip_uses_1395_2025(self):
        self.assertAlmostEqual(self._compute_paye(date(2025, 8, 31)), 700.0, places=2)

    def test_boundary_inclusive_and_exclusive(self):
        """8 July 2025 is the new regime; 7 July 2025 is still the old one."""
        self.assertAlmostEqual(self._compute_paye(date(2025, 7, 8)), 700.0, places=2)
        self.assertAlmostEqual(self._compute_paye(date(2025, 7, 7)), 935.0, places=2)

    def test_pension_commencement_is_the_phase_in_completion(self):
        """Proc 715/2011 art. 57 reaches 7%/11% only in year four (8 Jul 2014)."""
        config = self.env["l10n.et.pension.config"].search(
            [("company_id", "=", self.company.id)]
        )
        self.assertEqual(config.effective_from, date(2014, 7, 8))
        self.assertAlmostEqual(config.employee_rate, 0.07, places=6)
        self.assertAlmostEqual(config.employer_rate, 0.11, places=6)
