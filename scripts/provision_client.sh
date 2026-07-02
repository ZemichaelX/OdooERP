#!/usr/bin/env bash
# Provision a new client instance: create DB and install the base + chosen modules.
# Usage: ./scripts/provision_client.sh <db_name> [comma,separated,modules]
set -euo pipefail

DB_NAME="${1:?usage: provision_client.sh <db_name> [modules]}"
MODULES="${2:-sapian_core,l10n_et_payroll}"
COMPOSE="docker compose -f docker/docker-compose.yml"

echo ">> Provisioning client DB: ${DB_NAME}"
echo ">> Installing modules: ${MODULES}"

$COMPOSE run --rm odoo \
  odoo -d "${DB_NAME}" -i "${MODULES}" --without-demo=all --stop-after-init

echo ">> Done. Next: configure company/branding/roles via the onboarding wizard,"
echo ">>       import master data from data-templates/, enable backups & 2FA."
