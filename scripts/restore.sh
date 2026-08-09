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

# shellcheck source=scripts/lib/preflight.sh
. "${REPO_ROOT}/scripts/lib/preflight.sh"

# Pre-flight: compose mounts config/odoo.runtime.conf (gitignored, absent on a
# fresh clone). If a compose command ever ran before the file existed, docker
# created that path as a DIRECTORY — detect both cases so the documented path
# can't strand the operator on a confusing mount error.
if [ -d "${REPO_ROOT}/config/odoo.runtime.conf" ]; then
  echo "!! ${REPO_ROOT}/config/odoo.runtime.conf is a DIRECTORY (docker created it before the file existed)." >&2
  echo "!! Remove it (rm -rf config/odoo.runtime.conf) and re-run — it will be recreated from config/odoo.conf." >&2
  exit 1
fi
if [ ! -f "${REPO_ROOT}/config/odoo.runtime.conf" ]; then
  echo ">> Creating config/odoo.runtime.conf from the template."
  cp "${REPO_ROOT}/config/odoo.conf" "${REPO_ROOT}/config/odoo.runtime.conf"
fi

DB_NAME="${1:?usage: restore.sh <db_name> <db_dump> [filestore_tgz]}"
DB_DUMP="${2:?usage: restore.sh <db_name> <db_dump> [filestore_tgz]}"
FILESTORE_TGZ="${3:-}"

# Validate ALL inputs before touching anything, so a bad argument can never
# abort the script halfway through a destructive phase. The tar listing reads
# the WHOLE archive, so a truncated/corrupt file is rejected here — before the
# existing filestore is touched.
[ -f "${DB_DUMP}" ] || { echo "!! dump not found: ${DB_DUMP}" >&2; exit 1; }
if [ -n "${FILESTORE_TGZ}" ]; then
  [ -f "${FILESTORE_TGZ}" ] || { echo "!! filestore archive not found: ${FILESTORE_TGZ}" >&2; exit 1; }
  if ! tar tzf "${FILESTORE_TGZ}" >/dev/null; then
    echo "!! filestore archive is corrupt/truncated: ${FILESTORE_TGZ} — nothing touched." >&2
    exit 1
  fi
fi

# The stack must be reachable BEFORE the operator is asked to confirm a
# destructive restore: a restore happens under pressure, and discovering the
# daemon is down after typing the database name — with odoo already stopped and
# the DB already dropped — is the worst possible moment to find out.
if ! require_docker_stack "${COMPOSE}" db; then
  log_error "!! Aborting before touching anything — the stack is not available."
  exit 1
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
  # Extract into a temp dir FIRST and only then swap it in: the existing
  # filestore is removed only after a fully successful extraction.
  # --strip-components=1 drops the archive's source-db top-level dir; the mv
  # supplies the target name, so cross-name restores get a filestore too.
  echo ">> Restoring filestore..."
  # shellcheck disable=SC2016  # Intentional: the body runs INSIDE the container
  # and must not expand locally; only ${DB_NAME} is spliced in by closing and
  # reopening the quotes, which is why it appears outside the single quotes.
  $COMPOSE run --rm --no-deps -T odoo sh -c '
    set -e
    TMP="/var/lib/odoo/filestore/.restore_tmp_$$"
    rm -rf "$TMP"; mkdir -p "$TMP"
    tar xzf - -C "$TMP" --strip-components=1
    rm -rf "/var/lib/odoo/filestore/'"${DB_NAME}"'"
    mv "$TMP" "/var/lib/odoo/filestore/'"${DB_NAME}"'"
  ' < "${FILESTORE_TGZ}"
fi

echo ">> Starting odoo..."
$COMPOSE start odoo
echo ">> Restore complete for '${DB_NAME}'."
