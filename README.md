# SapianERP

A configurable, Ethiopian-localized ERP product built on **Odoo 19 Community**, delivered
per-client via Docker (with a path to multi-tenant SaaS). See the full master planning
package in `docs/` for the vision, module specs, architecture, market playbook, and
customization guide.

## Status
Starter scaffold. Implemented:
- `addons/sapian_core` — company setup + module catalog/toggle (product base).
- `addons/l10n_et_payroll` — Ethiopian PAYE + pension engine (configurable, effective-dated,
  with a tested pure-Python reference calculator).

## Quick start
1. `cp .env.example .env` and set a `DB_PASSWORD`.
2. `docker compose -f docker/docker-compose.yml up -d`
3. Open http://localhost:8069, create the `sapianerp` database, install the modules.

## Tests
Fast payroll math (no Odoo): `pip install pytest && pytest addons/l10n_et_payroll/reference/`

## Layout
See `CLAUDE.md`.

## Important
Tax/PAYE/pension seed values reflect Ethiopia's 2024/25 reform (tax-free ≤ ETB 2,000,
top 35% above ETB 14,000; pension 7% employee / 11% employer). **Re-verify against the
Ministry of Revenue before any payroll go-live** — the values are configuration data with
effective dates and are meant to be updated without code changes.
