# -*- coding: utf-8 -*-
"""Integration tests for the Proc 1395/2025 daily cash-payment cap check."""

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from ..models.l10n_et_cash_cap_config import _SUPERSEDED_SOURCE_NOTE
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
        self.assertEqual(config.cap_amount, 50000.0, "Art. 81 Proc 1395/2025 cap")
        self.assertEqual(config.enforcement, "warn")
        self.assertIn("Art. 81", config.source_note)

    def test_exactly_at_cap_allowed_silently(self):
        """A single 50,000 cash payment is exactly at the cap: no warning."""
        payment = self._create_cash_payment(50000)
        self.assertEqual(payment.state, "in_process")
        self.assertFalse(
            any("cash cap" in str(message.body) for message in payment.message_ids)
        )

    def test_over_cap_warn_posts_message(self):
        """Default 'warn': the payment posts but carries an audit message."""
        payment = self._create_cash_payment(50000.01)
        self.assertEqual(payment.state, "in_process")
        self.assertTrue(any("cash cap" in str(message.body) for message in payment.message_ids))

    def test_over_cap_block_raises(self):
        """'Block' enforcement refuses to post the breaching payment."""
        self._config().enforcement = "block"
        with self.assertRaises(ValidationError):
            self._create_cash_payment(50000.01)

    def test_single_transaction_over_cap_blocked(self):
        """Art. 81 also caps the single transaction — one 60,000 cash payment
        is refused even with no prior payments that day."""
        self._config().enforcement = "block"
        with self.assertRaises(ValidationError):
            self._create_cash_payment(60000)

    def test_daily_accumulation_across_payments(self):
        """30,000 + 25,000 to one party the same day breaches the DAILY cap even
        though each payment alone is under it."""
        self._config().enforcement = "block"
        self._create_cash_payment(30000)
        with self.assertRaises(ValidationError):
            self._create_cash_payment(25000)

    def test_different_days_do_not_accumulate(self):
        """The cap is per day: 45,000 on two different days is fine."""
        self._config().enforcement = "block"
        self._create_cash_payment(45000, date="2026-07-01")
        payment = self._create_cash_payment(45000, date="2026-07-02")
        self.assertEqual(payment.state, "in_process")

    def test_batch_post_siblings_counted(self):
        """R1#3/R3#3: two cash payments posted in ONE batch must see each other
        — otherwise each reads prior total 0 and both slip under the cap."""
        self._config().enforcement = "block"
        p1 = self._create_cash_payment(30000, post=False)
        p2 = self._create_cash_payment(30000, post=False)
        with self.assertRaises(ValidationError):
            (p1 | p2).action_post()

    def test_superseded_default_fixed_on_upgrade(self):
        """A config still on the pre-review 30,000 default is corrected by the
        upgrade hook; a customized cap is left alone."""
        config = self._config()
        config.write({"cap_amount": 30000.0, "source_note": _SUPERSEDED_SOURCE_NOTE})
        self.env["l10n.et.cash.cap.config"]._l10n_et_fix_superseded_defaults()
        self.assertEqual(config.cap_amount, 50000.0)
        self.assertIn("Art. 81", config.source_note)
        # Customized: same old cap but the client edited the note — untouched.
        config.write({"cap_amount": 30000.0, "source_note": "Client policy: stricter cap"})
        self.env["l10n.et.cash.cap.config"]._l10n_et_fix_superseded_defaults()
        self.assertEqual(config.cap_amount, 30000.0)

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
