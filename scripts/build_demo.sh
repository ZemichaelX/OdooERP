#!/usr/bin/env bash
# Build a SapianERP sales-demo database FROM NOTHING, with Odoo demo data OFF.
# Usage: ./scripts/build_demo.sh <db_name> [demo_module]
#   demo_module   defaults to sapian_demo_trader (building materials).
#                 Pass sapian_demo_pharma for the pharma pitch once that
#                 module is converted to the same data/ pattern.
#
# WHY THREE PHASES, and why not just `-i <module> --with-demo`:
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

log_line ">> [1/3] Dropping '${DB_NAME}' and creating it with base only (no demo data)..."
${COMPOSE} exec -T db psql -U odoo -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid<>pg_backend_pid();" >/dev/null
${COMPOSE} exec -T db dropdb -U odoo --if-exists "${DB_NAME}"
${COMPOSE} run --rm odoo odoo -d "${DB_NAME}" -i base --without-demo=all --stop-after-init

log_line ">> [2/3] Setting the company country to Ethiopia (before any chart loads)..."
printf "%s\n" \
  "company = env['res.company'].search([], limit=1)" \
  "company.country_id = env.ref('base.et')" \
  "env.cr.commit()" \
  "print('>> country set to', company.country_id.code)" \
  | ${COMPOSE} run --rm -T odoo odoo shell -d "${DB_NAME}" --no-http

log_line ">> [3/3] Installing ${DEMO_MODULE} (the 'et' chart loads onto that company)..."
${COMPOSE} run --rm odoo odoo -d "${DB_NAME}" -i "${DEMO_MODULE}" \
  --without-demo=all --stop-after-init

log_line ">> Done. Demo database '${DB_NAME}' is ready."
log_line ">>   Log in with admin / admin — deliberate for a local demo."
log_line ">>   Verify: exactly one company, on the 'et' chart:"
log_line ">>     docker compose -f docker/docker-compose.yml exec -T db \\"
log_line ">>       psql -U odoo -d ${DB_NAME} -c 'SELECT name, chart_template FROM res_company;'"
