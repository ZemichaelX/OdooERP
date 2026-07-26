# -*- coding: utf-8 -*-
"""The Ethiopian tax engines must fail LOUD, never open.

Before this fix the WHT and cash-cap configurations were seeded only when chart
'et' loaded, and both engines treated "no configuration" as "do nothing". A
group's second company or a tenant provisioned another way therefore posted
vendor bills with no withholding and cash payments with no cap check — no
error, no warning. These tests pin the three outcomes that replace it:

* in scope + configuration        → the engines act (WHT 1,500 on a 50,000 bill)
* in scope + NO configuration     → UserError naming the company
* in scope + backdated document   → skipped with a chatter note, never blocked
* out of scope (non-Ethiopian)    → inert, silently and correctly
"""

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import L10nEtBaseCommon


@tagged("post_install", "-at_install")
class TestTaxEngineScope(L10nEtBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ethiopia = cls.env.ref("base.et")
        cls.germany = cls.env.ref("base.de")

    # ------------------------------------------------------------------ helpers
    @classmethod
    def _new_company(cls, name, country):
        """A second company in the SAME database, created the ordinary way.

        Chart 'et' is loaded afterwards so the company owns journals and the
        Ethiopian taxes; the configuration seeding under test comes from
        res.company.create, which has already run by then.
        """
        company = cls.env["res.company"].create({"name": name, "country_id": country.id})
        cls.env["account.chart.template"].try_loading("et", company, install_demo=False)
        return company

    def _post_bill(self, company, amount, invoice_date="2026-07-01", partner=None):
        move = (
            self.env["account.move"]
            .with_company(company)
            .create(
                {
                    "move_type": "in_invoice",
                    "partner_id": (partner or self.partner_compliant).id,
                    "invoice_date": invoice_date,
                    "company_id": company.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_goods.id,
                                "quantity": 1,
                                "price_unit": amount,
                                "tax_ids": [],
                            }
                        )
                    ],
                }
            )
        )
        move.action_post()
        return move

    def _cash_journal(self, company):
        """Chart 'et' ships no cash journal, so create one on demand (the same
        gotcha sapian_dress_rehearsal encodes for its cash-cap payment)."""
        journal = self.env["account.journal"].search(
            [("company_id", "=", company.id), ("type", "=", "cash")], limit=1
        )
        return journal or self.env["account.journal"].create(
            {
                "name": "Cash",
                "type": "cash",
                "code": "CSH",
                "company_id": company.id,
            }
        )

    def _post_cash_payment(self, company, amount, date="2026-07-01"):
        payment = (
            self.env["account.payment"]
            .with_company(company)
            .create(
                {
                    "payment_type": "outbound",
                    "partner_type": "supplier",
                    "partner_id": self.partner_compliant.id,
                    "amount": amount,
                    "date": date,
                    "journal_id": self._cash_journal(company).id,
                    "company_id": company.id,
                }
            )
        )
        payment.action_post()
        return payment

    # -------------------------------------------------------------------- tests
    def test_new_ethiopian_company_is_seeded_and_in_scope(self):
        """res.company.create seeds both configs — no chart load needed."""
        company = self.env["res.company"].create(
            {"name": "Second ET Company PLC", "country_id": self.ethiopia.id}
        )
        self.assertTrue(company.l10n_et_tax_engine_active)
        self.assertTrue(
            self.env["l10n.et.wht.config"].search_count([("company_id", "=", company.id)])
        )
        self.assertTrue(
            self.env["l10n.et.cash.cap.config"].search_count([("company_id", "=", company.id)])
        )

    def test_country_set_after_creation_still_lands_in_scope(self):
        """Provisioning creates the company first and sets the country after
        (the onboarding wizard, provision_client.sh) — the scope flag must
        follow, or every wizard-provisioned tenant would be out of scope."""
        company = self.env["res.company"].create({"name": "Late Country PLC"})
        self.assertFalse(company.l10n_et_tax_engine_active)
        company.country_id = self.ethiopia
        self.assertTrue(company.l10n_et_tax_engine_active)

    def test_second_company_withholds_on_goods_bill(self):
        """The golden 50,000 goods bill withholds 3% in a SECOND company."""
        company = self._new_company("Withholding Second PLC", self.ethiopia)
        move = self._post_bill(company, 50000.0)
        wht = self._wht_lines(move)
        self.assertEqual(len(wht), 1)
        self.assertAlmostEqual(abs(wht.balance), 1500.0, places=2)

    def test_second_company_enforces_cash_cap(self):
        """A 60,000 ETB cash payment is caught for the second company."""
        company = self._new_company("Cash Cap Second PLC", self.ethiopia)
        config = self.env["l10n.et.cash.cap.config"]._get_config(company, "2026-07-01")
        config.enforcement = "block"
        with self.assertRaises(UserError):
            self._post_cash_payment(company, 60000.0)

    def test_non_ethiopian_company_stays_inert(self):
        """A non-Ethiopian company in the same database posts normally.

        It even owns the Ethiopian taxes here (the fixture loads chart 'et' for
        journals), which makes the point precisely: scope is decided by the
        company's engine flag, not by whether ET taxes happen to exist.
        """
        company = self._new_company("Auslandische GmbH", self.germany)
        self.assertFalse(company.l10n_et_tax_engine_active)
        move = self._post_bill(company, 50000.0)
        self.assertFalse(self._wht_lines(move))
        self.assertEqual(move.state, "posted")
        payment = self._post_cash_payment(company, 60000.0)
        # Odoo 19 posts payments to 'in_process' (later 'paid' on reconciliation).
        self.assertNotEqual(payment.state, "draft")

    def test_in_scope_company_without_config_raises_naming_company(self):
        """The compliance hole: posting through with no configuration at all."""
        company = self._new_company("Unconfigured ET PLC", self.ethiopia)
        self.env["l10n.et.wht.config"].search([("company_id", "=", company.id)]).unlink()
        with self.assertRaises(UserError) as caught:
            self._post_bill(company, 50000.0)
        self.assertIn("Unconfigured ET PLC", str(caught.exception))

    def test_in_scope_company_without_cash_cap_config_raises(self):
        company = self._new_company("No Cap ET PLC", self.ethiopia)
        self.env["l10n.et.cash.cap.config"].search([("company_id", "=", company.id)]).unlink()
        with self.assertRaises(UserError) as caught:
            self._post_cash_payment(company, 60000.0)
        self.assertIn("No Cap ET PLC", str(caught.exception))

    def test_backdated_bill_skips_withholding_with_chatter_note(self):
        """Historical data migration must not be blocked (bills predating the
        earliest configuration), but every skip must leave a record."""
        company = self._new_company("Backdated ET PLC", self.ethiopia)
        earliest = self.env["l10n.et.wht.config"]._get_config(company, "2026-07-01")
        move = self._post_bill(company, 50000.0, invoice_date="2025-01-15")
        self.assertEqual(move.state, "posted")
        self.assertFalse(self._wht_lines(move))
        bodies = " ".join(move.message_ids.mapped("body"))
        self.assertIn("no withholding was applied", bodies)
        self.assertIn(str(earliest.effective_from), bodies)

    def test_backdated_cash_payment_skips_check_with_chatter_note(self):
        company = self._new_company("Backdated Cash PLC", self.ethiopia)
        config = self.env["l10n.et.cash.cap.config"]._get_config(company, "2026-07-01")
        config.enforcement = "block"
        payment = self._post_cash_payment(company, 60000.0, date="2025-01-15")
        self.assertNotEqual(payment.state, "draft")
        bodies = " ".join(payment.message_ids.mapped("body"))
        self.assertIn("cash cap was not checked", bodies)

    def test_seed_all_companies_fills_in_an_unseeded_company(self):
        """The upgrade path (data <function> + migration) for databases that
        already have companies which never got configuration."""
        company = self._new_company("Legacy Unseeded PLC", self.ethiopia)
        self.env["l10n.et.wht.config"].search([("company_id", "=", company.id)]).unlink()
        self.env["l10n.et.cash.cap.config"].search([("company_id", "=", company.id)]).unlink()

        self.env["l10n.et.wht.config"]._l10n_et_seed_all_companies()
        self.env["l10n.et.cash.cap.config"]._l10n_et_seed_all_companies()

        self.assertTrue(
            self.env["l10n.et.wht.config"].search_count([("company_id", "=", company.id)])
        )
        self.assertTrue(
            self.env["l10n.et.cash.cap.config"].search_count([("company_id", "=", company.id)])
        )
        # And the engine works again end to end.
        move = self._post_bill(company, 50000.0)
        self.assertAlmostEqual(abs(self._wht_lines(move).balance), 1500.0, places=2)
