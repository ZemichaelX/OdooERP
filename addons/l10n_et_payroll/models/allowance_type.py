# -*- coding: utf-8 -*-
"""Allowance types with their PAYE exemption rules (accountant-verified Jul 2026).

Each type carries WHICH exemption rule applies — fully taxable, fully exempt,
or exempt up to a ceiling (the transport rule: lower of an absolute monthly
amount or a fraction of basic salary; the excess is taxable). The split math
lives in the reference calculator; payslip input lines linked to a type get
their exempt/taxable portions computed automatically instead of relying on a
hand-set flag."""

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .payslip_compute import _calc


class L10nEtAllowanceType(models.Model):
    _name = "l10n.et.allowance.type"
    _description = "Ethiopian Allowance Type (PAYE exemption rule)"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        help="Stable technical code (e.g. 'transport') used by seeding and tests.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        help="Exemption rules are configuration per company; never shared.",
    )
    rule = fields.Selection(
        selection=[
            ("taxable", "Fully Taxable"),
            ("exempt", "Fully Exempt"),
            ("capped", "Exempt Up To Ceiling"),
        ],
        required=True,
        default="taxable",
        help="'Exempt Up To Ceiling' exempts the allowance up to the LOWER of "
        "the configured ceilings and taxes the excess (the transport rule).",
    )
    cap_amount = fields.Float(
        string="Ceiling (ETB/month)",
        help="Absolute monthly exemption ceiling. 0 = no absolute ceiling.",
    )
    cap_salary_pct = fields.Float(
        string="Ceiling (% of Basic Salary)",
        help="Exemption ceiling as a fraction of basic salary (0.25 = 25%). "
        "0 = no salary-based ceiling.",
    )
    source_note = fields.Char(
        required=True,
        help="Legal source of the rule. Re-verify before each payroll go-live.",
    )
    active = fields.Boolean(default=True)

    _code_unique_per_company = models.Constraint(
        "unique(code, company_id)",
        "Allowance type codes must be unique per company.",
    )

    @api.constrains("rule", "cap_amount", "cap_salary_pct")
    def _check_ceilings(self):
        """A capped rule without any ceiling would silently mean fully exempt."""
        for allowance_type in self:
            if allowance_type.cap_amount < 0 or allowance_type.cap_salary_pct < 0:
                raise ValidationError(
                    self.env._("Allowance exemption ceilings cannot be negative.")
                )
            if allowance_type.rule == "capped" and not (
                allowance_type.cap_amount or allowance_type.cap_salary_pct
            ):
                raise ValidationError(
                    self.env._(
                        "An 'Exempt Up To Ceiling' allowance type needs at least "
                        "one ceiling (absolute amount or %% of salary)."
                    )
                )

    def split(self, amount, basic_salary):
        """Return ``(exempt, taxable)`` for ``amount`` under this type's rule.

        Delegates the ceiling math to the reference calculator (CLAUDE.md
        rule #10 — never re-implement)."""
        self.ensure_one()
        if self.rule == "taxable":
            return 0.0, amount
        if self.rule == "exempt":
            return amount, 0.0
        return _calc.split_allowance(
            amount,
            basic_salary,
            cap_amount=self.cap_amount or None,
            cap_salary_pct=self.cap_salary_pct or None,
        )

    @api.model
    def _l10n_et_ensure_defaults(self, company):
        """Seed the accountant-verified (Jul 2026) statutory allowance types
        for ``company``; existing codes are never overwritten (a client may
        have tuned them)."""
        verified = "Accountant-verified Jul 2026 (Proc 1395/2025 + MoR directives)"
        defaults = [
            {
                "name": "Transport Allowance",
                "code": "transport",
                "rule": "capped",
                "cap_amount": _calc.DEFAULT_TRANSPORT_EXEMPT_CAP,
                "cap_salary_pct": _calc.DEFAULT_TRANSPORT_EXEMPT_SALARY_PCT,
                "source_note": f"Exempt up to the LOWER of ETB 2,200/month or 25% of "
                f"basic salary; excess taxable. {verified}.",
            },
            {
                "name": "Hardship Allowance",
                "code": "hardship",
                "rule": "exempt",
                "source_note": f"Hardship/desert allowance exempt. {verified}.",
            },
            {
                "name": "Medical Reimbursement",
                "code": "medical",
                "rule": "exempt",
                "source_note": f"Actual medical costs incurred are exempt. {verified}.",
            },
            {
                "name": "Housing Allowance",
                "code": "housing",
                "rule": "taxable",
                "source_note": f"Housing allowance is taxable by default. {verified}.",
            },
            {
                "name": "Position Allowance",
                "code": "position",
                "rule": "taxable",
                "source_note": f"Position/responsibility allowance is taxable. {verified}.",
            },
        ]
        existing_codes = set(
            self.with_context(active_test=False)
            .search([("company_id", "=", company.id)])
            .mapped("code")
        )
        to_create = [
            dict(vals, company_id=company.id)
            for vals in defaults
            if vals["code"] not in existing_codes
        ]
        if to_create:
            self.create(to_create)
        return True

    @api.model
    def _l10n_et_seed_all_companies(self):
        """Data-file hook (install + every upgrade): seed every active company."""
        for company in self.env["res.company"].search([("active", "=", True)]):
            self._l10n_et_ensure_defaults(company)
        return True
