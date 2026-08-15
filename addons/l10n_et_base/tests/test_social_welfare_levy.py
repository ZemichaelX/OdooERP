# -*- coding: utf-8 -*-
"""The social welfare levy on an actual vendor bill.

Council of Ministers Regulation No. 519/2022: 3% of the aggregate CIF value of
imported goods, effective 6 August 2022.

The arithmetic is NOT retested here — it has golden tests in tests_fast/ that
run without Odoo (CLAUDE.md rule 10). What is tested here is everything the
ledger adds on top, and in particular the two properties that are easy to get
exactly backwards:

  * the levy lands in a COST account, not a receivable — a competitor's
    published guide calls this an "Import Advance Income Tax ... offset against
    income tax", which would capitalise 3% of every consignment as an asset
    that is never recovered;
  * the levy is IN ADDITION to the other import taxes and enters NOBODY's base
    — not VAT's, not excise's, not surtax's.

The second one is asserted against posted amounts on a real move rather than
against the tax's configuration flags, because a flag is a claim about what
Odoo will do and the move is what it did.
"""

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.l10n_et_base.reference import et_tax_calc

from .common import L10nEtBaseCommon

CIF = 1_250_000.00
LEVY = 37_500.00  # 3% of CIF
VAT_ON_CIF = 187_500.00  # 15% of CIF — NOT 15% of (CIF + levy), which is 193,125


@tagged("post_install", "-at_install")
class TestSocialWelfareLevy(L10nEtBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["l10n.et.social.welfare.levy.config"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.levy_tax = cls.config._l10n_et_get_tax()

    # ---- the configuration -------------------------------------------------

    def test_the_regulation_is_seeded_per_company(self):
        self.assertTrue(self.config, "no levy configuration was seeded")
        self.assertEqual(str(self.config.effective_from), "2022-08-06")
        self.assertEqual(self.config.rate, 0.03)
        self.assertEqual(self.config.company_id, self.company)
        self.assertIn("519/2022", self.config.source_note)

    def test_a_rate_change_must_be_a_new_record(self):
        """CLAUDE.md rule 4, enforced by the overlap constraint: a second
        open-ended configuration for the same company is refused, so the only
        way to change the rate is a dated record that leaves history alone."""
        with self.assertRaises(ValidationError):
            self.env["l10n.et.social.welfare.levy.config"].create(
                {
                    "company_id": self.company.id,
                    "effective_from": "2026-01-01",
                    "rate": 0.05,
                    "source_note": "hypothetical future rate",
                }
            )
        # …and a properly CLOSED period accepts the successor.
        self.config.effective_to = "2025-12-31"
        successor = self.env["l10n.et.social.welfare.levy.config"].create(
            {
                "company_id": self.company.id,
                "effective_from": "2026-01-01",
                "rate": 0.05,
                "source_note": "hypothetical future rate",
            }
        )
        self.assertEqual(
            self.env["l10n.et.social.welfare.levy.config"]
            ._get_config(self.company, "2023-05-01")
            .rate,
            0.03,
            "an import cleared in 2023 must still compute at the 2022 rate",
        )
        self.assertEqual(successor.rate, 0.05)

    def test_the_model_delegates_the_arithmetic(self):
        """The Odoo layer must not do tax maths of its own."""
        result = self.config.compute_levy(CIF)
        self.assertEqual(result.amount, LEVY)
        self.assertEqual(result.amount, et_tax_calc.compute_social_welfare_levy(CIF).amount)
        self.assertFalse(result.creditable)

    def test_the_commencement_date_gates_the_engine(self):
        before = self.config.compute_levy(
            CIF, on_date=self.config.effective_from.replace(day=5)
        )
        self.assertFalse(before.applicable)
        self.assertEqual(before.amount, 0.0)

    @classmethod
    def _exemption_codes(cls):
        return sorted(et_tax_calc.SWL_EXEMPTIONS)

    def test_the_exempt_path(self):
        for code in self._exemption_codes():
            result = self.config.compute_levy(CIF, exemption=code)
            self.assertFalse(result.applicable, code)
            self.assertEqual(result.amount, 0.0, code)

    # ---- the tax record ----------------------------------------------------

    def test_the_levy_posts_to_a_cost_account_and_not_a_receivable(self):
        """THE TREATMENT. Read off the tax's own repartition, not off a comment."""
        self.assertTrue(self.levy_tax, "the levy tax is not on this company's chart")
        accounts = self.levy_tax.invoice_repartition_line_ids.account_id
        self.assertTrue(accounts, "the levy tax posts nowhere at all")
        for account in accounts:
            self.assertEqual(
                account.account_type,
                "expense",
                "the levy must be a COST of the import; %s is a %s account"
                % (account.display_name, account.account_type),
            )
            self.assertNotIn(
                account.account_type,
                ("asset_receivable", "asset_current"),
                "booking the levy as an asset capitalises 3% of every "
                "consignment as a receivable that will never be recovered",
            )

    def test_the_configuration_refuses_a_tax_that_books_the_levy_as_an_asset(self):
        """The competitor's reading, attempted, and refused.

        This is the discrimination proof for the constraint: build the exact
        wiring the "Import Advance Income Tax, offset against income tax"
        description implies — a 3% tax posting to a receivable — and point the
        configuration at it.
        """
        receivable = self.company_data["default_account_receivable"]
        wrong_tax = self.env["account.tax"].create(
            {
                "name": "3% Import Advance Income Tax (the wrong reading)",
                "amount": 3.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "company_id": self.company.id,
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create({"repartition_type": "tax", "account_id": receivable.id}),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create({"repartition_type": "tax", "account_id": receivable.id}),
                ],
            }
        )
        with self.assertRaises(ValidationError) as caught:
            self.config.tax_id = wrong_tax
        self.assertIn("not creditable", str(caught.exception).lower())

    def test_the_levy_enters_nobody_else_s_base(self):
        """Configuration side of the property, on the tax record itself.

        `include_base_amount` is Odoo's "this tax is added to the base of the
        taxes after it"; `is_base_affected` is "the taxes before this one are
        added to MY base". The levy needs BOTH False: its base is the CIF value
        alone, and it forms no part of anyone else's.
        """
        self.assertFalse(
            self.levy_tax.include_base_amount,
            "the levy would be added to the base of taxes sequenced after it",
        )
        self.assertFalse(
            self.levy_tax.is_base_affected,
            "the levy would be computed on CIF plus whatever preceded it",
        )

    # ---- on a posted bill --------------------------------------------------

    def _without_wht(self):
        """Take the withholding engine out of the picture for this test.

        NOT cosmetic. The domestic WHT rate is 3% and the levy is 3%, so on a
        bill carrying both they are numerically EQUAL at every CIF value —
        `amount_total` came out at exactly the untaxed amount and looked like
        "the levy was not added" when what actually happened was
        `CIF + levy - WHT`. A test that cannot tell those two apart is not a
        test, so the levy is asserted in isolation here and the interaction is
        asserted separately at 30%, where the numbers cannot coincide.
        """
        self.company.l10n_et_tax_engine_active = False

    def _import_bill(self, taxes, price_unit=CIF, invoice_date="2026-07-01", partner=None):
        """A vendor bill for one imported consignment carrying ``taxes``."""
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": (partner or self.partner_compliant).id,
                "invoice_date": invoice_date,
                "company_id": self.company.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_goods.id,
                            "quantity": 1,
                            "price_unit": price_unit,
                            "tax_ids": [Command.set(taxes.ids)],
                        }
                    )
                ],
            }
        )
        move.action_post()
        return move

    def _tax_amount(self, move, tax):
        lines = move.line_ids.filtered(lambda line: line.tax_line_id == tax)
        return sum(lines.mapped("balance"))

    def test_the_levy_on_a_sample_import(self):
        self._without_wht()
        move = self._import_bill(self.levy_tax)
        self.assertEqual(move.amount_untaxed, CIF)
        self.assertEqual(self._tax_amount(move, self.levy_tax), LEVY)
        self.assertEqual(
            move.amount_total,
            CIF + LEVY,
            "the levy is IN ADDITION to the value of the goods",
        )

    def test_the_levy_lands_in_the_cost_account_on_the_posted_move(self):
        """Not "the tax is configured to post to an expense account" — where
        the money actually went on a posted journal entry."""
        self._without_wht()
        move = self._import_bill(self.levy_tax)
        levy_lines = move.line_ids.filtered(lambda line: line.tax_line_id == self.levy_tax)
        self.assertTrue(levy_lines)
        for line in levy_lines:
            self.assertEqual(line.account_id.account_type, "expense")
            self.assertEqual(line.balance, LEVY, "debit — a cost, not a credit")
        receivables = move.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        self.assertFalse(
            receivables,
            "an import bill carrying the levy must create NO receivable: %s"
            % receivables.mapped("account_id.display_name"),
        )

    def test_the_levy_does_not_enter_the_base_of_vat(self):
        """VAT is 15% of CIF, not 15% of (CIF + levy).

        Both taxes on one line, which is how an import bill actually carries
        them. If the levy entered VAT's base, VAT would come out at 193,125.00
        instead of 187,500.00 — a 5,625.00 overstatement on one consignment.
        """
        vat = self.env["account.tax"].search(
            [
                *self.env["account.tax"]._check_company_domain(self.company),
                ("type_tax_use", "=", "purchase"),
                ("amount", "=", 15.0),
                ("amount_type", "=", "percent"),
            ],
            limit=1,
        )
        self.assertTrue(vat, "no 15% purchase VAT on this company's chart")
        self._without_wht()
        move = self._import_bill(self.levy_tax | vat)
        self.assertEqual(self._tax_amount(move, self.levy_tax), LEVY)
        self.assertEqual(
            self._tax_amount(move, vat),
            VAT_ON_CIF,
            "VAT was computed on a base that includes the levy",
        )
        self.assertNotEqual(self._tax_amount(move, vat), 193_125.00)

    def test_the_levy_does_not_enter_the_base_of_an_excise_or_surtax(self):
        """The same property against a tax that COULD have pulled it in.

        This module ships no excise or surtax, so one is built here in the
        shape those take — a percent tax whose base IS affected by preceding
        taxes (`is_base_affected=True`, which is Odoo's default and the setting
        an excise would carry). Sequenced after the levy, it still computes on
        CIF alone, because the levy declares `include_base_amount = False`.

        Without that flag this test would read 3% higher, which is the whole
        point of asserting it against an amount rather than a checkbox.
        """
        self._without_wht()
        excise_like = self.env["account.tax"].create(
            {
                "name": "10% Excise (stand-in)",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "sequence": 100,  # after the levy
                "is_base_affected": True,  # would absorb a preceding tax that offered itself
                "company_id": self.company.id,
            }
        )
        move = self._import_bill(self.levy_tax | excise_like)
        self.assertEqual(self._tax_amount(move, self.levy_tax), LEVY)
        self.assertEqual(
            self._tax_amount(move, excise_like),
            125_000.00,
            "the excise stand-in was computed on CIF + levy (128,750) instead of CIF",
        )

    def test_the_levy_check_discriminates(self):
        """Prove the base assertions can fail, by building the tax that fails them.

        A levy that DID offer itself to later taxes is created and sequenced the
        same way; the excise stand-in then reads 128,750.00. If this test cannot
        produce that number, the test above is asserting nothing.
        """
        self._without_wht()
        leaky_levy = self.env["account.tax"].create(
            {
                "name": "3% levy that wrongly enters other bases",
                "amount": 3.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "sequence": 1,
                "include_base_amount": True,  # the defect
                "company_id": self.company.id,
            }
        )
        excise_like = self.env["account.tax"].create(
            {
                "name": "10% Excise (stand-in)",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "sequence": 100,
                "is_base_affected": True,
                "company_id": self.company.id,
            }
        )
        move = self._import_bill(leaky_levy | excise_like)
        self.assertEqual(
            self._tax_amount(move, excise_like),
            128_750.00,
            "the leaky levy did not inflate the excise base, so the assertion "
            "in the test above proves nothing",
        )

    def test_the_levy_is_in_addition_to_withholding(self):
        """WHT and the levy are different things and both land, separately.

        Asserted against a supplier with no TIN, so withholding is 30% and the
        levy 3% — the two numbers cannot coincide, which is exactly the trap
        this test exists to avoid. At the domestic 3% rate they are equal at
        every CIF value, and a bill carrying both nets to the untaxed amount.

        Note the SIGNS: the levy is a debit to a cost account (money the
        importer spends), withholding is a credit to a payable (money the
        importer holds back from the supplier and owes the authority). They
        move in opposite directions and are not each other's opposite.
        """
        self.assertTrue(self.company.l10n_et_tax_engine_active, "engine must be on here")
        move = self._import_bill(self.levy_tax, partner=self.partner_no_tin)

        levy_lines = move.line_ids.filtered(lambda line: line.tax_line_id == self.levy_tax)
        self.assertEqual(sum(levy_lines.mapped("balance")), LEVY)
        self.assertEqual(levy_lines.account_id.account_type, "expense")

        wht_lines = move.line_ids.filtered(lambda line: line.tax_line_id.l10n_et_wht_kind)
        self.assertTrue(wht_lines, "the punitive WHT did not apply")
        self.assertEqual(sum(wht_lines.mapped("balance")), -CIF * 0.30)
        self.assertEqual(wht_lines.account_id.account_type, "liability_current")
