#!/usr/bin/env bash
# Fail if the newest VERIFIED backup for a database is older than N hours.
# Usage: ./scripts/check_backup_freshness.sh <db_name> <backup_dir> [max_age_hours]
#
# Run it from the scheduler (or by hand before a risky change). Exit 0 = a
# recent backup exists; exit 1 = stale, missing, or the last run failed. This
# is the counterpart to LAST_BACKUP_STATUS: the status file says what the last
# run did, this says whether a usable backup exists NOW. Seven silent failures
# over two weeks are what happens without either.
set -euo pipefail

DB_NAME="${1:?usage: check_backup_freshness.sh <db_name> <backup_dir> [max_age_hours]}"
BACKUP_DIR="${2:?usage: check_backup_freshness.sh <db_name> <backup_dir> [max_age_hours]}"
MAX_AGE_HOURS="${3:-48}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/preflight.sh
. "${REPO_ROOT}/scripts/lib/preflight.sh"

if [ ! -d "${BACKUP_DIR}" ]; then
  log_error "!! STALE: backup directory ${BACKUP_DIR} does not exist."
  exit 1
fi

# Newest dump for THIS database (exact-name glob, as retention uses).
NEWEST="$(find "${BACKUP_DIR}" -maxdepth 1 -type f -name "${DB_NAME}_[0-9]*.dump" \
  -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2- || true)"

if [ -z "${NEWEST}" ]; then
  log_error "!! STALE: no backup found for '${DB_NAME}' in ${BACKUP_DIR}."
  exit 1
fi

if [ ! -s "${NEWEST}" ]; then
  log_error "!! STALE: newest backup ${NEWEST} is EMPTY."
  exit 1
fi

NOW="$(date +%s)"
MTIME="$(date -r "${NEWEST}" +%s)"
AGE_HOURS=$(( (NOW - MTIME) / 3600 ))

STATUS_FILE="${BACKUP_DIR}/LAST_BACKUP_STATUS"
if [ -f "${STATUS_FILE}" ] && grep -q '^outcome=FAILED' "${STATUS_FILE}"; then
  log_error "!! The last backup run FAILED — see ${STATUS_FILE}:"
  sed 's/^/     /' "${STATUS_FILE}" >&2
  exit 1
fi

if [ "${AGE_HOURS}" -gt "${MAX_AGE_HOURS}" ]; then
  log_error "!! STALE: newest backup for '${DB_NAME}' is ${AGE_HOURS}h old (limit ${MAX_AGE_HOURS}h): ${NEWEST}"
  exit 1
fi

log_line ">> OK: newest backup for '${DB_NAME}' is ${AGE_HOURS}h old (limit ${MAX_AGE_HOURS}h)."
log_line ">>     ${NEWEST}"
