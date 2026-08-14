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
# Git Bash (Windows) converts POSIX-looking arguments to Windows paths on the
# way out to native binaries. CONTAINER paths (/var/lib/odoo/...) must NOT be
# converted — that mangles them into C:/Program Files/Git/... inside docker.
# The exclusion is SCOPED to those paths: an earlier blanket
# MSYS2_ARG_CONV_EXCL='*' also stopped the HOST path passed to `docker compose
# -f` from being converted, so docker resolved /c/Users/... against the current
# drive as C:\c\Users\... and every compose call failed. No-op off Windows.
export MSYS2_ARG_CONV_EXCL='/var/lib/odoo'

DB="${1:-scratch_rehearsal}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/preflight.sh
. "${REPO_ROOT}/scripts/lib/preflight.sh"

# The -f path goes through compose_cmd so the HOST path is in the form
# docker can open on Windows (see scripts/lib/preflight.sh).
COMPOSE="$(compose_cmd "${REPO_ROOT}/docker/docker-compose.yml")"

# Pre-flight: compose mounts config/odoo.runtime.conf (gitignored, absent on a
# fresh clone). See ensure_runtime_conf in scripts/lib/preflight.sh.
if ! ensure_runtime_conf "${REPO_ROOT}"; then
  log_error "!! Aborting — config/odoo.runtime.conf is not usable."
  exit 1
fi

echo ">> This will DROP and recreate database '${DB}' from empty."
read -r -p ">> Type the DB name to confirm: " CONFIRM
[ "${CONFIRM}" = "${DB}" ] || { echo "!! confirmation mismatch; aborting." >&2; exit 1; }

echo ">> Dropping and recreating '$DB' ..."
$COMPOSE exec -T db psql -U odoo -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB' AND pid <> pg_backend_pid();" \
  >/dev/null 2>&1 || true
$COMPOSE exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS $DB;"

# sapian_theme installs here for the same reason it installs in build_demo.sh:
# THE TENANT YOU REHEARSE ON MUST BE THE TENANT YOU SHOW. A rehearsal on an
# Odoo-purple, rail-less database rehearses a different product, and the point
# of a dress rehearsal is to meet the surprises here rather than on camera.
echo ">> Installing modules on '$DB' ..."
$COMPOSE run --rm odoo odoo -d "$DB" -i sapian_dress_rehearsal,sapian_theme \
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

# The tenant must LOOK like the product too, not just add up. Read out of the
# compiled stylesheet, the same way build_demo.sh does — a config line that
# says "install the theme" is what was already there when the demo came out
# purple.
import re  # noqa: E402
from odoo.addons.sapian_theme import brand  # noqa: E402

# `_get_asset_bundle(...).css()` COMPILES and stores; `_generate_asset_links`
# does not, and on a freshly built database it leaves the attachment absent —
# which reads as "the brand is missing" when the brand is fine. Measured: this
# check reported backend_primary=ABSENT on a correctly themed rehearsal.
_att = env["ir.qweb"]._get_asset_bundle("web.assets_web", css=True, js=False).css()
_css = (_att.raw or b"").decode("utf-8", "ignore") if _att else ""
_primary = re.findall(r"--primary: (#[0-9A-Fa-f]{6});", _css)
_rail = bool(re.search(r"\.o_web_client:has\(\.o_sapian_rail\)\{padding-left", _css))
print("LOOK backend_primary=%s expected=%s rail_css=%s"
      % (_primary[0] if _primary else "ABSENT", brand.brand_primary(), _rail))
_looks_right = bool(_primary) and _primary[0].upper() == brand.brand_primary().upper() and _rail

print("EXAM_VERDICT: " + ("PASS" if result["all_ok"] and _looks_right else "FAIL"))
PYEOF

if ! grep -q "EXAM_VERDICT: PASS" "${EXAM_OUT}"; then
  rm -f "${EXAM_OUT}"
  echo "!! Dress-rehearsal FAILED — see the XX rows in the exam report above," >&2
  echo "   or the LOOK line if the tenant does not carry the SapianERP theme." >&2
  exit 1
fi
grep -E '^LOOK ' "${EXAM_OUT}" || true
rm -f "${EXAM_OUT}"
echo ">> Done. Exam PASSED. Tenant kept on database '$DB' for manual click-through."
