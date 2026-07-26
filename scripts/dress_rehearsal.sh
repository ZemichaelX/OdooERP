#!/usr/bin/env bash
# Pre-release ritual: rebuild a fresh tenant, run one realistic month of
# business (August 2026), then prove the books with an independent exam.
#
#   scripts/dress_rehearsal.sh [db_name]
#
# The tenant is KEPT after the run for manual click-through. Rerun any time —
# it drops and recreates the database from empty each time.
# Exits non-zero if the reconciliation exam finds any mismatch, so this can
# gate a release without eyeballing the report.
set -euo pipefail
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'

DB="${1:-scratch_rehearsal}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="docker compose -f ${REPO_ROOT}/docker/docker-compose.yml"

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

echo ">> This will DROP and recreate database '${DB}' from empty."
read -r -p ">> Type the DB name to confirm: " CONFIRM
[ "${CONFIRM}" = "${DB}" ] || { echo "!! confirmation mismatch; aborting." >&2; exit 1; }

echo ">> Dropping and recreating '$DB' ..."
$COMPOSE exec -T db psql -U odoo -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB' AND pid <> pg_backend_pid();" \
  >/dev/null 2>&1 || true
$COMPOSE exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS $DB;"

echo ">> Installing modules on '$DB' ..."
$COMPOSE run --rm odoo odoo -d "$DB" -i sapian_dress_rehearsal \
  --stop-after-init --workers=0 --log-level=warn

echo ">> Provisioning the August-2026 month and running the exam ..."
EXAM_OUT="$(mktemp)"
# Heredoc piped to odoo shell (bash, not PowerShell — avoids a BOM prefix).
# The EXAM_VERDICT sentinel is how this script learns the exam's outcome:
# odoo shell always exits 0, so the verdict must ride on stdout.
$COMPOSE run --rm -T odoo odoo shell -d "$DB" --workers=0 --log-level=error <<'PYEOF' | tee "${EXAM_OUT}"
company = env["sapian.dress.rehearsal"]._provision()
env.cr.commit()
result = env["sapian.dress.rehearsal.exam"].run(company)
print(env["sapian.dress.rehearsal.exam"].format_report(result))
print("EXAM_VERDICT: " + ("PASS" if result["all_ok"] else "FAIL"))
PYEOF

if ! grep -q "EXAM_VERDICT: PASS" "${EXAM_OUT}"; then
  rm -f "${EXAM_OUT}"
  echo "!! Dress-rehearsal exam FAILED — see the XX rows in the report above." >&2
  exit 1
fi
rm -f "${EXAM_OUT}"
echo ">> Done. Exam PASSED. Tenant kept on database '$DB' for manual click-through."
