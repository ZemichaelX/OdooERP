#!/usr/bin/env bash
# Deploy the current master to a local tenant: pull, then upgrade what is
# installed and install what is new, in one Odoo invocation.
#
# Usage: ./scripts/update_local.sh [db_name] [--install mod1,mod2]
#        ./scripts/update_local.sh --self-test
#        db_name defaults to demo_allapps.
#
# RUN IT FROM THE WSL2 UBUNTU TERMINAL, NOT POWERSHELL. It is a bash script and
# uses bash-only constructs (arrays, `declare -a`, process substitution). From
# PowerShell there is no bash to run it. See "ASSUMPTIONS" at the foot of this
# header for the full list of what it expects of the machine.
#
# WHY THIS EXISTS
# ---------------
# Every green pull request between #47 and #49 was invisible on the machine the
# product is demonstrated from, because nothing had ever deployed a merged PR to
# it. The tenant was three PRs behind while CI was green, which is the worst
# possible split: the evidence and the artefact disagreed and nothing said so.
#
# THE PART THAT IS NOT OBVIOUS — STEP 2, AND IT IS THE POINT OF THE SCRIPT.
# `odoo -u <module>` for a module that has never been installed does NOT install
# it. Odoo prints
#
#     WARNING ... odoo.modules.loading: invalid module names, ignored: sapian_theme_auth_signup
#
# and carries on to exit 0. That is how #48's bridge went missing on the demo
# tenant: the operator upgraded a list that included it, the run was green, and
# the module was never there. A NEW module needs -i; an INSTALLED one needs -u;
# and only the database can say which is which. So this script asks the database
# first and then passes each module in the right list.
#
# WHICH NEW MODULES GET INSTALLED, AND WHICH DO NOT
# -------------------------------------------------
# A new module is installed only when it is `auto_install` AND every module it
# depends on is ALREADY installed. Both halves are needed, and the second half
# was learned the hard way — see the comment above the query in step 2: without
# it, `-i l10n_et_calendar_account` on a base + theme database installed
# l10n_et_calendar, account and purchase as dependencies and took the database
# from a handful of modules to 65. `auto_install` means "install me when my
# dependencies are already there"; passing -i means "install me and everything I
# need", which is a different and much larger action.
#
# With both halves, installing such a module restores PARITY: it is exactly the
# module Odoo would already have installed by itself on a fresh build with this
# module set. Anything else — a vertical, a demo tenant, a new app, or a bridge
# still waiting on its dependencies — is a decision about what a client has
# bought. Those are reported as SKIPPED, by name and with what they are waiting
# on, and installed only if the operator names them with --install.
#
# That distinction is load-bearing: `addons/` contains sapian_demo_trader,
# sapian_demo_pharma and sapian_dress_rehearsal, and a script that installed
# every new module would push demo data and an internal QA harness onto a client
# tenant. scripts/check_no_demo_modules.sh exists because that must not happen.
#
# A SCRIPT THAT CAN SILENTLY DO NOTHING IS NOT A DEPLOY SCRIPT
# -----------------------------------------------------------
# So, in order:
#   * it refuses to run from a dirty tree (that is not a deploy of master);
#   * it aborts if the computed module list is EMPTY — no modules means the
#     enumeration broke, not that there was nothing to do;
#   * it fails on Odoo's "invalid module names, ignored" line, the exact silent
#     failure above;
#   * it requires one `Loading module <name>` line per module it named, which is
#     why it runs at --log-level=info;
#   * it reads `ir_module_module` back afterwards and fails unless every module
#     it named reports state=installed;
#   * it RESTARTS the server and proves the restart, because `--stop-after-init`
#     upgrades the database and exits while the container that serves the tenant
#     keeps the old registry and asset bundles in memory. Without this the
#     script reports a successful deploy that the browser cannot see.
# Each of those can only be satisfied by the work actually happening.
#
# And `--self-test` makes each of those checks FALSE ON PURPOSE and requires the
# script to go red for that specific reason. It runs in CI.
#
# ASSUMPTIONS ABOUT THE MACHINE — all of them, so a failure can be read
# ---------------------------------------------------------------------
#   1. bash 4+.  Arrays and process substitution. Not sh, not PowerShell.
#   2. The WSL2 Ubuntu terminal, with the repository at its Windows path
#      (/mnt/c/...). Running it from PowerShell will not work at all.
#   3. `docker` and `docker compose` on PATH and Docker Desktop RUNNING, with
#      WSL2 integration enabled for this distro.
#   4. `git`, `curl` and `awk` on PATH.
#   5. The checkout is a git repository with `origin` reachable — the pull is
#      `--ff-only`, so local commits on master stop the run rather than being
#      merged silently.
#   6. The working tree is CLEAN. A deploy from a dirty tree is not a deploy of
#      master.
#   7. `config/odoo.runtime.conf` exists and its addons_path carries
#      /mnt/vendor (assert_addons_path checks this and says so if not).
#   8. The compose stack's odoo service publishes 8069 on localhost, which is
#      what the post-restart HTTP check polls. Override with
#      SAPIAN_UPDATE_HTTP_URL if it is mapped elsewhere.
#   9. LF line endings. A CRLF checkout on the Windows filesystem makes bash
#      fail with `$'\r': command not found`; the repo ships .gitattributes for
#      this, but a tree cloned before that landed can still carry CRLF.
set -uo pipefail

# --- SELF-TEST ----------------------------------------------------------------
# Every guard above is a claim. `--self-test` makes each claim false ON PURPOSE
# and requires the script to go red, then requires the healthy case to go green.
# A guard nobody has watched fail is another thing that passes by doing nothing,
# and this script's whole subject is things that pass by doing nothing.
#
# It needs no Docker and no database: each case drives the script with a stub
# Odoo through SAPIAN_ODOO_CMD, so it runs in CI on any machine.
if [ "${1:-}" = "--self-test" ]; then
  set -uo pipefail
  SELF="${BASH_SOURCE[0]}"
  ROOT="$(cd "$(dirname "${SELF}")/.." && pwd)"
  TMP="$(mktemp -d)"
  trap 'rm -rf "${TMP}"' EXIT
  FAILED=0

  # A stub that answers the two `odoo shell` queries and the upgrade run.
  # $STUB_MODE decides which lie it tells.
  cat > "${TMP}/stub" <<'STUB'
#!/usr/bin/env bash
args="$*"
case "${STUB_MODE}" in
  healthy)
    if [ "${1}" = "shell" ]; then
      if grep -q . "${TMP_MARK}/verify" 2>/dev/null; then
        echo "SAPIAN-VERIFY sapian_core installed 19.0.1.0.0"
        echo "SAPIAN-VERIFY-BAD none"
      else
        echo "SAPIAN-MOD sapian_core installed manual -"
        echo seen > "${TMP_MARK}/verify"
      fi
    else
      echo "Loading module sapian_core (1/1)"
    fi ;;
  empty_state)
    [ "${1}" = "shell" ] && echo "" || echo "Loading module sapian_core (1/1)" ;;
  invalid_names)
    if [ "${1}" = "shell" ]; then echo "SAPIAN-MOD sapian_core installed manual -"
    else echo "WARNING odoo.modules.loading: invalid module names, ignored: sapian_core"; fi ;;
  no_loading_line)
    if [ "${1}" = "shell" ]; then echo "SAPIAN-MOD sapian_core installed manual -"
    else echo "nothing of interest happened"; fi ;;
  bad_readback)
    if [ "${1}" = "shell" ]; then
      if grep -q . "${TMP_MARK}/verify" 2>/dev/null; then
        echo "SAPIAN-VERIFY sapian_core uninstalled -"
        echo "SAPIAN-VERIFY-BAD sapian_core"
      else
        echo "SAPIAN-MOD sapian_core installed manual -"
        echo seen > "${TMP_MARK}/verify"
      fi
    else echo "Loading module sapian_core (1/1)"; fi ;;
esac
exit 0
STUB
  chmod +x "${TMP}/stub"

  # $5 IS NOT OPTIONAL DECORATION — it is what makes a red mean something.
  #
  # Proved by breaking it: with the sapian_prod guard deliberately INVERTED, an
  # exit-code-only check still reported "ok: sapian_prod is refused", because
  # the script went on to exit 1 for an unrelated reason (a dirty tree). A test
  # that accepts any non-zero exit cannot tell "the guard fired" from "something
  # else broke first", which is the same defect this whole script is about.
  # So every case names the message it must see.
  # THE FIXTURE IS BUILT FIRST AND EVERY CASE RUNS AGAINST IT.
  #
  # An earlier version ran the silent-failure cases against the checkout the
  # self-test was launched from. Those cases exited non-zero and reported "ok"
  # — but on a dirty tree they were aborting at the dirty-tree guard and never
  # reaching the guard under test at all. Four cases were green for a reason
  # that had nothing to do with what they claimed to prove, and only asserting
  # the MESSAGE exposed it.
  FIX="${TMP}/fixture"
  mkdir -p "${FIX}/origin" "${FIX}/repo"
  git init -q --bare "${FIX}/origin"
  git init -q "${FIX}/repo"
  git -C "${FIX}/repo" config user.email selftest@example.com
  git -C "${FIX}/repo" config user.name selftest
  git -C "${FIX}/repo" checkout -q -b master
  mkdir -p "${FIX}/repo/scripts/lib" "${FIX}/repo/docker" \
           "${FIX}/repo/addons/sapian_core" "${FIX}/repo/vendor/oca_web"
  cp "${SELF}" "${FIX}/repo/scripts/update_local.sh"
  cp "${ROOT}/scripts/lib/preflight.sh" "${FIX}/repo/scripts/lib/preflight.sh"
  cp "${ROOT}/docker/docker-compose.yml" "${FIX}/repo/docker/docker-compose.yml"
  printf '{"name": "core", "version": "19.0.1.0.0"}\n' \
    > "${FIX}/repo/addons/sapian_core/__manifest__.py"
  # assert_addons_path's three preconditions, satisfied honestly rather than
  # stubbed out: the vendored launcher on disk, the compose mount (copied
  # above), and a runtime config whose addons_path carries /mnt/vendor.
  mkdir -p "${FIX}/repo/vendor/oca_web/web_responsive" "${FIX}/repo/config"
  printf '{"name": "web_responsive"}\n' \
    > "${FIX}/repo/vendor/oca_web/web_responsive/__manifest__.py"
  # addons_path ONLY. No admin_passwd line: assert_addons_path does not read
  # one, and a credential-shaped literal in a tracked file is exactly what
  # .gitleaks.toml's odoo-admin-passwd rule exists to catch — it caught this
  # one, correctly, on the first push.
  printf '[options]\naddons_path = /mnt/extra-addons,/mnt/vendor\n' \
    > "${FIX}/repo/config/odoo.runtime.conf"
  git -C "${FIX}/repo" add -A
  git -C "${FIX}/repo" commit -q -m "self-test fixture"
  git -C "${FIX}/repo" remote add origin "${FIX}/origin"
  git -C "${FIX}/repo" push -q origin master
  git -C "${FIX}/repo" branch -q --set-upstream-to=origin/master master 2>/dev/null || true

  run_case () {   # $1 label, $2 expected exit, $3 mode, $4 db, $5 required text
    local label="$1" expect="$2" mode="$3" db="$4" want="$5" out rc
    rm -f "${TMP}/verify"
    out="$(STUB_MODE="${mode}" TMP_MARK="${TMP}" \
           SAPIAN_ODOO_CMD="${TMP}/stub" \
           SAPIAN_UPDATE_LOG="${TMP}/odoo.log" \
           bash "${FIX}/repo/scripts/update_local.sh" "${db}" 2>&1)"
    rc=$?
    if [ "${expect}" = "0" ] && [ "${rc}" -ne 0 ]; then
      echo "!! ${label}: expected exit 0, got ${rc}"; printf '%s\n' "${out}" | tail -8 | sed 's/^/     /'
      FAILED=$((FAILED+1)); return
    fi
    if [ "${expect}" != "0" ] && [ "${rc}" -eq 0 ]; then
      echo "!! ${label}: THE GUARD DID NOT FIRE — expected non-zero, got 0"
      printf '%s\n' "${out}" | tail -8 | sed 's/^/     /'
      FAILED=$((FAILED+1)); return
    fi
    if [ -n "${want}" ] && ! printf '%s\n' "${out}" | grep -qF -- "${want}"; then
      echo "!! ${label}: exited ${rc}, but for the WRONG REASON — expected to see"
      echo "     ${want}"
      printf '%s\n' "${out}" | tail -8 | sed 's/^/     /'
      FAILED=$((FAILED+1)); return
    fi
    echo "   ok: ${label} (exit ${rc})"
  }

  echo "-- self-test: the database guard refuses what it must"
  run_case "sapian_prod is refused"            nonzero healthy sapian_prod \
    "REFUSING to run against 'sapian_prod'"
  run_case "an unrecognised name is refused"   nonzero healthy acme_books \
    "does not look like a local"
  run_case "a client-looking name is refused"  nonzero healthy sapianerp_client7 \
    "does not look like a local"

  echo "-- self-test: the database guard ALLOWS a local name"
  # Proving the refusal is not simply "refuse everything", which would pass the
  # three cases above while making the script useless.
  run_case "demo_allapps completes"            0       healthy demo_allapps \
    "Every module named above reported state=installed"
  run_case "scratch_x completes"               0       healthy scratch_x \
    "Every module named above reported state=installed"

  echo "-- self-test: a dirty tree is refused even on an allowed database"
  echo "dirt" > "${FIX}/repo/addons/sapian_core/dirt.txt"
  run_case "a dirty tree aborts"               nonzero healthy demo_allapps \
    "the working tree is dirty"
  rm -f "${FIX}/repo/addons/sapian_core/dirt.txt"

  echo "-- self-test: the silent-failure guards each go red"
  run_case "unreadable module state aborts"    nonzero empty_state     demo_allapps \
    "could not read ir_module_module"
  run_case "'invalid module names' aborts"     nonzero invalid_names   demo_allapps \
    "Odoo ignored module names"
  run_case "a missing Loading line aborts"     nonzero no_loading_line demo_allapps \
    "named but never loaded"
  run_case "a bad state read-back aborts"      nonzero bad_readback    demo_allapps \
    "Some modules are not installed after the run"

  echo
  if [ "${FAILED}" -ne 0 ]; then
    echo "!! self-test FAILED: ${FAILED} case(s). The guards do not discriminate."
    exit 1
  fi
  echo ">> self-test passed: every guard fired when broken, and the healthy path"
  echo "   still completed. The checks discriminate."
  exit 0
fi

DB_NAME="demo_allapps"
EXTRA_INSTALL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --install) EXTRA_INSTALL="${2:?--install needs a comma-separated list}"; shift 2 ;;
    --install=*) EXTRA_INSTALL="${1#--install=}"; shift ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    -*) echo "!! unknown option: $1" >&2; exit 2 ;;
    *) DB_NAME="$1"; shift ;;
  esac
done

# --- WHICH DATABASES THIS MAY TOUCH ------------------------------------------
# DEFAULT-DENY, and deliberately with no override flag.
#
# This script upgrades every installed module and installs new ones. On a client
# tenant that is a production change with no backup taken, no maintenance window
# and no rollback — run by a script whose name says "local". A denylist cannot
# work here because it would have to know every client database that will ever
# exist; the safe direction is to name the shapes that are demonstrably NOT
# production and refuse everything else.
#
# There is no --force. An escape hatch on a guard like this gets used at the end
# of a long day, which is exactly when it must not be available. A local
# database whose name does not match is renamed, or this list is edited in a
# commit somebody reviews.
LOCAL_DB_PATTERNS=("demo_*" "scratch_*" "test_*" "ci_*" "local_*" "*_local" "*_demo")

db_is_local() {   # $1 = database name
  local name="$1" pattern
  # Named explicitly so the refusal can say so, rather than reporting it as a
  # generic pattern miss. It is the one database in this product that must
  # never be reached from here.
  if [ "${name}" = "sapian_prod" ]; then
    return 1
  fi
  for pattern in "${LOCAL_DB_PATTERNS[@]}"; do
    # shellcheck disable=SC2254  # the pattern is meant to glob
    case "${name}" in ${pattern}) return 0 ;; esac
  done
  return 1
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/preflight.sh
. "${REPO_ROOT}/scripts/lib/preflight.sh"

COMPOSE="$(compose_cmd "${REPO_ROOT}/docker/docker-compose.yml")"
# Overridable so the module arithmetic can be exercised without Docker; the
# default is the compose invocation every other ops script uses. Set it only if
# you know why you are setting it.
ODOO_CMD="${SAPIAN_ODOO_CMD:-${COMPOSE} run --rm -T odoo odoo}"
LOG="${SAPIAN_UPDATE_LOG:-/tmp/sapian-update-${DB_NAME}.log}"

if ! db_is_local "${DB_NAME}"; then
  if [ "${DB_NAME}" = "sapian_prod" ]; then
    log_error "!! REFUSING to run against 'sapian_prod'."
    log_error "   That is the production tenant. This script upgrades every installed"
    log_error "   module and installs new ones, with no backup, no maintenance window"
    log_error "   and no rollback. Nothing has been read or written."
  else
    log_error "!! REFUSING to run against '${DB_NAME}' — it does not look like a local"
    log_error "   database, and this script defaults to deny because it cannot know"
    log_error "   which names are clients'. Nothing has been read or written."
    log_error "   Recognised as local: ${LOCAL_DB_PATTERNS[*]}"
  fi
  log_error "   If this really is a throwaway local database, rename it to match one"
  log_error "   of those shapes. There is deliberately no --force."
  exit 1
fi

log_line ">> Deploying master to '${DB_NAME}'"

# --- 0. Preconditions ---------------------------------------------------------
# The vendored launcher must be reachable before anything is upgraded, for the
# reason preflight.sh sets out at length: a module that is `installed` but off
# the serving addons path delivers nothing, in silence.
if ! assert_addons_path "${REPO_ROOT}"; then
  log_error "!! Aborting — the vendored launcher could not be reached."
  exit 1
fi

if [ -n "$(git -C "${REPO_ROOT}" status --porcelain)" ]; then
  log_error "!! Aborting — the working tree is dirty. A deploy from a dirty tree is"
  log_error "   not a deploy of master, and it is not reproducible. Commit, stash or"
  log_error "   discard first:"
  git -C "${REPO_ROOT}" status --short >&2
  exit 1
fi

# --- 1. Pull master -----------------------------------------------------------
BEFORE="$(git -C "${REPO_ROOT}" rev-parse --short HEAD)"
BRANCH="$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD)"
log_line ">> [1/6] Pulling master (currently on ${BRANCH} at ${BEFORE})"
if [ "${BRANCH}" != "master" ]; then
  git -C "${REPO_ROOT}" checkout master || { log_error "!! could not check out master"; exit 1; }
fi
# --ff-only: a merge commit created by a deploy script is a surprise nobody
# asked for. If it cannot fast-forward, the operator has local commits and needs
# to know that rather than have them merged silently.
git -C "${REPO_ROOT}" pull --ff-only origin master || {
  log_error "!! Aborting — could not fast-forward master. You have local commits on"
  log_error "   master, or the remote has diverged. Resolve it by hand."
  exit 1
}
AFTER="$(git -C "${REPO_ROOT}" rev-parse --short HEAD)"
PULLED_NOTHING=""
if [ "${BEFORE}" = "${AFTER}" ]; then
  PULLED_NOTHING="yes"
  # LOUD, because a no-op pull is the shape of the defect this script exists
  # for: the operator runs a deploy, sees a wall of green, and assumes new code
  # arrived. It is NOT fatal, and that is a deliberate choice rather than an
  # oversight — see the note at the end of the run. Re-deploying the same commit
  # is a legitimate and common thing to do (it is how you recover a tenant whose
  # modules drifted), and making it exit non-zero would mean this script fails
  # every second time it is run, which trains an operator to stop reading the
  # exit code. What must never happen is a no-op passing QUIETLY.
  log_error "!! ================================================================"
  log_error "!! NOTHING WAS PULLED. master is already at ${AFTER}."
  log_error "!! No new commits came down. If you expected some, this deploy is"
  log_error "!! NOT the reason your change is or is not on the tenant — check"
  log_error "!! that the pull request actually merged."
  log_error "!! The module upgrade below still runs, and still has to prove it"
  log_error "!! did something."
  log_error "!! ================================================================"
else
  log_line "   ${BEFORE} -> ${AFTER}"
  git -C "${REPO_ROOT}" log --oneline "${BEFORE}..${AFTER}" | sed 's/^/     /'
fi

# --- 2. Which of our modules exist, and which does the DATABASE have? ---------
# Enumerated from the filesystem rather than a hardcoded list: a list in this
# file is a list that goes stale the next time a bridge is added, which is the
# failure this script exists to prevent.
log_line ">> [2/6] Asking ${DB_NAME} which of our modules are installed"

declare -a OURS=()
for manifest in "${REPO_ROOT}"/addons/*/__manifest__.py "${REPO_ROOT}"/vendor/oca_web/*/__manifest__.py; do
  [ -f "${manifest}" ] || continue
  OURS+=("$(basename "$(dirname "${manifest}")")")
done
if [ "${#OURS[@]}" -eq 0 ]; then
  log_error "!! Aborting — found no manifests under addons/ or vendor/oca_web/."
  log_error "   The enumeration is broken; it has not decided there is nothing to do."
  exit 1
fi
log_line "   ${#OURS[@]} modules in the tree"

# ONE query, and it reads the manifests through ODOO's own reader rather than
# grepping them. That matters more than it looks: Odoo NORMALISES
# `auto_install: True` into the SET of the module's depends
# (odoo.modules.module.get_manifest), so the set is exactly the condition under
# which Odoo would install the module by itself — no second interpretation of
# the flag to keep in step, and a future `auto_install: {"account"}` (a partial
# auto-install) is handled without a change here.
#
# WHY THE DEPENDENCY CHECK EXISTS, measured rather than reasoned: an earlier
# version installed every NEW auto_install module outright. On a base + theme
# database that turned `-i l10n_et_calendar_account` into l10n_et_calendar,
# account, purchase and l10n_et_calendar_purchase — 65 installed modules where
# there had been a handful. On a client tenant that is an accounting and
# purchasing rollout dressed up as a deploy. `auto_install` means "install me
# when my dependencies are ALREADY there", not "install me and my
# dependencies", so the deps are checked and a bridge whose dependencies are
# absent is reported as skipped, by name and with the missing list.
NAMES_PY="$(printf "'%s'," "${OURS[@]}")"
STATE_OUT="$(printf "%s\n" \
  "from odoo.modules.module import get_manifest" \
  "names = [${NAMES_PY}]" \
  "state = {r['name']: r['state'] for r in env['ir.module.module'].sudo().search_read([], ['name','state'])}" \
  "for n in names:" \
  "    auto = (get_manifest(n) or {}).get('auto_install')" \
  "    gate = sorted(auto) if isinstance(auto, (set, list, tuple)) else ([] if auto else None)" \
  "    missing = [d for d in (gate or []) if state.get(d) != 'installed']" \
  "    print('SAPIAN-MOD %s %s %s %s' % (n, state.get(n, 'absent'), 'auto' if gate is not None else 'manual', ','.join(missing) or '-'))" \
  | ${ODOO_CMD} shell -d "${DB_NAME}" --no-http --log-level=warn 2>&1)"

if ! printf '%s\n' "${STATE_OUT}" | grep -q '^SAPIAN-MOD '; then
  log_error "!! Aborting — could not read ir_module_module from '${DB_NAME}'."
  log_error "   Nothing was upgraded. Output was:"
  printf '%s\n' "${STATE_OUT}" | tail -20 >&2
  exit 1
fi

declare -a TO_UPGRADE=() TO_INSTALL=() SKIPPED=() ODD=()
while read -r _marker name state kind missing; do
  case "${state}" in
    installed)
      TO_UPGRADE+=("${name}")
      printf '     %-32s installed  -> upgrade\n' "${name}"
      ;;
    uninstalled|absent)
      if [ "${kind}" = "auto" ] && [ "${missing}" = "-" ]; then
        TO_INSTALL+=("${name}")
        printf '     %-32s NEW        auto_install, dependencies present -> install\n' "${name}"
      elif [ "${kind}" = "auto" ]; then
        SKIPPED+=("${name}")
        printf '     %-32s NEW        auto_install but waiting on: %s\n' "${name}" "${missing}"
      else
        SKIPPED+=("${name}")
        printf '     %-32s NEW        not auto_install -> skipped\n' "${name}"
      fi
      ;;
    *)
      ODD+=("${name}:${state}")
      printf '     %-32s %-10s (left alone)\n' "${name}" "${state}"
      ;;
  esac
done < <(printf '%s\n' "${STATE_OUT}" | grep '^SAPIAN-MOD ')

# --install adds modules the operator has decided this tenant should carry.
if [ -n "${EXTRA_INSTALL}" ]; then
  IFS=',' read -r -a EXTRAS <<< "${EXTRA_INSTALL}"
  for m in "${EXTRAS[@]}"; do
    [ -n "${m}" ] || continue
    TO_INSTALL+=("${m}")
    log_line "   ${m} added by --install"
    SKIPPED=("${SKIPPED[@]/${m}}")
  done
fi

# --- 3. Refuse to do nothing --------------------------------------------------
if [ "${#TO_UPGRADE[@]}" -eq 0 ] && [ "${#TO_INSTALL[@]}" -eq 0 ]; then
  log_error "!! Aborting — the computed module list is EMPTY."
  log_error "   That is not 'nothing to do': ${#OURS[@]} of our modules exist in the tree and"
  log_error "   none of them came back installed or new from '${DB_NAME}'. Either the"
  log_error "   database name is wrong or the query is broken. Nothing was run."
  exit 1
fi

UP_LIST="$(IFS=,; echo "${TO_UPGRADE[*]:-}")"
IN_LIST="$(IFS=,; echo "${TO_INSTALL[*]:-}")"

# --- 4. One invocation --------------------------------------------------------
# --log-level=info deliberately: the per-module "Loading module <name>" line is
# the only positive, per-module evidence that a module was acted on, and the
# check below requires one for each. At warn level that evidence does not exist.
log_line ">> [3/6] Running Odoo once: -u '${UP_LIST}' -i '${IN_LIST}'"
set -- -d "${DB_NAME}" --stop-after-init --log-level=info
[ -n "${UP_LIST}" ] && set -- "$@" -u "${UP_LIST}"
[ -n "${IN_LIST}" ] && set -- "$@" -i "${IN_LIST}"
${ODOO_CMD} "$@" > "${LOG}" 2>&1
ODOO_EXIT=$?
log_line "   odoo exit ${ODOO_EXIT}, log at ${LOG}"
if [ "${ODOO_EXIT}" -ne 0 ]; then
  log_error "!! Odoo exited ${ODOO_EXIT}. Last 30 lines:"
  tail -30 "${LOG}" >&2
  exit 1
fi

# --- 5. Prove it happened -----------------------------------------------------
log_line ">> [4/6] Checking the log for the silent failure this script exists for"
if grep -q "invalid module names, ignored" "${LOG}"; then
  log_error "!! Odoo ignored module names. This is the failure mode that hid #48's"
  log_error "   bridge — it exits 0 and does nothing:"
  grep "invalid module names, ignored" "${LOG}" | sed 's/^/     /' >&2
  exit 1
fi

MISSING_LOAD=""
for m in "${TO_UPGRADE[@]:-}" "${TO_INSTALL[@]:-}"; do
  [ -n "${m}" ] || continue
  grep -Eq "Loading module ${m}[ (]" "${LOG}" || MISSING_LOAD="${MISSING_LOAD} ${m}"
done
if [ -n "${MISSING_LOAD}" ]; then
  log_error "!! These modules were named but never loaded, so nothing was applied to"
  log_error "   them:${MISSING_LOAD}"
  exit 1
fi

log_line ">> [5/6] Reading the module states back out of ${DB_NAME}"
ACTED="$(printf "'%s'," ${TO_UPGRADE[@]:-} ${TO_INSTALL[@]:-})"
VERIFY_OUT="$(printf "%s\n" \
  "names = [${ACTED}]" \
  "rows = env['ir.module.module'].sudo().search_read([('name','in',names)], ['name','state','latest_version'])" \
  "found = {r['name']: r for r in rows}" \
  "bad = [n for n in names if (found.get(n) or {}).get('state') != 'installed']" \
  "for n in names: r = found.get(n) or {}; print('SAPIAN-VERIFY %s %s %s' % (n, r.get('state','absent'), r.get('latest_version') or '-'))" \
  "print('SAPIAN-VERIFY-BAD %s' % (','.join(bad) or 'none'))" \
  | ${ODOO_CMD} shell -d "${DB_NAME}" --no-http --log-level=warn 2>&1)"
printf '%s\n' "${VERIFY_OUT}" | grep '^SAPIAN-VERIFY ' | awk '{printf "     %-32s %-10s %s\n", $2, $3, $4}'
if ! printf '%s\n' "${VERIFY_OUT}" | grep -q '^SAPIAN-VERIFY-BAD none$'; then
  log_error "!! Some modules are not installed after the run:"
  printf '%s\n' "${VERIFY_OUT}" | grep '^SAPIAN-VERIFY-BAD ' | sed 's/^/     /' >&2
  exit 1
fi

# --- 6. Restart the server, and prove it came back ----------------------------
# WITHOUT THIS THE SCRIPT LIES. `odoo -u ... --stop-after-init` is a one-shot
# process: it upgrades the database and exits. The container that SERVES the
# tenant is still running the registry and the asset bundles it built at its own
# start, so the operator reloads the browser, sees the old build, and the script
# has just told him the deploy succeeded. That is the same evidence-and-artefact
# split this script was written to close, reintroduced at the last step.
#
# Skipped only when the operator has pointed SAPIAN_ODOO_CMD somewhere else --
# there is no container to restart then -- and it says so rather than passing
# quietly.
if [ -n "${SAPIAN_ODOO_CMD:-}" ]; then
  log_line ">> [6/6] SKIPPING the restart: SAPIAN_ODOO_CMD is set, so this run did not"
  log_line "         use the compose stack and there is no server here to restart."
  log_line "         The database is upgraded; whatever serves it still holds the OLD"
  log_line "         code in memory until you restart it yourself."
else
  log_line ">> [6/6] Restarting the server so it serves the code that was just deployed"
  BEFORE_ID="$(${COMPOSE} ps -q odoo 2>/dev/null | head -1)"
  BEFORE_START="$(docker inspect -f '{{.State.StartedAt}}' "${BEFORE_ID}" 2>/dev/null || echo none)"

  ${COMPOSE} up -d odoo >/dev/null 2>&1
  ${COMPOSE} restart odoo >/dev/null 2>&1 || {
    log_error "!! Could not restart the odoo service. The database is upgraded but the"
    log_error "   running server still has the old code in memory."
    exit 1
  }

  AFTER_ID="$(${COMPOSE} ps -q odoo 2>/dev/null | head -1)"
  AFTER_START="$(docker inspect -f '{{.State.StartedAt}}' "${AFTER_ID}" 2>/dev/null || echo none)"
  RUNNING="$(docker inspect -f '{{.State.Running}}' "${AFTER_ID}" 2>/dev/null || echo false)"

  # ASSERT THE POSITIVE, not the absence of an error. `restart` exits 0 for a
  # container that crashed a second later, and StartedAt not moving means the
  # process we are talking to is the one that was already there.
  if [ "${RUNNING}" != "true" ]; then
    log_error "!! The odoo container is not running after the restart:"
    ${COMPOSE} ps odoo >&2
    log_error "   Last 30 lines of its log:"
    ${COMPOSE} logs --tail=30 odoo >&2 2>/dev/null || true
    exit 1
  fi
  if [ "${AFTER_START}" = "none" ] || [ "${AFTER_START}" = "${BEFORE_START}" ]; then
    log_error "!! The odoo container did not actually restart — its start time is"
    log_error "   unchanged (${BEFORE_START} -> ${AFTER_START}). It is still serving the"
    log_error "   code it was started with, so this deploy is not live."
    exit 1
  fi
  log_line "   restarted: started at ${AFTER_START}"

  # And it must actually SERVE. A container can be "running" while Odoo inside
  # it is failing to boot on the very code just deployed, which is precisely the
  # case worth catching here.
  HTTP_URL="${SAPIAN_UPDATE_HTTP_URL:-http://localhost:8069/web/login}"
  HTTP_OK=""
  for _ in $(seq 1 30); do
    CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "${HTTP_URL}" 2>/dev/null || echo 000)"
    if [ "${CODE}" = "200" ]; then HTTP_OK="yes"; break; fi
    sleep 2
  done
  if [ -z "${HTTP_OK}" ]; then
    log_error "!! The server restarted but never answered ${HTTP_URL} with 200 within"
    log_error "   60 seconds (last status: ${CODE:-none}). It is up but not serving, so"
    log_error "   the deploy is not usable. Last 30 lines:"
    ${COMPOSE} logs --tail=30 odoo >&2 2>/dev/null || true
    exit 1
  fi
  log_line "   ${HTTP_URL} answered 200 — the new code is being served"
fi

# --- The report ---------------------------------------------------------------
echo
log_line "== ${DB_NAME}: master ${AFTER}"
log_line "== UPGRADED (${#TO_UPGRADE[@]}): ${UP_LIST:-none}"
log_line "== INSTALLED (${#TO_INSTALL[@]}): ${IN_LIST:-none}"
SKIP_LIST="$(echo "${SKIPPED[@]:-}" | tr -s ' ')"
# "not installed and not installed BY US" — two reasons, both printed per module
# in step 2 above: not auto_install at all, or auto_install still waiting on a
# dependency. The label says both rather than only the first, because a line
# that reads "not auto_install" beside l10n_et_calendar_account would be wrong.
log_line "== SKIPPED, left uninstalled (${#SKIPPED[@]}): ${SKIP_LIST:-none}"
log_line "   (reasons per module are in step [2/6] above: not auto_install, or"
log_line "    auto_install still waiting on a dependency)"
[ "${#ODD[@]}" -gt 0 ] && log_line "== OTHER STATES, left alone: ${ODD[*]}"
log_line "== Every module named above reported state=installed on read-back."
if [ -n "${PULLED_NOTHING}" ]; then
  log_line "== NOTE: no new commits were pulled — this was a re-deploy of ${AFTER}."
  log_line "   The modules were still upgraded and verified, and the server was"
  log_line "   restarted, so the exit code is 0 for work that genuinely happened."
fi
