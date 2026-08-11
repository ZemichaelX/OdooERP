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
1. `./scripts/install_hooks.sh` — installs the tracked git hooks, including a
   **gitleaks pre-commit secret scan**. Needs gitleaks on PATH
   (`winget install gitleaks` / `brew install gitleaks`); the hook refuses to
   commit if it is missing, deliberately. See
   [Secrets](#secrets-nothing-real-in-a-tracked-file).
2. `cp .env.example docker/.env` and set a `DB_PASSWORD` (compose's project
   directory is `docker/`, so it reads `docker/.env` — a repo-root `.env` is
   ignored).
3. `cp config/odoo.conf.example config/odoo.runtime.conf` — the gitignored
   runtime config that compose mounts. Set `admin_passwd` (replace `CHANGEME`)
   and, if several databases exist, `dbfilter`.
   `scripts/provision_client.sh` does this for you, generating a strong
   per-tenant `admin_passwd` and printing it once for your vault.
4. `docker compose -f docker/docker-compose.yml up -d`
5. Open http://localhost:8069.

## Secrets: nothing real in a tracked file
| File | Tracked? | Holds |
|---|---|---|
| `config/odoo.conf.example` | **yes** | template only — `admin_passwd = CHANGEME`, blank `dbfilter` |
| `config/odoo.runtime.conf` | no (gitignored) | the real `admin_passwd`, the real `dbfilter`. What compose mounts. |
| `.env.example` | **yes** | template only |
| `docker/.env` | no (gitignored) | the real `DB_PASSWORD` |

Never edit a tracked file to hold a per-instance value. The template and the
working file used to be the same path (`config/odoo.conf`), and a live Odoo
master password reached git twice as a result — the second time under a comment
reading "LOCAL SECRET, DO NOT COMMIT". A comment is not a control; the
pre-commit hook is. Background and the rotation checklist:
[`docs/KICKOFF-engineering-hygiene.md`](docs/KICKOFF-engineering-hygiene.md).

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
