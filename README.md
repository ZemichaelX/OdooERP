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
   commit if it is missing, deliberately. It is a convenience, not the
   guarantee — **run the verification** in
   [Secrets](#secrets-nothing-real-in-a-tracked-file) and watch it fail, because
   an uninstalled hook is silent.
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

### Two layers, and only one of them is a guarantee

| Layer | Where | Can it be bypassed? |
|---|---|---|
| **CI `Secret scan / gitleaks`** | `.github/workflows/secret-scan.yml`, every push and PR | **No** — once it is a required status check in branch protection. **This is the guarantee.** |
| pre-commit hook | `.githooks/pre-commit`, your clone only | Yes — `--no-verify`, or simply never installing it. **Convenience only.** |

The hook is fast and stops a mistake before it becomes a commit, but it lives in
per-clone git config (`core.hooksPath`), which **cannot be committed**. On a
fresh clone it silently does not exist and its absence is invisible — that is
not a theory, it is how a test `admin_passwd` value got committed on a machine
where the hook had never been installed. Install it, but do not rely on it.

### Install the hook, then verify it actually fires

Run this in Git Bash on Windows, or any POSIX shell. The commit **must fail**.

```bash
winget install gitleaks          # macOS: brew install gitleaks
gitleaks version                 # must print a version, not "command not found"

./scripts/install_hooks.sh
git config --get core.hooksPath  # must print: .githooks

printf '[options]\nadmin_passwd = %s\n' \
  "$(head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-32)" \
  > config/leaktest.conf
git add -f config/leaktest.conf
git commit -m "this must be blocked"
# EXPECT: ">> pre-commit: SECRET DETECTED IN STAGED CHANGES — commit blocked."

git log --oneline -1             # must be UNCHANGED — no new commit
git reset config/leaktest.conf && rm config/leaktest.conf
```

If `git commit` succeeded, the hook is not installed in this clone and the
verification has told you so. Fix it before trusting it.

### Verify the CI check is required (the layer that actually holds)

```bash
gh api repos/ZemichaelX/OdooERP/branches/master/protection \
  --jq '.required_status_checks.contexts'
# EXPECT the list to contain: gitleaks
```

To set it: **Settings → Branches → branch protection rule for `master` →
Require status checks to pass before merging → add `gitleaks`.**

### Never edit a tracked file to hold a per-instance value

The template and the working file used to be the same path
(`config/odoo.conf`), and a live Odoo master password reached git twice as a
result — the second time under a comment reading "LOCAL SECRET, DO NOT COMMIT".
A comment is not a control; the
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
