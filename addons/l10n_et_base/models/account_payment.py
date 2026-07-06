# -*- coding: utf-8 -*-
"""Proc 1395/2025 daily cash-payment cap check on outbound cash payments.

The cap applies to the DAILY TOTAL of cash paid to one party. Whether a breach
warns or blocks is effective-dated configuration (l10n.et.cash.cap.config); the
comparison itself lives in the tested reference calculator.
"""

import hashlib

from odoo import models
from odoo.exceptions import ValidationError

from ..reference import et_tax_calc


def _cash_cap_lock_key(partner_id, on_date):
    """A stable 31-bit key for the (partner, day) advisory lock (A6). SHA-256 of
    ``partner-date`` folded into int4 range so ``pg_advisory_xact_lock`` can pair
    it with the company id."""
    digest = hashlib.sha256(f"{partner_id}-{on_date}".encode()).hexdigest()
    return int(digest, 16) % (2**31)


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
            # Serialize concurrent posts to the SAME party on the SAME day (A6):
            # without this, two payments posted in separate transactions each
            # search only committed priors, neither sees the other, and both
            # slip under the cap (a fail-open on a blocking control). A
            # transaction-scoped advisory lock keyed on (company, party, day)
            # forces the second transaction to wait until the first commits and
            # its payment becomes visible. Auto-released at transaction end;
            # re-entrant within one transaction, so same-batch siblings (handled
            # explicitly below) never self-block.
            self.env.cr.execute(
                "SELECT pg_advisory_xact_lock(%s, %s)",
                (payment.company_id.id, _cash_cap_lock_key(partner.id, payment.date)),
            )
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
            # Also count siblings being posted in THIS batch: they are still
            # draft during the check, so a search on posted state misses them —
            # otherwise two 30,000 payments posted together each see prior 0 and
            # both slip under a 50,000 cap.
            batch_siblings = (self - payment).filtered(
                lambda other, p=payment: other.company_id == p.company_id
                and other.payment_type == "outbound"
                and other.journal_id.type == "cash"
                and other.date == p.date
                and other.partner_id.commercial_partner_id == partner
            )
            prior_total = sum(
                abs(other.amount_company_currency_signed)
                for other in prior_payments | batch_siblings
            )
            amount = abs(payment.amount_company_currency_signed)
            result = et_tax_calc.check_cash_cap(amount, prior_total, cap=config.cap_amount)
            if not result.exceeded:
                continue
            # NB: env._()'s first positional parameter is named `source`, so the
            # format kwarg must not be called "source".
            message = self.env._(
                "Cash payments to %(partner)s on %(date)s total %(total).2f "
                "%(currency)s — %(excess).2f over the %(cap).2f cash cap "
                "(single transaction or same-day aggregate per party — "
                "%(legal_source)s).",
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
