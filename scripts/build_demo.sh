#!/usr/bin/env bash
# Build a SapianERP sales-demo database FROM NOTHING, with Odoo demo data OFF.
# Usage: ./scripts/build_demo.sh <db_name> [demo_module]
#   demo_module   defaults to sapian_demo_trader (building materials).
#                 Pass sapian_demo_pharma for the pharma pitch once that
#                 module is converted to the same data/ pattern.
#
# WHY IT IS PHASED, and why not just `-i <module> --with-demo`:
# Odoo's own demo data ships US placeholder companies and a website bound to
# the wrong company — a prospect must never see a US company list in software
# sold as Ethiopian. So demo data stays OFF and the tenant ships as module
# data. But with demo off the single company is created on generic_coa with
# country US, and Odoo does NOT allow switching charts afterwards; so the
# country must be set BEFORE the accounting modules install. That is the same
# two-phase dance scripts/provision_client.sh does for a real client — which
# means recording the demo is a rehearsal of the actual deployment.
#
# Result: exactly ONE company, Selam General Trading PLC, on the 'et' chart.
set -euo pipefail
export MSYS2_ARG_CONV_EXCL='/var/lib/odoo'

DB_NAME="${1:?usage: build_demo.sh <db_name> [demo_module]}"
DEMO_MODULE="${2:-sapian_demo_trader}"
# The provisioning model each demo module exposes.
case "${DEMO_MODULE}" in
  sapian_demo_trader) DEMO_MODEL="sapian.demo.trader" ;;
  sapian_demo_pharma) DEMO_MODEL="sapian.demo.pharma" ;;
  *) echo "!! Unknown demo module '${DEMO_MODULE}'." >&2; exit 1 ;;
esac
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/preflight.sh
. "${REPO_ROOT}/scripts/lib/preflight.sh"
COMPOSE="$(compose_cmd "${REPO_ROOT}/docker/docker-compose.yml")"

if [ ! -f "${REPO_ROOT}/config/odoo.runtime.conf" ]; then
  log_line ">> Creating config/odoo.runtime.conf from the template."
  cp "${REPO_ROOT}/config/odoo.conf" "${REPO_ROOT}/config/odoo.runtime.conf"
fi
if ! require_docker_stack "${COMPOSE}" db; then
  log_error "!! Aborting — the stack is not available."
  exit 1
fi

log_line ">> [1/5] Dropping '${DB_NAME}' and creating it with base only (no demo data)..."
${COMPOSE} exec -T db psql -U odoo -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid<>pg_backend_pid();" >/dev/null
${COMPOSE} exec -T db dropdb -U odoo --if-exists "${DB_NAME}"
${COMPOSE} run --rm odoo odoo -d "${DB_NAME}" -i base --without-demo=all --stop-after-init

log_line ">> [2/5] Setting the company country to Ethiopia (before any chart loads)..."
printf "%s\n" \
  "company = env['res.company'].search([], limit=1)" \
  "company.country_id = env.ref('base.et')" \
  "env.cr.commit()" \
  "print('>> country set to', company.country_id.code)" \
  | ${COMPOSE} run --rm -T odoo odoo shell -d "${DB_NAME}" --no-http

log_line ">> [3/5] Installing ${DEMO_MODULE} (the 'et' chart loads onto that company)..."
${COMPOSE} run --rm odoo odoo -d "${DB_NAME}" -i "${DEMO_MODULE}" \
  --without-demo=all --stop-after-init

# Provisioning runs AFTER the install completes, never during it: module data
# loads mid-install, and a company charted at that point collides with the
# account module's end-of-load chart auto-install hook.
log_line ">> [4/5] Provisioning the tenant (adopting the existing company)..."
printf "%s\n" \
  "company = env['${DEMO_MODEL}']._provision_demo_tenant(adopt_existing=True)" \
  "env.cr.commit()" \
  "print('>> provisioned:', company.name, '| chart:', company.chart_template)" \
  | ${COMPOSE} run --rm -T odoo odoo shell -d "${DB_NAME}" --no-http

# The acceptance checks, asserted rather than suggested. Both of these have
# silently regressed before: the company list picked up Odoo's US placeholders,
# and the UoM setting was left off so the quintal/bag conversion — the demo's
# headline moment — was invisible on every form. A build that fails either is
# not a demo you can record, so it exits non-zero here instead of on camera.
log_line ">> [5/5] Verifying the built database..."
VERIFY_OUT="$(printf "%s\n" \
  "companies = env['res.company'].search([('name', '!=', False)])" \
  "print('CHECK companies=%d' % len(companies))" \
  "print('CHECK charts=%s' % ','.join(c.chart_template or 'none' for c in companies))" \
  "print('CHECK names=%s' % ' | '.join(companies.mapped('name')))" \
  "on = env.ref('uom.group_uom') in env.ref('base.group_user').all_implied_ids" \
  "print('CHECK group_uom=%s' % on)" \
  | ${COMPOSE} run --rm -T odoo odoo shell -d "${DB_NAME}" --no-http 2>&1 || true)"

printf '%s\n' "${VERIFY_OUT}" | grep -E '^CHECK ' || true
verify_failed=0
check() {  # check <grep pattern> <what went wrong>
  if ! printf '%s\n' "${VERIFY_OUT}" | grep -q "$1"; then
    log_error "!! $2"
    verify_failed=1
  fi
}
check '^CHECK companies=1$' \
  "Expected exactly ONE active company. A prospect must never see a US"$'\n'"   placeholder in the company switcher — see the CHECK names line above."
check '^CHECK charts=et$' \
  "The company is not on the Ethiopian chart 'et'. Odoo cannot switch charts"$'\n'"   afterwards, so this database has to be rebuilt, not repaired."
check '^CHECK group_uom=True$' \
  "Settings > Inventory > 'Units of Measure & Packagings' is OFF, so Odoo"$'\n'"   hides every unit field and the quintal->bag conversion is invisible."
if [ "${verify_failed}" -ne 0 ]; then
  log_error "!! Demo database '${DB_NAME}' FAILED verification — do not record it."
  exit 1
fi

log_line ">> Done. Demo database '${DB_NAME}' is ready and verified."
log_line ">>   Log in with admin / admin — deliberate for a local demo."
