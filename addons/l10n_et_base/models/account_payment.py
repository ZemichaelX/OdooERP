# -*- coding: utf-8 -*-
"""Proc 1395/2025 daily cash-payment cap check on outbound cash payments.

The cap applies to the DAILY TOTAL of cash paid to one party. Whether a breach
warns or blocks is effective-dated configuration (l10n.et.cash.cap.config); the
comparison itself lives in the tested reference calculator.
"""

from odoo import models
from odoo.exceptions import ValidationError

from ..reference import et_tax_calc


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        """Check the Ethiopian daily cash cap before confirming payments."""
        self._l10n_et_check_cash_cap()
        return super().action_post()

    def _l10n_et_check_cash_cap(self):
        """Flag/block outbound CASH payments whose daily per-party total exceeds
        the configured cap.

        Sums today's already-confirmed cash payments to the same commercial
        entity (any of its contacts), converts amounts to company currency, and
        delegates the comparison to the reference calculator. Enforcement comes
        from the effective-dated configuration: 'block' raises, 'warn' posts an
        audit message on the payment, 'off' does nothing.
        """
        for payment in self:
            if (
                payment.payment_type != "outbound"
                or payment.journal_id.type != "cash"
                or not payment.partner_id
            ):
                continue
            config = self.env["l10n.et.cash.cap.config"]._get_config(
                payment.company_id, payment.date
            )
            if not config or config.enforcement == "off":
                continue
            partner = payment.partner_id.commercial_partner_id
            prior_payments = self.env["account.payment"].search(
                [
                    ("id", "!=", payment.id),
                    ("company_id", "=", payment.company_id.id),
                    ("partner_id", "child_of", partner.id),
                    ("payment_type", "=", "outbound"),
                    ("journal_id.type", "=", "cash"),
                    ("date", "=", payment.date),
                    ("state", "in", ("in_process", "paid")),
                ]
            )
            prior_total = sum(
                abs(prior.amount_company_currency_signed) for prior in prior_payments
            )
            amount = abs(payment.amount_company_currency_signed)
            result = et_tax_calc.check_cash_cap(amount, prior_total, cap=config.cap_amount)
            if not result.exceeded:
                continue
            # NB: env._()'s first positional parameter is named `source`, so the
            # format kwarg must not be called "source".
            message = self.env._(
                "Cash payments to %(partner)s on %(date)s total %(total).2f "
                "%(currency)s — %(excess).2f over the daily cash cap of "
                "%(cap).2f (%(legal_source)s).",
                partner=partner.display_name,
                date=payment.date,
                total=result.total_day,
                currency=payment.company_id.currency_id.name,
                excess=result.excess,
                cap=result.cap,
                legal_source=config.source_note,
            )
            if config.enforcement == "block":
                raise ValidationError(message)
            payment.message_post(body=message)
