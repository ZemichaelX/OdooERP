# -*- coding: utf-8 -*-
"""A1 regression: PAYE bands + pension config are seeded PER COMPANY and drive
the payroll math — never a silent hard-coded fallback.

Proves the audit finding is closed:
- every new company owns real, effective-dated PAYE band + pension records;
- with those records removed, the compute helper RAISES instead of silently
  using code constants;
- the seeded 10,000 golden (1,650 / 700 / 7,650) is produced FROM the records,
  demonstrated by editing a band and watching PAYE change accordingly.
"""

from datetime import date

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..models.payslip_compute import _calc


@tagged("post_install", "-at_install", "l10n_et_payroll")
class TestPayrollConfigSeeding(TransactionCase):
    ON_DATE = date(2026, 7, 31)

    def _compute(self, company, **kwargs):
        return (
            self.env["l10n.et.payslip.compute"]
            .with_company(company)
            .compute_for(basic_salary=10000, on_date=self.ON_DATE, **kwargs)
        )

    def test_new_company_is_seeded_with_config(self):
        """res.company.create seeds PAYE bands + pension config immediately."""
        company = self.env["res.company"].create({"name": "A1 Seed Co"})
        bands = self.env["l10n.et.paye.band"].search([("company_id", "=", company.id)])
        pension = self.env["l10n.et.pension.config"].search([("company_id", "=", company.id)])
        # Every KNOWN generation is seeded, not just the current one, so the
        # table can answer "what was the tax in May 2025?" — counted against the
        # generations rather than a literal, which would have to move again the
        # next time a proclamation amends the bands.
        expected_bands = sum(
            len(generation.bands) for generation in _calc.PAYE_BAND_GENERATIONS
        )
        self.assertEqual(len(bands), expected_bands, "every generation is seeded")
        current = bands.filtered(
            lambda band: band.effective_from == _calc.PAYE_1395_2025_EFFECTIVE_FROM
        )
        self.assertEqual(len(current), len(_calc.PAYE_BANDS_1395_2025))
        self.assertTrue(current.filtered("is_top_band"), "the top band is seeded")
        self.assertEqual(len(pension), 1, "one seeded pension config")
        self.assertEqual(pension.employee_rate, 0.07)
        self.assertEqual(pension.employer_rate, 0.11)

    def test_missing_bands_raises_no_silent_fallback(self):
        """With the seeded bands removed, computation FAILS LOUDLY naming the
        company — it must never fall back to DEFAULT_PAYE_BANDS."""
        company = self.env["res.company"].create({"name": "A1 No-Bands Co"})
        self.env["l10n.et.paye.band"].search([("company_id", "=", company.id)]).unlink()
        with self.assertRaisesRegex(UserError, "No Ethiopian PAYE bands"):
            self._compute(company)

    def test_missing_pension_raises_no_silent_fallback(self):
        company = self.env["res.company"].create({"name": "A1 No-Pension Co"})
        self.env["l10n.et.pension.config"].search([("company_id", "=", company.id)]).unlink()
        with self.assertRaisesRegex(UserError, "No Ethiopian pension"):
            self._compute(company)

    def test_golden_10000_comes_from_config_records(self):
        """10,000 → 1,650 / 700 / net 7,650 from the SEEDED records, and editing
        a band changes PAYE — proof the records are read, not the constants."""
        company = self.env["res.company"].create({"name": "A1 Golden Co"})
        result = self._compute(company)
        self.assertAlmostEqual(result["paye"], 1650.0, places=2)
        self.assertAlmostEqual(result["pension_employee"], 700.0, places=2)
        self.assertAlmostEqual(result["net_pay"], 7650.0, places=2)

        # 10,000 taxable falls in the 7,000–10,000 band (rate 0.25, deduction
        # 850 → 1,650). Bump that band's deduction to 950 and PAYE must drop to
        # 1,550: if the compute used the hard-coded constants this would not
        # move.
        band = self.env["l10n.et.paye.band"].search(
            [
                ("company_id", "=", company.id),
                ("lower_bound", "=", 7000.0),
                ("upper_bound", "=", 10000.0),
            ],
            limit=1,
        )
        self.assertTrue(band, "the 7,000–10,000 band is a seeded record")
        band.deduction = 950.0
        edited = self._compute(company)
        self.assertAlmostEqual(
            edited["paye"],
            1550.0,
            places=2,
            msg="editing the config record changed PAYE — records drive the "
            "math, not code constants",
        )

    def test_pension_cap_from_config_is_applied(self):
        """An insurable cap on the pension record limits the pensionable base —
        another proof the config record (not a constant) is read."""
        company = self.env["res.company"].create({"name": "A1 Cap Co"})
        self.env["l10n.et.pension.config"].search(
            [("company_id", "=", company.id)]
        ).insurable_cap = 8000.0
        result = self._compute(company)
        # 7% / 11% of the capped 8,000, not of the 10,000 basic.
        self.assertAlmostEqual(result["pension_employee"], 560.0, places=2)
        self.assertAlmostEqual(result["pension_employer"], 880.0, places=2)
