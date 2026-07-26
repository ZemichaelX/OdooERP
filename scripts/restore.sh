#!/usr/bin/env bash
# Restore a SapianERP tenant from a backup produced by scripts/backup.sh.
# Usage: ./scripts/restore.sh <db_name> <db_dump> [filestore_tgz]
#   e.g. ./scripts/restore.sh sapian_prod \
#          backups/sapian_prod_20260707_153000.dump \
#          backups/sapian_prod_filestore_20260707_153000.tgz
#
# DESTRUCTIVE: drops <db_name> and recreates it from the dump. The Odoo service
# is stopped during the restore and restarted ONLY on success. On any failure
# the script aborts and leaves odoo STOPPED so a half-restored tenant can never
# serve traffic — fix the cause and re-run until the restore succeeds.
set -euo pipefail
# See backup.sh: stop Git Bash mangling container-absolute paths. No-op on Linux.
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="docker compose -f ${REPO_ROOT}/docker/docker-compose.yml"

DB_NAME="${1:?usage: restore.sh <db_name> <db_dump> [filestore_tgz]}"
DB_DUMP="${2:?usage: restore.sh <db_name> <db_dump> [filestore_tgz]}"
FILESTORE_TGZ="${3:-}"

# Validate ALL inputs before touching anything, so a bad argument can never
# abort the script halfway through a destructive phase.
[ -f "${DB_DUMP}" ] || { echo "!! dump not found: ${DB_DUMP}" >&2; exit 1; }
if [ -n "${FILESTORE_TGZ}" ]; then
  [ -f "${FILESTORE_TGZ}" ] || { echo "!! filestore archive not found: ${FILESTORE_TGZ}" >&2; exit 1; }
fi

echo ">> This will DROP and recreate database '${DB_NAME}'."
read -r -p ">> Type the DB name to confirm: " CONFIRM
[ "${CONFIRM}" = "${DB_NAME}" ] || { echo "!! confirmation mismatch; aborting." >&2; exit 1; }

DESTRUCTIVE_PHASE=0
on_exit() {
  status=$?
  if [ "${status}" -ne 0 ] && [ "${DESTRUCTIVE_PHASE}" -eq 1 ]; then
    echo "!! Restore FAILED (exit ${status}). Known state: odoo is STOPPED;" >&2
    echo "!! database '${DB_NAME}' and/or its filestore may be INCOMPLETE." >&2
    echo "!! Do NOT start odoo for this tenant — re-run restore.sh until it succeeds." >&2
  fi
}
trap on_exit EXIT

echo ">> Stopping odoo..."
$COMPOSE stop odoo
DESTRUCTIVE_PHASE=1

echo ">> Dropping and recreating '${DB_NAME}'..."
$COMPOSE exec -T db psql -U odoo -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid<>pg_backend_pid();" >/dev/null
$COMPOSE exec -T db dropdb -U odoo --if-exists "${DB_NAME}"
$COMPOSE exec -T db createdb -U odoo "${DB_NAME}"

echo ">> Restoring database..."
$COMPOSE exec -T db pg_restore -U odoo -d "${DB_NAME}" --no-owner < "${DB_DUMP}"

if [ -n "${FILESTORE_TGZ}" ]; then
  # The odoo service is stopped, so run the filestore phase in a throwaway
  # container from the same service definition — it mounts the same
  # odoo-data volume without needing the service to be up.
  echo ">> Restoring filestore..."
  $COMPOSE run --rm --no-deps -T odoo \
    sh -c "rm -rf /var/lib/odoo/filestore/${DB_NAME} && mkdir -p /var/lib/odoo/filestore"
  $COMPOSE run --rm --no-deps -T odoo \
    tar xzf - -C /var/lib/odoo/filestore < "${FILESTORE_TGZ}"
fi

echo ">> Starting odoo..."
$COMPOSE start odoo
echo ">> Restore complete for '${DB_NAME}'."
