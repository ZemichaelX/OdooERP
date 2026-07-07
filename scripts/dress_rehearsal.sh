#!/usr/bin/env bash
# Pre-release ritual: rebuild a fresh tenant, run one realistic month of
# business (August 2026), then prove the books with an independent exam.
#
#   scripts/dress_rehearsal.sh [db_name]
#
# The tenant is KEPT after the run for manual click-through. Rerun any time —
# it drops and recreates the database from empty each time.
set -euo pipefail

DB="${1:-scratch_rehearsal}"
COMPOSE="docker compose -f docker/docker-compose.yml"

echo ">> Dropping and recreating '$DB' ..."
$COMPOSE exec -T db psql -U odoo -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB' AND pid <> pg_backend_pid();" \
  >/dev/null 2>&1 || true
$COMPOSE exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS $DB;"

echo ">> Installing modules on '$DB' ..."
$COMPOSE run --rm odoo odoo -d "$DB" -i sapian_dress_rehearsal \
  --stop-after-init --workers=0 --log-level=warn

echo ">> Provisioning the August-2026 month and running the exam ..."
# Heredoc piped to odoo shell (bash, not PowerShell — avoids a BOM prefix).
$COMPOSE run --rm -T odoo odoo shell -d "$DB" --workers=0 --log-level=error <<'PYEOF'
company = env["sapian.dress.rehearsal"]._provision()
env.cr.commit()
result = env["sapian.dress.rehearsal.exam"].run(company)
print(env["sapian.dress.rehearsal.exam"].format_report(result))
PYEOF

echo ">> Done. Tenant kept on database '$DB' for manual click-through."
