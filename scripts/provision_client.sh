#!/usr/bin/env bash
# Provision a new client instance: create the DB and install the base + chosen
# modules, landing the company on the Ethiopian chart of accounts ('et').
# Usage: ./scripts/provision_client.sh <db_name> [comma,separated,modules]
#
# Why two phases (this is the fix for the "company ends up on generic_coa" bug):
# Odoo auto-loads a chart of accounts the moment `account` installs, choosing by
# the company's COUNTRY. A brand-new DB's company has no country, so it gets the
# generic chart — and Odoo won't let you switch charts afterwards. So we:
#   1. create the DB with `base` only (no accounting, no chart yet),
#   2. set the company country to Ethiopia,
#   3. install the real modules — now `account` sees an Ethiopian company and
#      loads the 'et' chart automatically, and the l10n_et_* loaders apply the
#      payroll accounts / WHT / VAT defaults on top.
# The chosen MODULES must include an Ethiopian localization (l10n_et_*) so the
# 'et' chart template exists; the default set does.
set -euo pipefail

DB_NAME="${1:?usage: provision_client.sh <db_name> [modules]}"
MODULES="${2:-sapian_core,l10n_et_base,l10n_et_payroll,l10n_et_reports}"
COUNTRY_CODE="${SAPIAN_COUNTRY:-et}"   # override for a non-Ethiopian tenant
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/preflight.sh
. "${REPO_ROOT}/scripts/lib/preflight.sh"

# The -f path goes through compose_cmd so the HOST path is in the form
# docker can open on Windows (see scripts/lib/preflight.sh).
COMPOSE="$(compose_cmd "${REPO_ROOT}/docker/docker-compose.yml")"

# --- Master password (admin_passwd) --------------------------------------------
# The database-manager master password protects DB create/drop/backup. It must
# be a strong, per-tenant secret and must NEVER be committed (A10). Secrets go
# in config/odoo.runtime.conf — the gitignored copy of the tracked template
# config/odoo.conf.example — which is what docker-compose actually mounts.
# ensure_runtime_conf creates that copy, replaces the CHANGEME placeholder with
# a generated secret, prints it ONCE for the vault, and refuses to continue if
# the placeholder survives. Idempotent: a real password from an earlier
# provision is left untouched.
if ! ensure_runtime_conf "${REPO_ROOT}"; then
  echo "!! Aborting — config/odoo.runtime.conf is not usable." >&2
  exit 1
fi

echo ">> Provisioning client DB: ${DB_NAME}"
echo ">> Country: ${COUNTRY_CODE} | Modules: ${MODULES}"

# --- Phase 1: create the DB with base only (no chart yet) ----------------------
echo ">> [1/3] Creating database (base only)..."
$COMPOSE run --rm odoo \
  odoo -d "${DB_NAME}" -i base --without-demo=all --stop-after-init

# --- Phase 2: set the company country BEFORE any chart loads -------------------
echo ">> [2/3] Setting company country to '${COUNTRY_CODE}'..."
printf "%s\n" \
  "company = env['res.company'].search([], limit=1)" \
  "country = env['res.country'].search([('code','=','${COUNTRY_CODE}'.upper())], limit=1)" \
  "company.country_id = country" \
  "env.cr.commit()" \
  "print('>> country set to', company.country_id.code)" \
  | $COMPOSE run --rm -T odoo odoo shell -d "${DB_NAME}" --no-http

# --- Phase 3: install the real modules — 'et' chart auto-loads now -------------
echo ">> [3/3] Installing modules (chart auto-loads for the country)..."
$COMPOSE run --rm odoo \
  odoo -d "${DB_NAME}" -i "${MODULES}" --without-demo=all --stop-after-init

# Acceptance: a client database must carry no demo content. This replaces the
# implicit guard that existed while the demo tenant shipped in demo/ (see
# scripts/check_no_demo_modules.sh). The rest of the acceptance check is
# still outstanding.
echo ">> Acceptance check: no demo modules on the new database..."
"${REPO_ROOT}/scripts/check_no_demo_modules.sh" "${DB_NAME}"

echo ">> Done. The company is on the '${COUNTRY_CODE}' chart of accounts."
echo ">> Next: configure company profile/branding/roles via the onboarding wizard,"
echo ">>       set the fiscal year + TIN, import master data from data-templates/,"
echo ">>       and confirm scripts/backup.sh is scheduled."
