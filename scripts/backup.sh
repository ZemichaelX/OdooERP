#!/usr/bin/env bash
# Daily backup of a client DB + filestore. Schedule via cron / Task Scheduler.
# Usage: ./scripts/backup.sh <db_name> <backup_dir> [offsite_dir] [retention_days]
#   offsite_dir     if given, the two archives are also copied here (e.g. a
#                   OneDrive/Google-Drive-synced folder) for an off-site copy.
#   retention_days  prune archives older than this in BOTH dirs (default 14).
#
# DESIGN RULE, learned the hard way: a file bearing a backup's real name must
# only ever come into existence AFTER that backup is complete and verified.
# Seven 0-byte .dump files accumulated over two weeks because Docker Desktop
# was not running: the dump command failed, but `>` had already created the
# destination, and the cleanup that would have removed it never ran (the shell
# died — the log shows a Git-Bash fork failure, exit code 0xC000026B). Cleanup
# after the fact cannot be relied on, because cleanup is exactly what does not
# happen when a process dies. So: preconditions first, work in <name>.tmp,
# verify, then mv into place. Every outcome is recorded in LAST_BACKUP_STATUS.
set -euo pipefail
# Git Bash (Windows) rewrites container-absolute paths like /var/lib/odoo/...
# into C:/Program Files/Git/...; disable that so docker exec gets the real path.
# No-op on Linux/CI.
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
DB_NAME="${1:?usage: backup.sh <db_name> <backup_dir> [offsite_dir] [retention_days]}"
BACKUP_DIR="${2:?usage: backup.sh <db_name> <backup_dir> [offsite_dir] [retention_days]}"
OFFSITE_DIR="${3:-}"
RETENTION_DAYS="${4:-14}"
STAMP="$(date +%Y%m%d_%H%M%S)"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="docker compose -f ${REPO_ROOT}/docker/docker-compose.yml"

# shellcheck source=scripts/lib/preflight.sh
. "${REPO_ROOT}/scripts/lib/preflight.sh"

STATUS_FILE="${BACKUP_DIR}/LAST_BACKUP_STATUS"

# Record the outcome where a human or a monitoring check can find it. Written
# on EVERY exit path, including failure — a backup that fails silently for a
# fortnight is the actual damage this script exists to prevent.
write_status() {
  local outcome="$1"
  local reason="${2:-}"
  # The status file itself must never be the thing that fails the run.
  {
    printf 'timestamp=%s\n' "$(date '+%Y-%m-%d %H:%M:%S')"
    printf 'database=%s\n' "${DB_NAME}"
    printf 'outcome=%s\n' "${outcome}"
    if [ -n "${reason}" ]; then
      printf 'reason=%s\n' "${reason}"
    fi
  } > "${STATUS_FILE}" 2>/dev/null || true
}

fail() {
  local reason="$1"
  log_error "!! ${reason}"
  write_status "FAILED" "${reason}"
  exit 1
}

# --- Preconditions -------------------------------------------------------
# Checked BEFORE mkdir/redirect, so an unreachable stack leaves no artefact.
if [ -d "${REPO_ROOT}/config/odoo.runtime.conf" ]; then
  log_error "!! ${REPO_ROOT}/config/odoo.runtime.conf is a DIRECTORY (docker created it before the file existed)."
  log_error "!! Remove it (rm -rf config/odoo.runtime.conf) and re-run — it will be recreated from config/odoo.conf."
  exit 1
fi
if [ ! -f "${REPO_ROOT}/config/odoo.runtime.conf" ]; then
  log_line ">> Creating config/odoo.runtime.conf from the template."
  cp "${REPO_ROOT}/config/odoo.conf" "${REPO_ROOT}/config/odoo.runtime.conf"
fi

# The directory itself is created first so the failure can be RECORDED: a
# precondition failure that leaves no trace is the silent-failure bug in a new
# costume. What must not be created is a backup ARTEFACT — no .dump, no .tgz.
mkdir -p "${BACKUP_DIR}"

if ! require_docker_stack "${COMPOSE}" db; then
  fail "Docker stack unavailable — aborted before creating any backup file."
fi

DB_DUMP="${BACKUP_DIR}/${DB_NAME}_${STAMP}.dump"
FILESTORE_ARCHIVE="${BACKUP_DIR}/${DB_NAME}_filestore_${STAMP}.tgz"
DB_DUMP_TMP="${DB_DUMP}.tmp"
FILESTORE_TMP="${FILESTORE_ARCHIVE}.tmp"

# Whatever happens, temp files never survive to look like backups. They also
# never bear a backup's real name, so even a killed shell leaves only .tmp.
cleanup_tmp() {
  rm -f "${DB_DUMP_TMP}" "${FILESTORE_TMP}" 2>/dev/null || true
}
trap cleanup_tmp EXIT

# --- Database dump (to .tmp) ---------------------------------------------
log_line ">> Dumping database ${DB_NAME}"
if ! $COMPOSE exec -T db pg_dump -U odoo -Fc "${DB_NAME}" > "${DB_DUMP_TMP}"; then
  fail "Database dump FAILED for ${DB_NAME} — no backup file was created."
fi

# An empty or truncated dump must not reach the verification step looking
# plausible: check the size explicitly, then have pg_restore read the archive.
if [ ! -s "${DB_DUMP_TMP}" ]; then
  fail "Database dump for ${DB_NAME} is EMPTY (0 bytes) — no backup file was created."
fi

log_line ">> Verifying dump is restorable"
if ! $COMPOSE exec -T db pg_restore --list >/dev/null < "${DB_DUMP_TMP}"; then
  fail "Dump verification FAILED for ${DB_NAME} — no backup file was created."
fi

# --- Filestore archive (to .tmp) -----------------------------------------
# The filestore holds attachments, report assets and logos: a DB dump without
# it is an INCOMPLETE backup. Throwaway container (same pattern as restore.sh)
# so the backup works with the odoo SERVICE stopped or crashed — right after a
# crash is exactly when a backup matters most.
log_line ">> Archiving filestore"
if ! $COMPOSE run --rm --no-deps -T odoo tar czf - -C /var/lib/odoo/filestore "${DB_NAME}" > "${FILESTORE_TMP}"; then
  fail "Filestore archive FAILED for ${DB_NAME} — no backup file was created."
fi
if [ ! -s "${FILESTORE_TMP}" ]; then
  fail "Filestore archive for ${DB_NAME} is EMPTY (0 bytes) — no backup file was created."
fi
if ! tar tzf "${FILESTORE_TMP}" >/dev/null 2>&1; then
  fail "Filestore archive for ${DB_NAME} is not a readable tarball — no backup file was created."
fi

# --- Publish: only now do the real names exist ---------------------------
mv "${DB_DUMP_TMP}" "${DB_DUMP}"
mv "${FILESTORE_TMP}" "${FILESTORE_ARCHIVE}"
log_line ">> Backup written to ${BACKUP_DIR} (database + filestore)."

# Retention must match THIS database's archives exactly: the stamp starts with
# a digit, so 'sapian_[0-9]*' cannot swallow 'sapian_prod_*' the way a bare
# 'sapian_*' prefix glob did.
PRUNE_GLOBS=( \( -name "${DB_NAME}_[0-9]*.dump" -o -name "${DB_NAME}_filestore_[0-9]*.tgz" \) )

# Off-site copy: a backup on the same disk as the DB won't survive a disk loss.
if [ -n "${OFFSITE_DIR}" ]; then
  log_line ">> Copying off-site to ${OFFSITE_DIR}"
  if ! mkdir -p "${OFFSITE_DIR}" || ! cp "${DB_DUMP}" "${FILESTORE_ARCHIVE}" "${OFFSITE_DIR}/"; then
    fail "Off-site copy FAILED for ${DB_NAME}."
  fi
  find "${OFFSITE_DIR}" -maxdepth 1 -type f "${PRUNE_GLOBS[@]}" -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
  log_line ">> Off-site copy complete."
fi

# Retention: prune old local archives for this DB.
find "${BACKUP_DIR}" -maxdepth 1 -type f "${PRUNE_GLOBS[@]}" -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true

write_status "OK"
log_line ">> Done. Reminder: test a restore periodically (scripts/restore.sh)."
