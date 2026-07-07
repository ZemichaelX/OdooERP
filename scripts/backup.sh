#!/usr/bin/env bash
# Daily backup of a client DB + filestore. Schedule via cron / Task Scheduler.
# Usage: ./scripts/backup.sh <db_name> <backup_dir> [offsite_dir] [retention_days]
#   offsite_dir     if given, the two archives are also copied here (e.g. a
#                   OneDrive/Google-Drive-synced folder) for an off-site copy.
#   retention_days  prune archives older than this in BOTH dirs (default 14).
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
mkdir -p "${BACKUP_DIR}"
COMPOSE="docker compose -f docker/docker-compose.yml"

DB_DUMP="${BACKUP_DIR}/${DB_NAME}_${STAMP}.dump"
FILESTORE_ARCHIVE="${BACKUP_DIR}/${DB_NAME}_filestore_${STAMP}.tgz"

echo ">> Dumping database ${DB_NAME}"
$COMPOSE exec -T db pg_dump -U odoo -Fc "${DB_NAME}" > "${DB_DUMP}"

# The filestore holds attachments, report assets and logos: a DB dump without
# it is an INCOMPLETE backup. A failure here must abort loudly (A9) — never
# print "Backup written" on a partial success. The partial archive is removed
# so it can't be mistaken for a good one.
echo ">> Archiving filestore"
if ! $COMPOSE exec -T odoo tar czf - -C /var/lib/odoo/filestore "${DB_NAME}" > "${FILESTORE_ARCHIVE}"; then
  echo "!! Filestore archive FAILED for ${DB_NAME} — removing partial file and aborting." >&2
  rm -f "${FILESTORE_ARCHIVE}"
  exit 1
fi

echo ">> Backup written to ${BACKUP_DIR} (database + filestore)."

# Off-site copy: a backup on the same disk as the DB won't survive a disk loss.
# Copy both archives to the synced folder; a failure here aborts loudly (A9) so
# a broken off-site can never pass silently.
if [ -n "${OFFSITE_DIR}" ]; then
  echo ">> Copying off-site to ${OFFSITE_DIR}"
  if ! mkdir -p "${OFFSITE_DIR}" || ! cp "${DB_DUMP}" "${FILESTORE_ARCHIVE}" "${OFFSITE_DIR}/"; then
    echo "!! Off-site copy FAILED for ${DB_NAME} — aborting." >&2
    exit 1
  fi
  find "${OFFSITE_DIR}" -maxdepth 1 -type f -name "${DB_NAME}_*" -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
  echo ">> Off-site copy complete."
fi

# Retention: prune old local archives for this DB.
find "${BACKUP_DIR}" -maxdepth 1 -type f -name "${DB_NAME}_*" -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
echo ">> Done. Reminder: test a restore periodically (scripts/restore.sh)."
