#!/usr/bin/env bash
# Assert that everything under vendor/ is still byte-for-byte the upstream code
# it claims to be.  Usage:
#
#   ./scripts/check_vendor.sh              # check, print each tree hash
#   ./scripts/check_vendor.sh --self-test  # prove the check discriminates
#
# WHY THIS EXISTS
# ---------------
# vendor/README.md records a pinned upstream commit. On its own that is a
# sentence in a markdown file: it stays true-looking after somebody edits a
# vendored .js to fix something in a hurry, after a partial copy, after a
# half-resolved merge. "We run web_responsive 19.0.1.1.0" would then be a claim
# about a version that exists on no other machine on earth, and the next upgrade
# would silently revert whatever the edit was for.
#
# HOW IT CHECKS
# -------------
# git tree objects are content-addressed: the object ID of a directory is a hash
# over every file's mode, name and content, recursively. So the ID that OCA/web
# has for `web_responsive` at the pinned commit is the SAME ID our copy hashes
# to — no separate checksum file to keep in step, no format of our own. One
# `git write-tree --prefix=` reproduces it from the WORKING tree (not the index
# and not HEAD, so an uncommitted local edit is caught too).
#
# It fails on a changed byte, a changed file mode, a deleted file and an added
# file alike, and it fails LOUDLY when the directory is missing rather than
# reporting success over an empty search — the failure shape CLAUDE.md calls
# "a success signal that can be produced by doing nothing". The file-count floor
# is the second half of that: a hash mismatch already catches truncation, but the
# floor states the expected magnitude in a form a human can sanity-check.
#
# --self-test breaks each of those things ON PURPOSE and requires the check to
# go red, then restores the tree and requires it to go green again. An untested
# guard is one more thing that passes by doing nothing.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

# --------------------------------------------------------------------------
# The pins. One line per vendored tree:  <path>|<git tree hash>|<file floor>
#
# Keep in step with the table in vendor/README.md. The hash is
# `git rev-parse <pinned-commit>:<upstream-subdir>` in the upstream clone.
# --------------------------------------------------------------------------
PINS=(
  "vendor/oca_web/web_responsive|f1e9c8dfadbdf32603a6fb0cea2e0031438e779b|100"
)

tree_hash () {  # tree_hash <path> -> prints the working tree's git tree object ID
  local path="$1"
  local index
  index="$(mktemp)"
  rm -f "${index}"
  # A private index, so this never touches the caller's staging area.
  #
  # --force so that a vendored file cannot be hidden from this check by adding
  # it to .gitignore, but with Python bytecode excluded: Odoo writes
  # __pycache__/*.pyc INTO the module directory the moment it imports it, so
  # without these exclusions the check goes red after every single test run.
  # A guard that cries wolf on ordinary work is a guard people learn to skip.
  # Bytecode is generated output, never part of what was vendored; an extra
  # SOURCE file is still caught (self-test 4 proves it).
  GIT_INDEX_FILE="${index}" git add --force -- "${path}" \
    ":(exclude)${path}/**/__pycache__/**" \
    ":(exclude)${path}/**/*.pyc" 2>/dev/null || true
  local out=""
  out="$(GIT_INDEX_FILE="${index}" git write-tree --prefix="${path}" 2>/dev/null || true)"
  rm -f "${index}"
  printf '%s' "${out}"
}

check_all () {   # -> 0 if every pin matches, 1 otherwise. Quiet unless $1 = loud.
  local loud="${1:-loud}"
  local failed=0 pin path want floor got count
  for pin in "${PINS[@]}"; do
    IFS='|' read -r path want floor <<<"${pin}"

    if [ ! -d "${path}" ]; then
      [ "${loud}" = loud ] && echo "!! MISSING: ${path} is not there at all." >&2
      failed=1
      continue
    fi

    count="$(find "${path}" -type f ! -path '*/__pycache__/*' | wc -l | tr -d ' ')"
    if [ "${count}" -lt "${floor}" ]; then
      [ "${loud}" = loud ] && echo "!! TRUNCATED: ${path} holds ${count} files, floor is ${floor}." >&2
      failed=1
    fi

    got="$(tree_hash "${path}")"
    if [ -z "${got}" ]; then
      [ "${loud}" = loud ] && echo "!! UNHASHABLE: could not compute a tree hash for ${path}." >&2
      failed=1
      continue
    fi
    if [ "${got}" != "${want}" ]; then
      [ "${loud}" = loud ] && {
        echo "!! MODIFIED: ${path} is not the upstream code it is pinned to." >&2
        echo "     pinned: ${want}" >&2
        echo "     actual: ${got}" >&2
        echo "   Vendored code is never edited in place — see vendor/README.md." >&2
        echo "   If this is a deliberate upstream refresh, update the pin AND the README." >&2
      }
      failed=1
    else
      [ "${loud}" = loud ] && echo "${got}  ${path}  (${count} files)"
    fi
  done
  return "${failed}"
}

# --------------------------------------------------------------------------
# --self-test: make the bad thing happen and watch the check go red.
# --------------------------------------------------------------------------
if [ "${1:-}" = "--self-test" ]; then
  VICTIM="vendor/oca_web/web_responsive/__manifest__.py"
  SPARE_DIR="vendor/oca_web/web_responsive/models"
  BACKUP="$(mktemp)"
  RESTORED=0

  restore () {
    if [ "${RESTORED}" -eq 0 ] && [ -f "${BACKUP}" ]; then
      cp -a "${BACKUP}" "${VICTIM}" 2>/dev/null || true
      rm -f "${VICTIM}.selftest-extra" "${SPARE_DIR}/.selftest-extra" 2>/dev/null || true
      rm -f "${BACKUP}"
    fi
  }
  trap restore EXIT

  echo "-- self-test: the tree must be clean before we break it"
  check_all quiet || { echo "!! self-test cannot run: vendor/ is ALREADY failing." >&2; exit 1; }
  echo "   clean."

  cp -a "${VICTIM}" "${BACKUP}"

  echo "-- self-test 1/4: change one byte in a vendored file"
  printf '\n# self-test\n' >>"${VICTIM}"
  if check_all quiet; then echo "!! DISCRIMINATION FAILED: an edited vendored file passed." >&2; exit 1; fi
  cp -a "${BACKUP}" "${VICTIM}"
  echo "   went red, as it must."

  echo "-- self-test 2/4: change a file's mode"
  chmod +x "${VICTIM}"
  if check_all quiet; then echo "!! DISCRIMINATION FAILED: a mode change passed." >&2; exit 1; fi
  cp -a "${BACKUP}" "${VICTIM}"
  chmod 644 "${VICTIM}"
  echo "   went red, as it must."

  echo "-- self-test 3/4: delete a vendored file"
  rm -f "${VICTIM}"
  if check_all quiet; then echo "!! DISCRIMINATION FAILED: a deleted file passed." >&2; exit 1; fi
  cp -a "${BACKUP}" "${VICTIM}"
  echo "   went red, as it must."

  echo "-- self-test 4/4: add a file that upstream does not have"
  touch "${SPARE_DIR}/.selftest-extra"
  if check_all quiet; then echo "!! DISCRIMINATION FAILED: an extra file passed." >&2; exit 1; fi
  rm -f "${SPARE_DIR}/.selftest-extra"
  echo "   went red, as it must."

  echo "-- self-test: and it recovers (a check that always failed would have passed 1-4)"
  restore
  RESTORED=1
  if ! check_all quiet; then
    echo "!! the tree did not come back clean after the self-test." >&2
    exit 1
  fi
  echo "   clean again. The guard discriminates."
  exit 0
fi

echo "Vendored trees, verified against their pinned upstream commits:"
if ! check_all loud; then
  exit 1
fi
echo "All vendored trees match their pins (vendor/README.md)."
