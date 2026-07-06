#!/usr/bin/env bash
# Daily backup of a client DB + filestore. Schedule via cron.
# Usage: ./scripts/backup.sh <db_name> <backup_dir>
set -euo pipefail
DB_NAME="${1:?usage: backup.sh <db_name> <backup_dir>}"
BACKUP_DIR="${2:?usage: backup.sh <db_name> <backup_dir>}"
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
echo ">> TODO: copy off-site and test restore."
