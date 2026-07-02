# Changelog

All notable changes to SapianERP. Epics per `docs/plan-2026/10-claude-code-roadmap.md`.

## [Unreleased]

### Epic A — `l10n_et_payroll` payroll workflow completion ✅ (2026-07-02)
- Monthly payroll runs on core `hr` (Odoo 19 has no hr_contract/hr_payroll:
  own light models; wages from `hr.version`): payslip generation, manual input
  lines (taxable/exempt earnings, post-tax deductions), freeze-on-confirm.
- Aggregated payroll journal posting to an auto-created `PAY` journal with
  per-company account config auto-resolved from the Ethiopian chart (golden:
  10,000 basic → expenses 11,100; payables 1,650 PAYE + 1,800 pension + 7,650
  net; balanced). Idempotent confirm/reset with chatter audit trail.
- Employee statutory identifiers: TIN (validated via the l10n_et_base reference
  calculator) + POESSA pension ID; statutory reports warn on missing ones.
- Generic bank salary transfer CSV (name/bank/account/net + totals row).
- QWeb reports (EN, `web.external_layout`): payslip PDF, PAYE monthly
  declaration (TIN per row), pension remittance schedule (POESSA ID per row).
- Fixed en route: pension config now effective-date filtered in the compute
  helper (was latest-record); Odoo 19 `_sql_constraints` → `models.Constraint`
  (payroll + sapian_core); sapian_core deprecated `name_get` removed; manifests
  cleaned. 21 integration tests; demo payroll (3 employees, one missing pension
  ID for the warning path) on the ET demo company; install/uninstall/reinstall
  verified.

### Epic 3 — `l10n_et_base` Ethiopian accounting localization ✅ (2026-07-02)
- Reference calculators (`addons/l10n_et_base/reference/et_tax_calc.py`, pure Python,
  no Odoo): WHT applicability + amount (3% goods > 20k / services > 10k, punitive 30%,
  foreign digital 15%, `punitive_respects_thresholds` config flag), Proc 1395/2025
  daily cash-payment cap check, Ethiopian TIN format validation. 45 golden tests in
  `tests_fast/`, adversarially verified (mutation-tested coverage).
- Odoo module extending the core `l10n_et` chart template `'et'`:
  - CoA additions (PAYE Payable 300900, Customs Duty Clearing 230200) and
    account-type fixes for the mistyped core VAT/WHT accounts (3006/3007/3008 →
    liabilities, 2212/2213/2214 → assets) — core files untouched.
  - Automatic WHT lines on vendor bills at post time, driven by the effective-dated
    `l10n.et.wht.config` (rates/thresholds/punitive-gating flag, source notes) and
    the reference calculator; idempotent on re-post; chatter audit trail.
  - Zero-rated + VAT-exempt fiscal positions mapped onto the core 15% VAT taxes.
  - `l10n.et.cash.cap.config` (warn/block/off) enforcing the ETB 30,000/party/day
    cash cap on outbound cash payments.
  - Partner compliance fields (TIN validated + normalized via the reference calc,
    VAT reg. no., business licence no./expiry, foreign-digital flag, Amharic name);
    commercial-field propagation; finance-only partner tab.
  - Printable WHT certificate and Ethiopian VAT invoice (QWeb, EN).
  - Security: access rules + multi-company record rules for both config models.
  - Demo data: 3 partners + posted documents exercising every tax path.
  - 33 Odoo integration tests (golden postings, effective dating, cash cap,
    reports); verified install → uninstall → reinstall on a scratch DB with demo;
    trial balance clean.
- Tooling: `ruff.toml`, `pyproject.toml` (black, line-length 96), `.pylintrc`
  (pylint-odoo 10/10); fixed `config/odoo.conf` inline comments that broke the
  Odoo 19 config parser; payroll import-order lint fixes.

### Revised build order (July 2026, token-conscious — supersedes docs epic order)
Next: Epic A payroll workflow completion → Epic B statutory reports slice →
Epic C thin onboarding + demo tenant. Verticals, payments/SMS, e-invoice,
Ethiopian calendar, full theme, BI deferred until a client signs.

## Baseline (Epics 0–2, ported from the starter repo)

- Repo skeleton: `docker/`, `config/`, `scripts/`, `data-templates/`, `docs/`
  (incl. the July-2026 `docs/plan-2026/` master-planning package).
- `sapian_core`: module catalog model + company defaults (S0-4/S1-1/S1-2).
- `l10n_et_payroll`: PAYE (Proc 1395/2025) + pension (Proc 1268/2022) engine with
  effective-dated rate models and a pure-Python reference calculator — 22 golden
  tests (basic 10,000 → PAYE 1,650 / pension 700 / net 7,650).
