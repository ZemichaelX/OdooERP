# CLAUDE.md — SapianERP build repo operating rules

You are building SapianERP: a productized, Ethiopia-localized ERP on Odoo 19 Community + OCA, sold to multiple clients with per-client customization. Specs live in `docs/` (see `docs/00-README.md` index; build order in `docs/10-claude-code-roadmap.md`).

## Non-negotiable rules

1. **Never modify Odoo core or OCA source.** Extend via module inheritance only. New code goes in `addons/sapian_*` or `addons/l10n_et_*`.
2. **Rates are data, never code.** Tax brackets, VAT/WHT rates, pension %, thresholds → effective-dated config records seeded from XML/CSV. Historical documents must stay correct after a rate change. Every rate carries a source note ("Proc 1395/2025, verify before go-live").
3. **Reference calculators first.** All tax/payroll/severance math lives in pure-Python modules under `reference/`, fully covered by `tests_fast/` (pytest, no Odoo needed). Odoo models import them — never duplicate the math.
4. **Per-client isolation.** One database per client. Client-specific config lives in `clients/<name>/manifest.yaml`, applied by `scripts/provision_client.sh` — never hand-edit a tenant for config changes.
5. **Customization ladder:** standardize → configure → extend (generic, catalog-worthy) → custom (rare, client-billed). If asked to build client-specific code, first propose the config/extension alternative.
6. **Least privilege.** Every module ships `security/ir.model.access.csv` + record rules. No `sudo()` without a comment justifying it. Finance/HR data never readable by other roles by default.
7. **Test everything.** Definition of done: `pytest tests_fast/` green; module installs AND uninstalls cleanly on a scratch DB; XML/manifests/CSV validate; demo data included. Golden payroll check: basic 10,000 ETB → PAYE 1,650, pension 700, net 7,650.
8. **Stable identifiers forever.** Never rename fields, models, or external IDs once released (OpenUpgrade survival). Migrations get scripts.
9. **Security defaults:** no secrets in code/DB; webhook signature verification; HTTPS-only assumptions; no sensitive data in logs.
10. **Ethiopian correctness:** Amharic strings translatable (UCS-2-safe for SMS); Ethiopian calendar via `l10n_et_calendar` utilities only (no ad-hoc date math); ETB formatting; TIN validation on partners.

## How to run

- `cp .env.example .env` → set passwords → `docker compose -f docker/docker-compose.yml up -d`
- New tenant: `./scripts/provision_client.sh <name> <package> <vertical>`
- Fast tests: `pytest tests_fast/` · Odoo tests: `--test-enable -i <module>` on scratch DB
- Lint: `ruff check . && pylint --load-plugins=pylint_odoo -e odoolint addons/`

## Current tax facts (seeded; re-verify before each go-live)

- PAYE monthly (Proc 1395/2025, eff. 2025-07-01): 0–2,000 @0% · –4,000 @15% · –7,000 @20% · –10,000 @25% · –14,000 @30% · above @35%
- Pension (Proc 1268/2022): employee 7% / employer 11% of basic
- VAT (Proc 1341/2024): 15%, monthly filing, registration threshold ETB 2M
- WHT (Aug 2025): 3% on goods >20,000 / services >10,000; 30% punitive if no TIN; cash cap 30,000/day/party
- Labor (Proc 1156/2019): OT 1.5/1.75/2/2.5×; leave 16d +1/2yr; probation ≤60 working days

## Backlog

Work epics in order from `docs/10-claude-code-roadmap.md`. When an epic completes, update `CHANGELOG.md` and tick the epic there. When a spec is ambiguous, prefer the DAT proposal behavior (`docs/01-proposal-extraction.md`) — it's the proven client blueprint.
