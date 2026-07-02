# -*- coding: utf-8 -*-
"""Ethiopian statutory identifiers on the employee.

Both are optional at data entry (hiring shouldn't block on paperwork) but the
statutory reports warn when they are missing: MoR rejects PAYE declarations
without employee TINs and pension remittances without POESSA registration
numbers. TIN format validation reuses the l10n_et_base reference calculator —
the single source of truth (CLAUDE.md rule #10).
"""

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.l10n_et_base.reference import et_tax_calc


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_et_tin = fields.Char(
        string="TIN (Ethiopia)",
        size=13,
        groups="hr.group_hr_user",
        help="Employee's Ministry of Revenue Taxpayer Identification Number "
        "(10 digits). Required on the PAYE monthly declaration — filings "
        "without it are rejected.",
    )
    l10n_et_pension_id = fields.Char(
        string="Pension ID (POESSA)",
        groups="hr.group_hr_user",
        help="POESSA pension registration number. Required per employee on the "
        "pension remittance schedule — filings without it are rejected.",
    )

    @api.constrains("l10n_et_tin")
    def _check_l10n_et_tin(self):
        """Reject TINs that fail the reference format validation."""
        for employee in self:
            if employee.l10n_et_tin:
                result = et_tax_calc.validate_tin(employee.l10n_et_tin)
                if not result.valid:
                    raise ValidationError(
                        self.env._(
                            "Invalid Ethiopian TIN %(tin)r for %(employee)s: " "%(reason)s",
                            tin=employee.l10n_et_tin,
                            employee=employee.name,
                            reason=result.reason,
                        )
                    )

    @api.model
    def _l10n_et_normalize_tin_vals(self, vals):
        """Normalize a TIN in ``vals`` in place when valid (separators stripped);
        invalid values are left for the constraint to report verbatim."""
        tin = vals.get("l10n_et_tin")
        if tin:
            result = et_tax_calc.validate_tin(tin)
            if result.valid:
                vals["l10n_et_tin"] = result.normalized

    @api.model_create_multi
    def create(self, vals_list):
        """Store TINs normalized regardless of how they were typed/imported."""
        for vals in vals_list:
            self._l10n_et_normalize_tin_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        """Store TINs normalized regardless of how they were typed/imported."""
        self._l10n_et_normalize_tin_vals(vals)
        return super().write(vals)
