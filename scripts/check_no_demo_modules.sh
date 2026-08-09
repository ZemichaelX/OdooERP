#!/usr/bin/env bash
# Client-provisioning acceptance check: NO demo module may be installed.
# Usage: ./scripts/check_no_demo_modules.sh <db_name>
#
# WHY: sapian_demo_trader used to ship its tenant in demo/, which meant Odoo
# would only create it when demo data was enabled. That was an implicit guard
# against fabricating "Selam General Trading PLC" and a month of invented
# invoices on a real client's books. Moving the tenant to data/ (so the sales
# demo can be built with Odoo's own demo fixtures OFF) gives that guard up, so
# it is replaced with an explicit one rather than with nothing.
#
# Exits non-zero and names the offenders if any demo module is installed.
#
# NOTE: this is ONE assertion of the client-provisioning acceptance check.
# The rest of that check (chart is 'et', currency ETB, TIN set, backups
# scheduled, no placeholder companies, admin_passwd set) is still OUTSTANDING.
set -euo pipefail
export MSYS2_ARG_CONV_EXCL='/var/lib/odoo'

DB_NAME="${1:?usage: check_no_demo_modules.sh <db_name>}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/preflight.sh
. "${REPO_ROOT}/scripts/lib/preflight.sh"
COMPOSE="$(compose_cmd "${REPO_ROOT}/docker/docker-compose.yml")"

if ! require_docker_stack "${COMPOSE}" db; then
  log_error "!! Cannot run the acceptance check — the stack is not available."
  exit 1
fi

# Any module whose technical name marks it as demo content.
INSTALLED="$(${COMPOSE} exec -T db psql -U odoo -d "${DB_NAME}" -t -A -c \
  "SELECT name FROM ir_module_module
    WHERE state = 'installed'
      AND (name LIKE 'sapian_demo%' OR name LIKE '%_demo_%' OR name = 'sapian_dress_rehearsal')
    ORDER BY name;")"

if [ -n "${INSTALLED}" ]; then
  log_error "!! ACCEPTANCE FAILED: demo module(s) installed on client database '${DB_NAME}':"
  printf '%s\n' "${INSTALLED}" | sed 's/^/     /' >&2
  log_error "!! These fabricate companies and transactions. Uninstall them before go-live."
  exit 1
fi

log_line ">> Acceptance OK: no demo module is installed on '${DB_NAME}'."
log_line ">>   (This is one assertion; the full provisioning acceptance check is outstanding.)"
