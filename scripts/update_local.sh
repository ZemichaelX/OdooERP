#!/usr/bin/env bash
# Deploy the current master to a local tenant: pull, then upgrade what is
# installed and install what is new, in one Odoo invocation.
#
# Usage: ./scripts/update_local.sh [db_name] [--install mod1,mod2]
#        db_name defaults to demo_allapps.
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
#     it named reports state=installed.
# Each of those can only be satisfied by the work actually happening.
set -uo pipefail

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

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/preflight.sh
. "${REPO_ROOT}/scripts/lib/preflight.sh"

COMPOSE="$(compose_cmd "${REPO_ROOT}/docker/docker-compose.yml")"
# Overridable so the module arithmetic can be exercised without Docker; the
# default is the compose invocation every other ops script uses. Set it only if
# you know why you are setting it.
ODOO_CMD="${SAPIAN_ODOO_CMD:-${COMPOSE} run --rm -T odoo odoo}"
LOG="${SAPIAN_UPDATE_LOG:-/tmp/sapian-update-${DB_NAME}.log}"

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
log_line ">> [1/5] Pulling master (currently on ${BRANCH} at ${BEFORE})"
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
if [ "${BEFORE}" = "${AFTER}" ]; then
  log_line "   master already at ${AFTER} (nothing pulled)"
else
  log_line "   ${BEFORE} -> ${AFTER}"
  git -C "${REPO_ROOT}" log --oneline "${BEFORE}..${AFTER}" | sed 's/^/     /'
fi

# --- 2. Which of our modules exist, and which does the DATABASE have? ---------
# Enumerated from the filesystem rather than a hardcoded list: a list in this
# file is a list that goes stale the next time a bridge is added, which is the
# failure this script exists to prevent.
log_line ">> [2/5] Asking ${DB_NAME} which of our modules are installed"

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
log_line ">> [3/5] Running Odoo once: -u '${UP_LIST}' -i '${IN_LIST}'"
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
log_line ">> [4/5] Checking the log for the silent failure this script exists for"
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

log_line ">> [5/5] Reading the module states back out of ${DB_NAME}"
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
log_line "   (reasons per module are in step [2/5] above: not auto_install, or"
log_line "    auto_install still waiting on a dependency)"
[ "${#ODD[@]}" -gt 0 ] && log_line "== OTHER STATES, left alone: ${ODD[*]}"
log_line "== Every module named above reported state=installed on read-back."
