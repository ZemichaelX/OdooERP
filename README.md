# SapianERP

A configurable, Ethiopian-localized ERP product built on **Odoo 19 Community**,
delivered per-client via Docker (with a path to multi-tenant SaaS). Full master
planning package in `docs/` (vision, module specs, architecture, market
playbook, customization guide). Operating rules: `CLAUDE.md`.

## Status — BUILD PHASE COMPLETE (next: sales)
- `addons/sapian_core` — product base: onboarding wizard (company profile, TIN,
  fiscal year, ETB, logo + primary color, module picks), module catalog.
- `addons/l10n_et_base` — Ethiopian accounting: extends core chart 'et'; 15%
  VAT + fiscal positions; WHT automation (3% goods/services thresholds, 30%
  punitive, 15% foreign digital, effective-dated config); cash cap; partner
  TIN/licence compliance; ET invoice + WHT certificate PDFs.
- `addons/l10n_et_payroll` — PAYE (Proc 1395/2025) + pension (Proc 1268/2022)
  engine; monthly batch runs, journal posting, bank CSV, payslip PDF, PAYE
  declaration + pension remittance schedule.
- `addons/l10n_et_reports` — monthly VAT declaration + WHT summary, live from
  posted moves with GL tie-out warnings, PDF + CSV.
- `addons/sapian_demo_trader` — the sales-demo tenant (see below).
- Accountant-review PDF samples in `samples/` (rendered from the demo tenant).

## Quick start
1. `cp .env.example docker/.env` and set a `DB_PASSWORD` (compose's project
   directory is `docker/`, so it reads `docker/.env` — a repo-root `.env` is
   ignored).
2. `cp config/odoo.conf config/odoo.runtime.conf` — the gitignored runtime
   config that compose mounts (`scripts/provision_client.sh` creates it and
   adds a per-tenant `admin_passwd`).
3. `docker compose -f docker/docker-compose.yml up -d`
4. Open http://localhost:8069.

## The demo (sales demo + local testing)
Build the sales-demo database **from nothing**, with Odoo's own demo data OFF:

```bash
./scripts/build_demo.sh demo_materials
```

Result: exactly ONE company — **Selam General Trading PLC**, a building-materials
and hardware trader on the Ethiopian chart, with a full July-2026 month (VAT,
3%/30%/15% withholding, payroll). Log in with `admin` / `admin`.

The command takes the demo module as a second argument
(`./scripts/build_demo.sh demo_pharma sapian_demo_pharma`) once that module is
converted to the same pattern.

Prices live in one marked block —
`addons/sapian_demo_trader/models/demo_catalogue.py` — and several are
**unverified placeholders**. Check them before recording anything.

Full recording guide: `docs/11-demo-video-kit.md`.

## Tests
- Fast reference goldens (no Odoo): `pytest tests_fast/`
- Full integration (Odoo 19 + Postgres, ~90 tests):
  `docker compose -f docker/docker-compose.yml run --rm odoo odoo -d scratch -i sapian_demo_trader --with-demo --test-enable --test-tags /sapian_core,/l10n_et_base,/l10n_et_payroll,/l10n_et_reports,/sapian_demo_trader --stop-after-init`
- CI (GitHub Actions): lint (ruff/black/pylint-odoo), fast goldens and XML/CSV/
  manifest validation on every push; the integration suite runs locally.

## Important
All tax/PAYE/pension/WHT figures are **effective-dated configuration data**
(never code) seeded from the July-2026 rules. **Re-verify every rate against
the Ministry of Revenue before any go-live** — updates are config changes, not
releases.
