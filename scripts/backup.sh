#!/usr/bin/env bash
# Daily backup of a client DB + filestore. Schedule via cron.
# Usage: ./scripts/backup.sh <db_name> <backup_dir>
set -euo pipefail
DB_NAME="${1:?usage: backup.sh <db_name> <backup_dir>}"
BACKUP_DIR="${2:?usage: backup.sh <db_name> <backup_dir>}"
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "${BACKUP_DIR}"
COMPOSE="docker compose -f docker/docker-compose.yml"

echo ">> Dumping database ${DB_NAME}"
$COMPOSE exec -T db pg_dump -U odoo -Fc "${DB_NAME}" > "${BACKUP_DIR}/${DB_NAME}_${STAMP}.dump"

echo ">> Archiving filestore"
$COMPOSE exec -T odoo tar czf - -C /var/lib/odoo/filestore "${DB_NAME}" \
  > "${BACKUP_DIR}/${DB_NAME}_filestore_${STAMP}.tgz" || true

echo ">> Backup written to ${BACKUP_DIR}. TODO: copy off-site and test restore."
