#!/usr/bin/env bash
# THE lint definition. One file, called by both the pre-push hook and CI.
#
# WHY THIS EXISTS
# ---------------
# CI went red on a pylint warning that a local run had already produced and I
# had called clean, because I read pylint's SCORE off the tail of its output
# instead of its exit code. pylint rates a tree 10.00/10 and still exits 4 when
# warnings are present:
#
#     $ pylint addons ; echo $?
#     Your code has been rated at 10.00/10
#     4
#
# Parsing a tool's prose for a verdict it already returns as a number is how
# "clean locally" and "clean in CI" come to mean different things. Everything
# below gates on `$?` and nothing reads output to decide anything.
#
# The second half of the same fix is that there is now only ONE definition of
# what lint means. The hook and the workflow both call this script, so a
# developer cannot pass a check CI will fail, or fail one CI would pass.
#
# Usage:
#     ./scripts/lint.sh          # from anywhere; resolves the repo itself
#
# Exit status: 0 when every tool passed, 1 otherwise — with the names of the
# tools that failed printed last, so the answer to "what broke" is the last
# line rather than somewhere in a thousand lines of tool output.
set -uo pipefail   # NOT -e: every tool must run, so one failure does not hide
                   # the next. The failures are collected and reported together.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

# The paths each tool covers. Stated once, here, rather than in two workflows.
RUFF_PATHS=(addons tests_fast)
BLACK_PATHS=(addons)
PYLINT_PATHS=(addons)

FAILED=()

# --- The tools must be PRESENT. Absence is a failure, not a skip. ------------
# Same rule as the gitleaks hook: a check that waves the tree through because
# its checker is missing is a green light produced by doing nothing. Each tool
# is resolved either as a bare command or as `python -m <tool>`, because a pip
# --user install often puts the module on sys.path without putting a script on
# PATH — and "ruff: command not found" must not read as "no lint problems".
resolve() {  # resolve <command-name> <python-module>
  if command -v "$1" >/dev/null 2>&1; then
    printf '%s' "$1"
    return 0
  fi
  for python in python3 python; do
    if command -v "${python}" >/dev/null 2>&1 \
       && "${python}" -c "import $2" >/dev/null 2>&1; then
      printf '%s -m %s' "${python}" "$2"
      return 0
    fi
  done
  return 1
}

missing=()
RUFF="$(resolve ruff ruff)" || missing+=("ruff")
BLACK="$(resolve black black)" || missing+=("black")
PYLINT="$(resolve pylint pylint)" || missing+=("pylint")
if [ "${#missing[@]}" -ne 0 ]; then
  cat >&2 <<EOF
!! lint: these tools are NOT INSTALLED: ${missing[*]}
!!
!! Refusing to report a clean tree that nothing checked. Install them:
!!     pip install ruff black pylint pylint-odoo
EOF
  exit 1
fi

# pylint-odoo is a PLUGIN, and pylint runs happily without it — reporting
# 10.00/10 while checking none of the Odoo rules (W8150 among them, which is
# the warning that started all this). Its absence would therefore be invisible.
if ! ${PYLINT} --list-extensions 2>/dev/null | grep -q pylint_odoo \
   && ! ${PYLINT%% *} -c "import pylint_odoo" >/dev/null 2>&1 \
   && ! python3 -c "import pylint_odoo" >/dev/null 2>&1; then
  cat >&2 <<'EOF'
!! lint: pylint-odoo is NOT INSTALLED.
!!
!! pylint would still run and still print a score, having checked none of the
!! Odoo-specific rules. Install it:
!!     pip install pylint-odoo
EOF
  exit 1
fi

# --- Assert there is something to lint ---------------------------------------
# Measured, not assumed: on an empty tree black exits 0 ("No Python files ...
# Nothing to do"), ruff exits 0 with a warning, and pylint exits 0. So a
# renamed, moved or half-checked-out addons/ passes every check below by
# containing nothing. The floors are well under the real counts — they catch
# "the tree is gone", not "somebody deleted a file".
MIN_PY_FILES=80      # 120 at this commit
MIN_MANIFESTS=5      # 11
py_files=$(find addons tests_fast -name '*.py' 2>/dev/null | wc -l)
manifests=$(find addons -maxdepth 2 -name '__manifest__.py' 2>/dev/null | wc -l)
printf '>> lint: %s python files (floor %s), %s manifests (floor %s)\n' \
  "${py_files}" "${MIN_PY_FILES}" "${manifests}" "${MIN_MANIFESTS}"
if [ "${py_files}" -lt "${MIN_PY_FILES}" ] || [ "${manifests}" -lt "${MIN_MANIFESTS}" ]; then
  echo "!! lint: the source tree is missing or truncated — every tool below would" >&2
  echo "   pass by checking nothing." >&2
  exit 1
fi

# --- Run each tool, and read its EXIT CODE -----------------------------------
run() {  # run <label> <command...>
  local label="$1"; shift
  printf '\n>> lint: %s\n' "${label}"
  "$@"
  local status=$?
  if [ "${status}" -ne 0 ]; then
    printf '>> lint: %s FAILED (exit %s)\n' "${label}" "${status}"
    FAILED+=("${label}")
  fi
  return 0
}

run ruff   ${RUFF} check "${RUFF_PATHS[@]}"
run black  ${BLACK} --check "${BLACK_PATHS[@]}"
# pylint's exit status is a BITMASK: 1 fatal, 2 error, 4 warning, 8 refactor,
# 16 convention, 32 usage error. Anything non-zero is a finding, and 4 — plain
# warnings, with a 10.00/10 score printed above it — is the exact value that
# reached CI. No special-casing: non-zero is non-zero.
run pylint ${PYLINT} "${PYLINT_PATHS[@]}"

printf '\n'
if [ "${#FAILED[@]}" -ne 0 ]; then
  printf '!! lint FAILED: %s\n' "${FAILED[*]}" >&2
  exit 1
fi
printf '>> lint clean: ruff, black, pylint-odoo all exited 0.\n'
exit 0
