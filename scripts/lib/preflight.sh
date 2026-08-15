#!/usr/bin/env bash
# Shared preconditions and Windows path handling for the ops scripts.
# Source it; do not execute it.
#
# Why this exists: backup.sh produced seven 0-byte "backups" over two weeks
# because Docker Desktop was not running. The dump failed, but the shell's `>`
# redirect had already created the destination file, and nothing reached the
# operator. Checking that the stack is actually reachable BEFORE touching the
# filesystem removes the whole class: no daemon, no file, no silence.

# Timestamped log lines. The original backup log had none, so diagnosing a
# fortnight of failures meant guessing against file mtimes.
log_line() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

log_error() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2
}

# compose_cmd <path-to-compose-file>
#
# Echo the compose invocation with a HOST path docker can actually open.
#
# On Git Bash, ${REPO_ROOT} is a POSIX path (/c/Users/...). docker.exe is a
# native Windows binary and resolves that against the current drive as
# C:\c\Users\... — "The system cannot find the path specified". MSYS normally
# converts such arguments on the way out, but these scripts used to disable
# conversion wholesale (MSYS2_ARG_CONV_EXCL='*') to protect CONTAINER paths
# like /var/lib/odoo/filestore, and the blanket took the -f host path with it.
# The exclusion is now scoped to the container paths that need it (see the
# callers), and the host path is converted explicitly here so it does not
# depend on MSYS heuristics, which differ between Git-for-Windows releases.
# cygpath -m yields C:/Users/... (forward slashes), which docker accepts and
# which survives word-splitting unlike a backslash form. No-op off Windows.
compose_cmd() {
  local compose_file="$1"
  if command -v cygpath >/dev/null 2>&1; then
    compose_file="$(cygpath -m "${compose_file}")"
  fi
  printf 'docker compose -f %s' "${compose_file}"
}

# require_docker_stack <compose-command> [service ...]
#
# Fails (returns 1) unless the Docker daemon answers AND every named compose
# service is running. Callers must check the return value and exit non-zero
# WITHOUT creating any backup artefact.
#
# NOTE: stderr from the probes is REPORTED, never discarded. An earlier version
# sent it to /dev/null and a broken -f path surfaced only as "service 'db' is
# not running" — the true error ("open C:\c\Users\...: The system cannot find
# the path specified") was swallowed. Suppressing the stream that carries the
# reason is the same silent-failure disease these scripts exist to remove.
require_docker_stack() {
  local compose="$1"
  shift

  local probe
  # `2>&1 >/dev/null` captures STDERR only: `docker info` prints pages of client
  # information to stdout even when the daemon is unreachable, and burying the
  # one useful line under it is its own small act of hiding the reason.
  # --format keeps it to a single server field, so success is quiet.
  if ! probe="$(docker info --format '{{.ServerVersion}}' 2>&1 >/dev/null)"; then
    log_error "!! Docker daemon is not reachable — is Docker Desktop running?"
    printf '%s\n' "${probe}" | head -3 | sed 's/^/     /' >&2
    return 1
  fi

  local running
  # `compose ps --status running --services` prints the service names that are
  # up. A non-zero exit here means compose itself failed (bad -f path, bad
  # file, no project) — a different fault from "the service is down", and the
  # operator needs to see which.
  if ! running="$(${compose} ps --status running --services 2>&1)"; then
    log_error "!! 'docker compose ps' FAILED — compose could not read the project:"
    printf '%s\n' "${running}" | sed 's/^/     /' >&2
    log_error "!! (command was: ${compose} ps --status running --services)"
    return 1
  fi

  local service
  for service in "$@"; do
    if ! printf '%s\n' "${running}" | grep -qx "${service}"; then
      log_error "!! Compose service '${service}' is not running — start the stack first."
      log_error "!! Services currently running: ${running:-<none>}"
      return 1
    fi
  done
  return 0
}

# ensure_runtime_conf <repo-root>
#
# Guarantee config/odoo.runtime.conf exists AND carries a real master password.
# Returns 1 on any problem; callers must abort.
#
# compose mounts config/odoo.runtime.conf, which is gitignored and therefore
# absent on a fresh clone. If a compose command ever ran before the file
# existed, docker created that path as a DIRECTORY — both cases are detected
# here so the documented path can't strand the operator on a mount error.
#
# The password part is not decoration. config/odoo.conf.example is TRACKED, so
# it ships the placeholder `admin_passwd = CHANGEME`. A plain copy would
# therefore produce a runtime config that HAS an admin_passwd line — which is
# exactly what the old "already set, leaving it unchanged" test looked for — and
# every instance would silently run with the master password `CHANGEME`. That is
# the do-nothing-and-pass shape: the guard would be green precisely because the
# work had not happened. So the placeholder is treated as UNSET, a secret is
# generated, and the function fails hard if CHANGEME survives.
ensure_runtime_conf() {
  local repo_root="$1"
  local runtime="${repo_root}/config/odoo.runtime.conf"
  local template="${repo_root}/config/odoo.conf.example"

  if [ -d "${runtime}" ]; then
    log_error "!! ${runtime} is a DIRECTORY (docker created it before the file existed)."
    log_error "!! Remove it (rm -rf config/odoo.runtime.conf) and re-run — it will be recreated from config/odoo.conf.example."
    return 1
  fi

  if [ ! -f "${template}" ]; then
    log_error "!! Template ${template} is missing — cannot create the runtime config."
    return 1
  fi

  if [ ! -f "${runtime}" ]; then
    log_line ">> Creating config/odoo.runtime.conf from config/odoo.conf.example."
    cp "${template}" "${runtime}" || {
      log_error "!! Could not copy ${template} to ${runtime}."
      return 1
    }
  fi

  # A placeholder or an empty value both count as "no password set".
  if grep -qE '^[[:space:]]*admin_passwd[[:space:]]*=[[:space:]]*(CHANGEME)?[[:space:]]*$' "${runtime}"; then
    local pw
    pw="$(head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-40)"
    if [ "${#pw}" -lt 32 ]; then
      log_error "!! Could not generate a 32+ character master password (got ${#pw})."
      return 1
    fi
    # sed -i differs between GNU and BSD; rewrite via a temp file so the script
    # behaves the same on Git Bash, macOS and Linux.
    local tmp="${runtime}.tmp.$$"
    sed "s|^[[:space:]]*admin_passwd[[:space:]]*=.*$|admin_passwd = ${pw}|" "${runtime}" > "${tmp}" \
      && mv "${tmp}" "${runtime}" || {
      rm -f "${tmp}"
      log_error "!! Could not write the generated master password into ${runtime}."
      return 1
    }
    log_line "============================================================"
    log_line ">> Generated database master password (admin_passwd) for this instance:"
    log_line ">>     ${pw}"
    log_line ">> Written to config/odoo.runtime.conf. STORE IT IN YOUR VAULT NOW — shown once."
    log_line "============================================================"
  fi

  # Assert the positive: a real value is present. Never trust the absence of an
  # error above.
  if ! grep -qE '^[[:space:]]*admin_passwd[[:space:]]*=[[:space:]]*[^[:space:]]{16,}[[:space:]]*$' "${runtime}"; then
    log_error "!! ${runtime} has no usable admin_passwd (needs 16+ non-blank characters)."
    return 1
  fi
  if grep -qE '^[[:space:]]*admin_passwd[[:space:]]*=[[:space:]]*CHANGEME[[:space:]]*$' "${runtime}"; then
    log_error "!! ${runtime} still carries the CHANGEME placeholder as its master password."
    return 1
  fi
  return 0
}

# verify_login_page <compose-command> <db-name> <repo-root>
#
# Assert that the login page THIS DATABASE serves is ours: branded button in
# every state, our attribution and not Odoo's, no public sign-up offer, and a
# support contact that reaches the page if one is configured.
#
# ONE DEFINITION, called by build_demo.sh and provision_client.sh. It lived
# inline in build_demo.sh only, and the consequence was that the demo was
# checked while the thing we actually sell was not: a client provisioned
# without sapian_theme served Odoo's own footer and nothing said so.
#
# Returns 0 when everything holds, 1 otherwise, printing the CHECK lines either
# way so an operator can see what was measured rather than only that it failed.
verify_login_page() {
  local compose="$1" db="$2" repo_root="$3"
  local out failed=0

  out="$(${compose} run --rm -T odoo odoo shell -d "${db}" --no-http --stop-after-init \
         < "${repo_root}/scripts/lib/check_login_page.py" 2>&1 || true)"
  printf '%s\n' "${out}" | grep -E '^(CHECK|NOTE) ' || true

  _login_check() {  # <grep pattern> <what went wrong>
    if ! printf '%s\n' "${out}" | grep -q "$1"; then
      log_error "!! $2"
      failed=1
    fi
  }

  # Ordered so "did it render at all" comes first: every absence check below is
  # meaningless on an empty page.
  _login_check '^CHECK theme=installed$' \
    "sapian_theme is NOT installed on '${db}', so this tenant has Odoo's login"$'\n'"   page, Odoo's footer and no app rail. The theme carries the de-branding;"$'\n'"   a tenant without it is being handed Odoo."
  _login_check '^CHECK login_http=200$' \
    "The login page did not return 200. Nothing below was checked on a real page."

  local bytes
  bytes="$(printf '%s\n' "${out}" | sed -n 's/^CHECK login_bytes=//p' | tr -d '\r')"
  if [ -z "${bytes}" ] || [ "${bytes}" -lt 2000 ]; then
    log_error "!! The login page came back at ${bytes:-0} bytes — too small to be the real"$'\n'"   page, and small enough that every 'must not contain' check would pass"$'\n'"   by having nothing in it."
    failed=1
  fi

  local expected rgb
  expected="$(printf '%s\n' "${out}" | sed -n 's/^CHECK brand_expected=//p' | tr -d '\r')"
  rgb="$(printf '%s\n' "${out}" | sed -n 's/^CHECK brand_expected_rgb=//p' | tr -d '\r')"
  if [ -z "${expected}" ]; then
    log_error "!! Could not read the brand colour from sapian_theme — the theme is not"$'\n'"   importable, so none of the colour checks below actually ran."
    failed=1
  else
    _login_check "^CHECK login_primary=${expected}\$" \
      "The sign-in button is not the brand colour. The frontend bundle never"$'\n'"   consults \$o-brand-primary — see sapian_frontend.scss."
    _login_check "^CHECK login_disabled=${expected}\$" \
      "The sign-in button's DISABLED colour is not the brand — which is the"$'\n'"   colour it turns the moment somebody clicks it, because login.js adds"$'\n'"   \`disabled\` while the request is in flight."
    _login_check "^CHECK login_focus_rgb=${rgb}\$" \
      "The sign-in button's FOCUS RING is not the brand. Anyone who tabs into"$'\n'"   the form sees Odoo purple."
  fi

  _login_check '^CHECK login_powered_sapian=1$' \
    "The login footer does not say 'Powered by SapianERP'. The page a client"$'\n'"   opens every morning is unsigned — or still signed by somebody else."
  _login_check '^CHECK login_mark=1$' \
    "The Sapian mark is not on the login page beside the attribution."
  _login_check '^CHECK login_odoo_refs=0$' \
    "The login page still attributes the product to Odoo, or still links to"$'\n'"   odoo.com."
  _login_check '^CHECK login_signup=0$' \
    "The login page offers ACCOUNT CREATION to anonymous visitors."
  _login_check '^CHECK login_signup_scope=b2b$' \
    "Public sign-up is not invitation-only on this database. Odoo's default is"$'\n'"   b2c — free sign up."

  # The support contact is per-deployment, so it is NOT required to be set.
  # What is required is that a configured one reaches the page: that turns the
  # check into something meaningful on a demo (which sets one) and on a fresh
  # client tenant (which has not been told the number yet) alike.
  if printf '%s\n' "${out}" | grep -q '^CHECK login_support_configured=1$'; then
    _login_check '^CHECK login_support_rendered=1$' \
      "A support contact IS configured but does not appear in the served page."
  else
    log_line ">> NOTE no support contact configured on '${db}' — the login page and the"
    log_line ">>      backend footer will show no way to get help. Set one with:"
    log_line ">>      ${compose} run --rm -T odoo odoo shell -d ${db} --no-http --stop-after-init <<<\\"
    log_line ">>        \"env['ir.config_parameter'].sudo().set_param('sapian_theme.support_contact', '+251 ...'); env.cr.commit()\""
  fi

  unset -f _login_check
  return "${failed}"
}

# ---------------------------------------------------------------------------
# verify_launcher <compose-command> <db-name> <repo-root>
#
# Assert that THIS DATABASE will actually put a user on the app launcher, in
# the house brand, when they log in.
#
# ONE DEFINITION, called by build_demo.sh and provision_client.sh — the same
# arrangement as verify_login_page, and for the same reason. Installing
# web_responsive is exactly what a tenant that lands on the Module Catalog
# would also have in its config: the module owns the field, but the admin of a
# demo or a client tenant is created in the `-i base` phase BEFORE the module
# exists, so the product default never reaches the one user who is in every
# screen recording. Measured, not assumed — see
# addons/sapian_theme/models/res_users.py. Verify the artefact, never the
# config line.
#
# The RENDERED proof (a browser logging in and seeing a teal launcher) lives in
# sapian_theme's browser tests and the launcher-defaults CI job. This is the
# part a provisioning script can prove without a browser, and it is the part
# that breaks.
#
# Returns 0 when everything holds, 1 otherwise, printing the CHECK lines either
# way so an operator can see what was measured rather than only that it failed.
verify_launcher() {
  local compose="$1" db="$2" repo_root="$3"
  local out failed=0

  out="$(${compose} run --rm -T odoo odoo shell -d "${db}" --no-http --stop-after-init \
         < "${repo_root}/scripts/lib/check_launcher.py" 2>&1 || true)"
  printf '%s\n' "${out}" | grep -E '^CHECK ' || true

  _launcher_check() {  # <grep pattern> <what went wrong>
    if ! printf '%s\n' "${out}" | grep -q "$1"; then
      log_error "!! $2"
      failed=1
    fi
  }

  # 1. Does the module exist to the asset pipeline at all? `state = installed`
  #    with `_init_modules` False is the exact defect this file was rewritten
  #    for: the row is in the database and the module is invisible to
  #    ir.asset, silently.
  _launcher_check '^CHECK launcher_module=installed$' \
    "web_responsive is NOT installed on '${db}', so there is no app launcher."
  _launcher_check '^CHECK launcher_in_init_modules=True$' \
    "web_responsive is installed in the DATABASE but was not loaded by this"$'\n'"   process — it is not on its addons path, so ir.asset skips its manifest"$'\n'"   entirely and NONE of its JavaScript or CSS is delivered. No error is"$'\n'"   raised for this. Check addons_path in config/odoo.runtime.conf and the"$'\n'"   ../vendor/oca_web:/mnt/vendor mount in docker/docker-compose.yml, then"$'\n'"   RESTART the serving container — a running server keeps its own path."

  # 2. Did we actually fetch the backend page? An unauthenticated fetch serves
  #    web.assets_frontend and would report a confident zero for everything
  #    below it.
  _launcher_check '^CHECK launcher_page_http=200$' \
    "The backend page did not return 200, so nothing below was measured on a"$'\n'"   real page."
  local bundles
  bundles="$(printf '%s\n' "${out}" | sed -n 's/^CHECK launcher_backend_js_bundles=//p' | tr -d '\r')"
  if [ -z "${bundles}" ] || [ "${bundles}" -lt 1 ]; then
    log_error "!! No backend JS bundle was served — the fetch did not reach the web"$'\n'"   client, so a clean result here would mean nothing."
    failed=1
  fi

  # 3. THE ASSERTION THAT MATTERS: the launcher's own module, by name, in the
  #    bytes the browser is served. Byte size does not catch this — in the
  #    reproduced failure the bundle was still 6.4 MB with zero web_responsive
  #    modules in it.
  _launcher_check '^CHECK launcher_js_named=True$' \
    "The launcher component is NOT in the JavaScript this database serves."$'\n'"   The apps grid will be Odoo's stock dropdown and login will land on a"$'\n'"   configuration screen, with a clean browser console."
  local modules
  modules="$(printf '%s\n' "${out}" | sed -n 's/^CHECK launcher_js_modules=//p' | tr -d '\r')"
  modules="${modules:-0}"
  if [ "${modules}" -lt 10 ]; then
    log_error "!! Only ${modules} web_responsive JS modules reached the bundle (expected"$'\n'"   at least 10). The port is partly delivered, which is worse than absent."
    failed=1
  fi

  # 4. CSS, asserted SEPARATELY from ours, so neither can stand in for the
  #    other. In the reproduced failure sapian_theme's CSS was present and
  #    correct while web_responsive's was entirely absent — the page looked
  #    branded and had no launcher.
  _launcher_check '^CHECK launcher_css_web_responsive=True$' \
    "web_responsive's stylesheet is not in the CSS this database serves."
  _launcher_check '^CHECK launcher_css_sapian_theme=True$' \
    "sapian_theme's stylesheet is not in the CSS this database serves — the"$'\n'"   app rail cannot render."

  # 5. The users this tenant is handed over with.
  _launcher_check '^CHECK launcher_users_not_redirected=0$' \
    "Internal users on '${db}' will NOT land on the app launcher — see the"$'\n'"   CHECK launcher_not_redirected_logins line above. Apply the defaults with:"$'\n'"   env['res.users']._sapian_apply_launcher_defaults(dry_run=False)"
  _launcher_check '^CHECK launcher_users_not_branded=0$' \
    "Internal users on '${db}' get the launcher in web_responsive's lilac"$'\n'"   rather than the house brand — see CHECK launcher_not_branded_logins."

  # 5b. THE HOME ACTION, which outranks both of the settings above and is not
  #     visible in either of them. `res.users.action_id` reaches the client as
  #     session_info['home_action_id']; the action service falls back to it when
  #     the URL carries no action, loadState() then returns true, and
  #     WebClient.loadRouterState skips _loadDefaultApp — the only method
  #     web_responsive patches and the only place is_redirect_home is read.
  #     Measured: the launcher paints correctly, and 357 ms later the client is
  #     on /odoo/action-<home>. Both checks above are green throughout.
  _launcher_check '^CHECK launcher_home_action_on_wire=false$' \
    "The page this database serves carries a HOME ACTION in session_info, so"$'\n'"   the client will load it and leave the launcher a second after login —"$'\n'"   with the two checks above still green. See CHECK"$'\n'"   launcher_home_action_logins. Clear it with:"$'\n'"   env['res.users']._sapian_apply_launcher_defaults(dry_run=False)"
  _launcher_check '^CHECK launcher_users_with_home_action=0$' \
    "Internal users on '${db}' carry a home action, which takes the screen"$'\n'"   away from the launcher on login — see CHECK launcher_home_action_logins."

  # 6. The colour, read out of the delivered stylesheet.
  local expected community milk
  expected="$(printf '%s\n' "${out}" | sed -n 's/^CHECK brand_expected=//p' | tr -d '\r')"
  community="$(printf '%s\n' "${out}" | sed -n 's/^CHECK launcher_community_colour=//p' | tr -d '\r')"
  milk="$(printf '%s\n' "${out}" | sed -n 's/^CHECK launcher_milk_colour=//p' | tr -d '\r')"
  if [ -z "${expected}" ]; then
    log_error "!! Could not read the brand colour from sapian_theme — the theme is not"$'\n'"   importable, so the launcher colour was not actually checked."
    failed=1
  elif [ "${community}" != "$(printf '%s' "${expected}" | tr 'a-f' 'A-F')" ]; then
    log_error "!! The launcher background in the served bundle is '${community}', not the"$'\n'"   brand '${expected}'. The demo or tenant opens on somebody else's colour."
    failed=1
  fi
  if [ "${community}" != "ABSENT" ] && [ -n "${milk}" ] && [ "${milk}" = "${community}" ]; then
    log_error "!! The 'milk' and 'community' launcher themes compile to the SAME colour"$'\n'"   (${milk}), so the brand check above cannot tell them apart."
    failed=1
  fi

  unset -f _launcher_check
  return "${failed}"
}

# ---------------------------------------------------------------------------
# assert_addons_path <repo-root>
#
# Fail BEFORE anything is built if the vendor tree cannot reach the server.
#
# WHY THIS RUNS FIRST.
# A module that is `state = installed` in the database but absent from the
# serving process's addons path is skipped by ir.asset in complete silence:
# `_fill_asset_paths` iterates `registry._init_modules`, so the manifest is
# never read, no warning is logged and no exception is raised. The database
# says installed, the browser gets nothing, and the console is clean. Measured
# on one database with two processes: 16 JS files with the vendor dir on the
# path, 0 without it, `state = installed` both times.
#
# Discovering that at phase 5 — or, worse, in a client's browser — costs a whole
# build. Discovering it as "invalid module names, ignored" twenty seconds in is
# barely better, because that line is a warning nobody is watching for. These
# are three file reads and they run before phase 1.
#
# Returns 1 on any problem; callers must abort.
assert_addons_path() {
  local repo_root="$1"
  local runtime="${repo_root}/config/odoo.runtime.conf"
  local compose_file="${repo_root}/docker/docker-compose.yml"
  local module_dir="${repo_root}/vendor/oca_web/web_responsive"
  local mount_point="/mnt/vendor"
  local failed=0

  # 1. The module is on disk where the mount expects it. `check_vendor.sh`
  #    proves it is the RIGHT code; this only proves it is there at all, which
  #    is the part the mount depends on.
  if [ ! -f "${module_dir}/__manifest__.py" ]; then
    log_error "!! ${module_dir}/__manifest__.py is missing. The vendored launcher is not"$'\n'"   in the working tree, so nothing can mount it. See vendor/README.md."
    failed=1
  fi

  # 2. compose actually mounts it. Matched on the mapping, not on the word
  #    'vendor' appearing somewhere in the file.
  if [ ! -f "${compose_file}" ]; then
    log_error "!! ${compose_file} is missing."
    failed=1
  elif ! grep -qE '^\s*-\s*\.\./vendor/oca_web:'"${mount_point}"'(:ro)?\s*$' "${compose_file}"; then
    log_error "!! docker/docker-compose.yml does not mount ../vendor/oca_web at ${mount_point}."$'\n'"   Add it to the odoo service's volumes, beside ../addons."
    failed=1
  fi

  # 3. THE ONE THAT ACTUALLY BIT. config/odoo.runtime.conf is gitignored and is
  #    only ever created from the template when MISSING — so an instance set up
  #    before the vendor tree existed keeps an addons_path without it, forever,
  #    while config/odoo.conf.example (tracked, and the file everyone reads)
  #    looks correct.
  if [ ! -f "${runtime}" ]; then
    log_error "!! ${runtime} is missing — run ensure_runtime_conf first."
    failed=1
  else
    local configured
    configured="$(sed -n 's/^[[:space:]]*addons_path[[:space:]]*=[[:space:]]*//p' "${runtime}" | tail -1 | tr -d '\r')"
    if [ -z "${configured}" ]; then
      log_error "!! config/odoo.runtime.conf declares no addons_path at all."
      failed=1
    elif ! printf '%s' "${configured}" | tr ',' '\n' | sed 's/[[:space:]]//g' | grep -qx "${mount_point}"; then
      log_error "!! config/odoo.runtime.conf's addons_path does NOT contain ${mount_point}:"$'\n'"     ${configured}"$'\n'"   The launcher would install and then deliver no JavaScript at all, with"$'\n'"   no error anywhere. This file is gitignored, so fixing the tracked"$'\n'"   template is not enough — fix the runtime copy:"$'\n'"     addons_path = /mnt/extra-addons,${mount_point},/usr/lib/python3/dist-packages/odoo/addons"$'\n'"   and RESTART the stack, because a running server keeps its own path."
      failed=1
    fi
  fi

  [ "${failed}" -eq 0 ] && log_line ">> addons_path carries ${mount_point}; the vendored launcher can be loaded."
  return "${failed}"
}
