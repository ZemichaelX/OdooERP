# l10n_et_payroll — Ethiopia Payroll (PAYE & Pension)

Ethiopian payroll engine + monthly workflow. Epic A of the revised backlog
(CLAUDE.md); spec `docs/plan-2026/07-ethiopian-localization.md` §2.

## Workflow (Ethiopian Payroll menu, under Employees)
1. **Payroll Run** (monthly): select employees (defaults to all), *Generate
   Payslips* — basic salary from each employee's `hr.version` wage, citizenship
   from nationality. Odoo 19 Community has no `hr_contract`/`hr_payroll`;
   this module ships its own light payslip models on core `hr`.
2. **Input lines** per payslip: earnings (taxable flag drives the PAYE base —
   overtime is a manual taxable input in v1) and POST-TAX deductions
   (loans/advances).
3. **Confirm & Post** (HR manager): freezes payslips and posts ONE aggregated
   entry to the `PAY` journal — debit gross salaries + employer pension expense;
   credit PAYE payable, pension payable (EE+ER), deductions, net wages.
   Accounts are per-company config, auto-resolved from the Ethiopian chart
   (Epic 3 accounts: PAYE payable 300900, salary payable 300400, …). Idempotent:
   reset-to-draft removes the entry; chatter carries the audit trail.
4. **Exports/prints** on the confirmed run: generic bank salary CSV (name,
   bank, account, net + totals row), branded **payslip PDF** (EN), **PAYE
   monthly declaration** (employee TIN per row) and **pension remittance
   schedule** (POESSA ID per row, EE 7% / ER 11% of basic).

## Statutory identifiers
`hr.employee.l10n_et_tin` (format-validated + normalized via the l10n_et_base
reference calculator) and `l10n_et_pension_id` (POESSA). Optional at entry;
the statutory reports WARN (report banner + chatter) when missing — MoR rejects
filings without them.

## Models
- `l10n.et.paye.band` / `l10n.et.pension.config` — effective-dated rate config;
  a future change is a NEW record, history never moves.
- `l10n.et.payslip.compute` — wraps `reference/et_payroll_calc.py` (pure Python,
  golden-tested in `tests_fast/`); both bands and pension config are selected by
  the payslip period end date.
- `l10n.et.payroll.run` / `l10n.et.payslip` / `l10n.et.payslip.input`.

## Golden values (Proc 1395/2025 — VERIFY before go-live)
Basic 10,000 → PAYE 1,650, pension 700/1,100, net 7,650 (journal: expenses
11,100 = payables 1,650 + 1,800 + 7,650). +2,000 taxable overtime → PAYE 2,250
on 12,000, pension unchanged (basic only), net 9,050.

## Skipped in v1 (deliberate)
Severance, attendance-driven overtime, Amharic payslip, Telebirr payout, leave
accrual. Per-bank transfer formats later.

## Depends
`hr`, `account`, `l10n_et_base`, `sapian_core`.

## Tests
`pytest tests_fast/` (reference goldens) · `--test-enable -i l10n_et_payroll`
on a scratch DB (21 integration tests: goldens, journal, freeze/idempotency,
bank file, report renders, warning paths). Demo: 3 employees on the ET demo
company incl. one missing POESSA ID (warning path), confirmed run + bank file.
