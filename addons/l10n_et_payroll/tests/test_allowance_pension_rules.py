# -*- coding: utf-8 -*-
"""Accountant-verified (Jul 2026) allowance exemption rules + pension
nationality rules, exercised through the real payslip flow.

Kickoff golden: salary 10,000 + transport 3,000 → exempt 2,200 (lower of
2,200 and 25% = 2,500), taxable 800 → PAYE on 10,800 = 30% × 10,800 − 1,350
= 1,890.
"""

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAllowancePensionRules(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("et")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.ethiopia = cls.env.ref("base.et")
        cls.germany = cls.env.ref("base.de")
        cls.env.user.group_ids += cls.env.ref("hr.group_hr_manager")
        cls.types = {
            t.code: t
            for t in cls.env["l10n.et.allowance.type"].search(
                [("company_id", "=", cls.company.id)]
            )
        }

    def _employee(self, name, wage, country=None, opt_in=False):
        emp = self.env["hr.employee"].create(
            {
                "name": name,
                "company_id": self.company.id,
                "country_id": (country or self.ethiopia).id,
                "l10n_et_pension_opt_in": opt_in,
            }
        )
        emp.version_id.write({"wage": wage})
        return emp

    def _run_for(self, employees):
        run = self.env["l10n.et.payroll.run"].create(
            {
                "company_id": self.company.id,
                "date_from": "2026-07-01",
                "date_to": "2026-07-31",
                "employee_ids": [Command.set(employees.ids)],
            }
        )
        run.action_generate_payslips()
        return run

    def test_default_types_seeded_with_sources(self):
        """The five statutory types exist for the company with source notes."""
        self.assertEqual(
            set(self.types), {"transport", "hardship", "medical", "housing", "position"}
        )
        transport = self.types["transport"]
        self.assertEqual(transport.rule, "capped")
        self.assertEqual(transport.cap_amount, 2200.0)
        self.assertEqual(transport.cap_salary_pct, 0.25)
        for allowance_type in self.types.values():
            self.assertIn("Jul 2026", allowance_type.source_note)
        self.assertEqual(self.types["hardship"].rule, "exempt")
        self.assertEqual(self.types["medical"].rule, "exempt")
        self.assertEqual(self.types["housing"].rule, "taxable")
        self.assertEqual(self.types["position"].rule, "taxable")

    def test_transport_golden_10000_plus_3000(self):
        """THE golden: 10,000 salary + 3,000 transport → PAYE 1,890 on 10,800;
        gross 13,000; pension on basic only; net 10,410."""
        employee = self._employee("Transport Golden", 10000)
        run = self._run_for(employee)
        slip = run.payslip_ids
        self.env["l10n.et.payslip.input"].create(
            {
                "payslip_id": slip.id,
                "name": "Transport July",
                "category": "earning",
                "allowance_type_id": self.types["transport"].id,
                "amount": 3000.0,
            }
        )
        self.assertEqual(slip.taxable_income, 10800.0, "exempt 2,200 / taxable 800")
        self.assertEqual(slip.paye, 1890.0)
        self.assertEqual(slip.gross, 13000.0)
        self.assertEqual(slip.pension_employee, 700.0, "pension on basic only")
        self.assertEqual(slip.net_pay, 13000.0 - 1890.0 - 700.0)

    def test_transport_salary_pct_binds_on_low_salary(self):
        """Salary 8,000: 25% = 2,000 < 2,200 → transport 3,000 splits
        2,000 exempt / 1,000 taxable → taxable income 9,000."""
        employee = self._employee("Pct Binds", 8000)
        run = self._run_for(employee)
        slip = run.payslip_ids
        self.env["l10n.et.payslip.input"].create(
            {
                "payslip_id": slip.id,
                "name": "Transport",
                "category": "earning",
                "allowance_type_id": self.types["transport"].id,
                "amount": 3000.0,
            }
        )
        self.assertEqual(slip.taxable_income, 9000.0)

    def test_exempt_and_taxable_types(self):
        """Hardship is fully exempt; housing is fully taxable — regardless of
        the manual flag (the type wins)."""
        employee = self._employee("Types Win", 10000)
        run = self._run_for(employee)
        slip = run.payslip_ids
        self.env["l10n.et.payslip.input"].create(
            [
                {
                    "payslip_id": slip.id,
                    "name": "Hardship",
                    "category": "earning",
                    "allowance_type_id": self.types["hardship"].id,
                    "taxable": True,  # ignored: the type's rule wins
                    "amount": 1000.0,
                },
                {
                    "payslip_id": slip.id,
                    "name": "Housing",
                    "category": "earning",
                    "allowance_type_id": self.types["housing"].id,
                    "taxable": False,  # ignored: the type's rule wins
                    "amount": 2000.0,
                },
            ]
        )
        self.assertEqual(slip.gross, 13000.0)
        self.assertEqual(slip.taxable_income, 12000.0, "housing taxable, hardship exempt")

    def test_capped_type_requires_a_ceiling(self):
        with self.assertRaises(ValidationError):
            self.env["l10n.et.allowance.type"].create(
                {
                    "name": "Broken",
                    "code": "broken",
                    "company_id": self.company.id,
                    "rule": "capped",
                    "source_note": "test",
                }
            )

    def test_pension_nationality_rules(self):
        """Ethiopian → mandatory; foreign → excluded; foreign of Ethiopian
        origin with opt-in → voluntary contribution applies."""
        ethiopian = self._employee("Abebe Ethiopian", 10000)
        foreign = self._employee("Hans Foreign", 10000, country=self.germany)
        origin_opt_in = self._employee(
            "Sara Diaspora", 10000, country=self.germany, opt_in=True
        )
        run = self._run_for(ethiopian | foreign | origin_opt_in)

        def slip(emp):
            return run.payslip_ids.filtered(lambda s: s.employee_id == emp)

        self.assertTrue(slip(ethiopian).is_citizen)
        self.assertEqual(slip(ethiopian).pension_employee, 700.0)
        self.assertFalse(slip(foreign).is_citizen)
        self.assertEqual(slip(foreign).pension_employee, 0.0)
        self.assertTrue(slip(origin_opt_in).is_citizen)
        self.assertEqual(slip(origin_opt_in).pension_employee, 700.0)
