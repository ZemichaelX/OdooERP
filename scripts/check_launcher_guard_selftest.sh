#!/usr/bin/env bash
# Prove that verify_launcher turns a null measurement into ONE honest error.
#
# WHY: check_launcher.py now emits `launcher_measured=0` and prints nothing
# downstream when the fetch never reached the backend. That is only half the
# fix — the half an operator reads is preflight.sh::verify_launcher, which used
# to print six separate alarms ("no backend JS bundle", "the launcher component
# is NOT in the JavaScript this database serves", "the app rail cannot render",
# ...) from that same null measurement.
#
# Each case below drives verify_launcher with a stub `compose` command that
# emits a canned transcript, so it needs no Docker, no database and no Odoo.
# The assertion is on the MESSAGE, not merely on the exit code: a guard that
# fails for the wrong reason is the failure mode this repository keeps finding.
#
# Run: bash scripts/check_launcher_guard_selftest.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/preflight.sh
. "${ROOT}/scripts/lib/preflight.sh"

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT
FAILED=0

fake_compose() {   # <fixture-file>
  cat > "${WORK}/compose" <<EOF
#!/usr/bin/env bash
cat "$1"
EOF
  chmod +x "${WORK}/compose"
  echo "${WORK}/compose"
}

# The six downstream alarms that must NOT appear when nothing was measured.
DOWNSTREAM_ALARMS=(
  "No backend JS bundle was served"
  "The launcher component is NOT in the JavaScript"
  "web_responsive's stylesheet is not in the CSS"
  "sapian_theme's stylesheet is not in the CSS"
  "web_responsive JS modules reached the bundle"
  "Could not read the brand colour"
)

check() {   # <label> <fixture> <expect-rc> <must-contain> <must-not-contain-downstream:0|1>
  local label="$1" fixture="$2" want_rc="$3" needle="$4" forbid="$5"
  local out rc
  out="$(verify_launcher "$(fake_compose "${fixture}")" demo_v3 "${ROOT}" 2>&1)"
  rc=$?
  if [ "${rc}" -ne "${want_rc}" ]; then
    echo "FAIL [${label}]: expected exit ${want_rc}, got ${rc}" >&2
    FAILED=1
  fi
  if ! printf '%s\n' "${out}" | grep -qF "${needle}"; then
    echo "FAIL [${label}]: expected message not found: ${needle}" >&2
    printf '%s\n' "${out}" | tail -20 >&2
    FAILED=1
  fi
  if [ "${forbid}" = "1" ]; then
    local alarm found=0
    for alarm in "${DOWNSTREAM_ALARMS[@]}"; do
      if printf '%s\n' "${out}" | grep -qF "${alarm}"; then
        echo "FAIL [${label}]: a downstream alarm was printed from a null measurement: ${alarm}" >&2
        found=1
      fi
    done
    [ "${found}" -eq 0 ] || FAILED=1
  fi
  echo "  [${label}] rc=${rc}"
}

# ---- 1. THE BAD THING: the verifier could not measure ----------------------
cat > "${WORK}/aborted.txt" <<'EOF'
CHECK launcher_module=installed
CHECK launcher_in_init_modules=True
CHECK launcher_users=2
CHECK launcher_users_not_redirected=0
CHECK launcher_users_not_branded=0
CHECK brand_expected=#14454F
CHECK launcher_page_http=200
CHECK launcher_page_bytes=9685
CHECK launcher_served_frontend=True
CHECK launcher_served_title=Login | My Website
CHECK launcher_measured=0
EOF
check "could not measure" "${WORK}/aborted.txt" 1 "COULD NOT MEASURE the launcher" 1

# ---- 2. The verifier did not report at all (it raised, or never ran) -------
cat > "${WORK}/silent.txt" <<'EOF'
Traceback (most recent call last):
  File "<stdin>", line 1
EOF
check "no marker at all" "${WORK}/silent.txt" 1 "did not report whether it measured anything" 1

# ---- 3. A REAL measurement, all green: the guard must stay out of the way --
cat > "${WORK}/green.txt" <<'EOF'
CHECK launcher_module=installed
CHECK launcher_in_init_modules=True
CHECK launcher_users=2
CHECK launcher_users_not_redirected=0
CHECK launcher_users_not_branded=0
CHECK brand_expected=#14454F
CHECK launcher_page_http=200
CHECK launcher_page_bytes=7098
CHECK launcher_measured=1
CHECK launcher_backend_js_bundles=1
CHECK launcher_backend_css_bundles=1
CHECK launcher_home_action_on_wire=false
CHECK launcher_users_with_home_action=0
CHECK launcher_js_bytes=7952727
CHECK launcher_css_bytes=1270134
CHECK launcher_js_modules=16
CHECK launcher_js_named=True
CHECK launcher_css_web_responsive=True
CHECK launcher_css_sapian_theme=True
CHECK launcher_community_colour=#14454F
CHECK launcher_milk_colour=#E9E6F9
EOF
check "measured and green" "${WORK}/green.txt" 0 "CHECK launcher_measured=1" 0

# ---- 4. A REAL measurement that is genuinely broken: still red, and for the
#         right reason. Without this, "return 1 early on everything" would pass.
cat > "${WORK}/broken.txt" <<'EOF'
CHECK launcher_module=installed
CHECK launcher_in_init_modules=True
CHECK launcher_users=2
CHECK launcher_users_not_redirected=0
CHECK launcher_users_not_branded=0
CHECK brand_expected=#14454F
CHECK launcher_page_http=200
CHECK launcher_page_bytes=7098
CHECK launcher_measured=1
CHECK launcher_backend_js_bundles=1
CHECK launcher_backend_css_bundles=1
CHECK launcher_home_action_on_wire=false
CHECK launcher_users_with_home_action=0
CHECK launcher_js_bytes=6459828
CHECK launcher_css_bytes=1084450
CHECK launcher_js_modules=0
CHECK launcher_js_named=False
CHECK launcher_css_web_responsive=False
CHECK launcher_css_sapian_theme=True
CHECK launcher_community_colour=#14454F
CHECK launcher_milk_colour=#E9E6F9
EOF
check "measured and broken" "${WORK}/broken.txt" 1 "The launcher component is NOT in the JavaScript" 0

if [ "${FAILED}" -ne 0 ]; then
  echo "verify_launcher's null-measurement guard does NOT discriminate." >&2
  exit 1
fi
echo "OK — one 'could not measure' error on a null measurement, no downstream alarms,"
echo "     and a genuinely broken launcher is still reported as broken."
