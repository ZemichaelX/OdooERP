# reference/
Pure-Python Ethiopian payroll math with no Odoo dependency.
- `et_payroll_calc.py` — the calculator (single source of truth for PAYE/pension math).
- The fast, standalone golden-value tests live at repo root in `tests_fast/` and run with `pytest`.
  (They load this calculator by file path, so they don't require Odoo.)
The Odoo model `l10n.et.payslip.compute` also loads this file by path.
