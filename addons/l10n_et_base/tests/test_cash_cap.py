# -*- coding: utf-8 -*-
"""Integration tests for the Proc 1395/2025 daily cash-payment cap check."""

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import L10nEtBaseCommon


@tagged("post_install", "-at_install")
class TestCashCap(L10nEtBaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cash_journal = cls.company_data["default_journal_cash"]

    def _create_cash_payment(self, amount, date="2026-07-01", post=True):
        """An outbound cash payment to the compliant demo supplier."""
        payment = self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.partner_compliant.id,
                "amount": amount,
                "date": date,
                "journal_id": self.cash_journal.id,
                "company_id": self.company.id,
            }
        )
        if post:
            payment.action_post()
        return payment

    def _config(self, date="2026-07-01"):
        return self.env["l10n.et.cash.cap.config"]._get_config(self.company, date)

    def test_config_seeded_on_chart_load(self):
        config = self._config()
        self.assertTrue(config, "Cash-cap config was not seeded on chart load")
        self.assertEqual(config.cap_amount, 30000.0)
        self.assertEqual(config.enforcement, "warn")
        self.assertTrue(config.source_note)

    def test_exactly_at_cap_allowed_silently(self):
        """A single 30,000 cash payment is exactly at the cap: no warning."""
        payment = self._create_cash_payment(30000)
        self.assertEqual(payment.state, "in_process")
        self.assertFalse(
            any("cash cap" in str(message.body) for message in payment.message_ids)
        )

    def test_over_cap_warn_posts_message(self):
        """Default 'warn': the payment posts but carries an audit message."""
        payment = self._create_cash_payment(30000.01)
        self.assertEqual(payment.state, "in_process")
        self.assertTrue(any("cash cap" in str(message.body) for message in payment.message_ids))

    def test_over_cap_block_raises(self):
        """'Block' enforcement refuses to post the breaching payment."""
        self._config().enforcement = "block"
        with self.assertRaises(ValidationError):
            self._create_cash_payment(30000.01)

    def test_daily_accumulation_across_payments(self):
        """15,000 + 20,000 to one party the same day breaches the DAILY cap even
        though each payment alone is under it."""
        self._config().enforcement = "block"
        self._create_cash_payment(15000)
        with self.assertRaises(ValidationError):
            self._create_cash_payment(20000)

    def test_different_days_do_not_accumulate(self):
        """The cap is per day: 25,000 on two different days is fine."""
        self._config().enforcement = "block"
        self._create_cash_payment(25000, date="2026-07-01")
        payment = self._create_cash_payment(25000, date="2026-07-02")
        self.assertEqual(payment.state, "in_process")

    def test_non_cash_journal_not_checked(self):
        """Bank payments are outside the cash cap."""
        self._config().enforcement = "block"
        payment = self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.partner_compliant.id,
                "amount": 100000,
                "date": "2026-07-01",
                "journal_id": self.company_data["default_journal_bank"].id,
                "company_id": self.company.id,
            }
        )
        payment.action_post()
        self.assertEqual(payment.state, "in_process")

    def test_enforcement_off_disables_check(self):
        self._config().enforcement = "off"
        payment = self._create_cash_payment(90000)
        self.assertEqual(payment.state, "in_process")
        self.assertFalse(
            any("cash cap" in str(message.body) for message in payment.message_ids)
        )
