# l10n_et_payroll

Ethiopian PAYE (employment income tax) and pension engine.

## Models
- `l10n.et.paye.band` — effective-dated PAYE bands (config data; add new records for new proclamations).
- `l10n.et.pension.config` — pension rates + optional insurable cap.
- `l10n.et.payslip.compute` — helper that wraps the tested pure-Python calculator.

## Reference calculator & tests
- `reference/et_payroll_calc.py` — pure-Python math, no Odoo dependency.
- `reference/test_et_payroll_calc.py` — 22 golden-value pytest cases (`pytest reference/`).
- `tests/test_payroll_compute.py` — Odoo-level tests over the seeded data.

## Seeded values (2024/25 reform — VERIFY before go-live)
PAYE: tax-free ≤ 2,000; 15/20/25/30/35% with deductions 300/500/850/1350/2050; top 35% > 14,000.
Pension: 7% employee, 11% employer, uncapped by default (citizens only).

## Depends
`base`, `sapian_core`.

## Design note
Rates are configuration, never hard-coded. Changing a future rate (new effective_from record)
does not alter historical payslips — a hard requirement for auditable payroll.
