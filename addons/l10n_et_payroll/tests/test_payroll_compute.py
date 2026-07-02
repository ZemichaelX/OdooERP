# -*- coding: utf-8 -*-
"""Odoo-level test: the compute helper reads seeded bands/pension and matches goldens."""

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "l10n_et_payroll")
class TestPayrollCompute(TransactionCase):
    def test_compute_10000(self):
        res = self.env["l10n.et.payslip.compute"].compute_for(basic_salary=10000)
        self.assertAlmostEqual(res["paye"], 1650.0, places=2)
        self.assertAlmostEqual(res["pension_employee"], 700.0, places=2)
        self.assertAlmostEqual(res["net_pay"], 7650.0, places=2)

    def test_compute_taxfree(self):
        res = self.env["l10n.et.payslip.compute"].compute_for(basic_salary=2000)
        self.assertEqual(res["paye"], 0.0)
        self.assertAlmostEqual(res["net_pay"], 1860.0, places=2)

    def test_non_citizen_no_pension(self):
        res = self.env["l10n.et.payslip.compute"].compute_for(
            basic_salary=10000, is_citizen=False
        )
        self.assertEqual(res["pension_employee"], 0.0)
