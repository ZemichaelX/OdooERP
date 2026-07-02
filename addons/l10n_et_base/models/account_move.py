# -*- coding: utf-8 -*-
"""Automatic Ethiopian withholding tax lines on vendor bills.

Design: WHT is recorded ON THE BILL (spec 07 §1 and core `l10n_et` precedent), as
negative-percent purchase taxes crediting the Withholding Tax Payable account —
not via the payment-time `l10n_account_withholding_tax` framework, because the
functional spec requires the WHT liability and the printable certificate at bill
level. The applicability decision (thresholds, punitive rate, foreign digital)
comes from the tested reference calculator with effective-dated configuration.
"""

from odoo import Command, fields, models
from odoo.exceptions import UserError

from ..reference import et_tax_calc


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        """Evaluate and apply Ethiopian WHT on vendor bills before posting.

        Only ``in_invoice`` is automated: refunds copy their taxes from the bill
        they reverse, and the per-transaction thresholds are defined on the
        original supply, not on the credit note.
        """
        for move in self:
            if move.move_type == "in_invoice" and move.state == "draft":
                move._l10n_et_apply_wht()
        return super()._post(soft=soft)

    def _l10n_et_apply_wht(self):
        """(Re-)apply Ethiopian withholding taxes on this draft vendor bill.

        Idempotent: previously applied ET WHT taxes are stripped first, then the
        decision is re-evaluated per supply kind with the configuration effective
        on the invoice date, so editing and re-posting a bill can never stack or
        strand WHT lines.
        """
        self.ensure_one()
        product_lines = self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
        )
        # Strip previous ET WHT taxes (identified by the kind marker).
        for line in product_lines:
            wht_taxes = line.tax_ids.filtered("l10n_et_wht_kind")
            if wht_taxes:
                line.write(
                    {
                        "tax_ids": [Command.unlink(tax.id) for tax in wht_taxes],
                    }
                )

        config = self.env["l10n.et.wht.config"]._get_config(
            self.company_id, self.invoice_date or fields.Date.context_today(self)
        )
        if not config or not product_lines:
            return  # No ET configuration: engine stays inert (non-ET company).

        partner = self.commercial_partner_id
        has_tin = et_tax_calc.validate_tin(partner.l10n_et_tin).valid
        has_licence = partner.l10n_et_has_valid_licence

        # Group lines per supply kind. A foreign-digital partner makes the whole
        # bill foreign digital; otherwise the product type decides per line
        # (service products → services threshold, everything else → goods).
        if partner.l10n_et_is_foreign_digital:
            line_groups = {et_tax_calc.KIND_FOREIGN_DIGITAL: product_lines}
        else:
            line_groups = {}
            for line in product_lines:
                kind = (
                    et_tax_calc.KIND_SERVICE
                    if line.product_id.type == "service"
                    else et_tax_calc.KIND_GOODS
                )
                line_groups.setdefault(kind, self.env["account.move.line"])
                line_groups[kind] |= line

        notes = []
        for kind, lines in line_groups.items():
            # Per-kind base in company currency (ETB), pre-VAT: the thresholds are
            # statutory ETB amounts, so foreign-currency bills are compared after
            # conversion at the invoice date rate (line.balance).
            base = abs(sum(lines.mapped("balance")))
            result = et_tax_calc.compute_wht(
                base,
                kind=kind,
                has_tin=has_tin,
                has_licence=has_licence,
                punitive_respects_thresholds=config.punitive_respects_thresholds,
                rate_standard=config.rate_standard,
                rate_punitive=config.rate_punitive,
                rate_foreign_digital=config.rate_foreign_digital,
                threshold_goods=config.threshold_goods,
                threshold_service=config.threshold_service,
            )
            if not result.applicable:
                continue
            compliant = has_tin and has_licence
            decision = (
                kind if kind == et_tax_calc.KIND_FOREIGN_DIGITAL or compliant else "punitive"
            )
            tax = config._l10n_et_get_tax(decision)
            if not tax:
                raise UserError(
                    self.env._(
                        "No Ethiopian withholding tax record found for '%(kind)s'. "
                        "Set it on the WHT configuration '%(config)s' or reload the "
                        "Ethiopian chart template.",
                        kind=decision,
                        config=config.display_name,
                    )
                )
            lines.write({"tax_ids": [Command.link(tax.id)]})
            notes.append(
                self.env._(
                    "%(tax)s at %(rate).0f%% on a %(kind)s base of %(base).2f "
                    "(threshold %(threshold).0f, supplier %(status)s)",
                    tax=tax.display_name,
                    rate=result.rate * 100,
                    kind=kind,
                    base=base,
                    threshold=result.threshold,
                    status=(
                        self.env._("compliant") if compliant else self.env._("NOT compliant")
                    ),
                )
            )

        if notes:
            # NB: env._()'s first positional parameter is named `source`, so the
            # format kwarg must not be called "source".
            self.message_post(
                body=self.env._(
                    "Ethiopian withholding tax applied automatically: %(details)s. "
                    "Source: %(legal_source)s",
                    details="; ".join(notes),
                    legal_source=config.source_note,
                )
            )

    def _l10n_et_wht_move_lines(self):
        """Return this move's WHT tax lines (used by the certificate report)."""
        self.ensure_one()
        return self.line_ids.filtered(lambda line: line.tax_line_id.l10n_et_wht_kind)
