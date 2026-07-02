# Kickoff prompt — Epic 3: `l10n_et_base` (copy into Claude Code)

Read CLAUDE.md fully and follow its rules for everything below.

We're building **Epic 3 — `l10n_et_base` (Ethiopian accounting localization)**.
Specs, in priority order:
1. docs/plan-2026/07-ethiopian-localization.md §1 (functional spec — authoritative for tax rules)
2. docs/plan-2026/10-claude-code-roadmap.md Epic 3 (definition of done)
3. docs/02_MODULE_REQUIREMENT_SPECS.md accounting section (task-level detail; where it conflicts with plan-2026 on rates/thresholds, plan-2026 wins)

Context: `sapian_core` and `l10n_et_payroll` are already built and tested (run `pytest tests_fast/` first to confirm 22/22 before touching anything).

Scope for this epic — new addon `addons/l10n_et_base`:
1. Ethiopian chart of accounts template (IFRS-for-SMEs aligned; include VAT receivable/payable, WHT receivable/payable, pension payable, PAYE payable, customs duty clearing).
2. Taxes as effective-dated data: 15% VAT (sale/purchase/zero-rated/exempt) per Proc 1341/2024; fiscal positions.
3. Withholding tax automation: 3% on goods > ETB 20,000 and services > ETB 10,000 per transaction (Aug 2025 rules) as automatic lines on vendor bills; 30% punitive WHT when partner lacks TIN + business licence; 15% code for foreign digital services; printable WHT certificate.
4. Partner compliance fields: TIN (format-validated), VAT reg no., business licence no./expiry (extend what sapian_core already has — check first, don't duplicate).
5. Cash-payment cap: warn/block (configurable) on cash payments > ETB 30,000 to one party per day (Proc 1395/2025).
6. Every rate/threshold: config data with effective dates and a source note field — never hardcoded.

Working method (per CLAUDE.md):
- Start with pure-Python reference calculators in `reference/` (WHT applicability + amount; cash-cap check) with pytest golden tests in `tests_fast/`, hand-computed expected values. Example: vendor bill, goods, ETB 50,000, supplier has TIN → WHT 1,500.
- Then the Odoo models/data/views importing those calculators.
- Security: access rules + record rules for every new model; finance-only visibility.
- Demo data: one demo company, 3 partners (with TIN, without TIN, foreign digital), sample bills/invoices exercising every tax path.

Definition of done (do not stop earlier):
- All tests green (`pytest tests_fast/` — old 22 plus the new ones).
- Module installs AND uninstalls cleanly on a scratch DB.
- Demo flow verified: vendor bill 50k goods → 3% WHT line + correct journal postings; sale invoice → 15% VAT; no-TIN supplier → 30% WHT; trial balance clean.
- XML/manifest/CSV validate; ruff + pylint-odoo clean; no Odoo core/OCA files touched.
- Update CHANGELOG.md and the "Implemented so far" line in CLAUDE.md.

Work step by step; show me the reference-calculator test cases for approval before writing the Odoo layer.
