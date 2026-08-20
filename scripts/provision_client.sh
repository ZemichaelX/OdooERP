#!/usr/bin/env bash
# Provision a new client instance: create the DB and install the base + chosen
# modules, landing the company on the Ethiopian chart of accounts ('et').
# Usage: ./scripts/provision_client.sh <db_name> [comma,separated,modules]
#
# Why two phases (this is the fix for the "company ends up on generic_coa" bug):
# Odoo auto-loads a chart of accounts the moment `account` installs, choosing by
# the company's COUNTRY. A brand-new DB's company has no country, so it gets the
# generic chart — and Odoo won't let you switch charts afterwards. So we:
#   1. create the DB with `base` only (no accounting, no chart yet),
#   2. set the company country to Ethiopia,
#   3. install the real modules — now `account` sees an Ethiopian company and
#      loads the 'et' chart automatically, and the l10n_et_* loaders apply the
#      payroll accounts / WHT / VAT defaults on top.
# The chosen MODULES must include an Ethiopian localization (l10n_et_*) so the
# 'et' chart template exists; the default set does.
set -euo pipefail

DB_NAME="${1:?usage: provision_client.sh <db_name> [modules]}"
# sapian_theme is in the DEFAULT set, not an upsell.
#
# It stopped being decoration: it now carries the de-branding (the login
# page says "Powered by SapianERP" and not "Powered by Odoo", on the login
# page AND on the customer portal), the login layout, the app rail that
# makes the app icons visible on desktop at all, the support contact, and
# the backend footer. A tenant provisioned without it is handed Odoo — with
# a link to odoo.com on the page their staff open every morning.
#
# Pass a second argument to override the whole list, as before.
# web_responsive joins the default set for the same reason sapian_theme did.
# It is the product's NAVIGATION: without it Odoo 19's desktop apps menu is a
# plain text dropdown and login lands on the Module Catalog, so a tenant
# provisioned without it opens on a configuration screen every morning. It is
# vendored at a pinned commit (vendor/README.md) and its per-user defaults are
# applied in phase 5 below — installing it is not enough on its own.
MODULES="${2:-sapian_core,sapian_theme,web_responsive,l10n_et_base,l10n_et_payroll,l10n_et_reports,sapian_landing}"
COUNTRY_CODE="${SAPIAN_COUNTRY:-et}"   # override for a non-Ethiopian tenant
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/preflight.sh
. "${REPO_ROOT}/scripts/lib/preflight.sh"

# The -f path goes through compose_cmd so the HOST path is in the form
# docker can open on Windows (see scripts/lib/preflight.sh).
COMPOSE="$(compose_cmd "${REPO_ROOT}/docker/docker-compose.yml")"

# --- Master password (admin_passwd) --------------------------------------------
# The database-manager master password protects DB create/drop/backup. It must
# be a strong, per-tenant secret and must NEVER be committed (A10). Secrets go
# in config/odoo.runtime.conf — the gitignored copy of the tracked template
# config/odoo.conf.example — which is what docker-compose actually mounts.
# ensure_runtime_conf creates that copy, replaces the CHANGEME placeholder with
# a generated secret, prints it ONCE for the vault, and refuses to continue if
# the placeholder survives. Idempotent: a real password from an earlier
# provision is left untouched.
if ! ensure_runtime_conf "${REPO_ROOT}"; then
  echo "!! Aborting — config/odoo.runtime.conf is not usable." >&2
  exit 1
fi

echo ">> Provisioning client DB: ${DB_NAME}"
echo ">> Country: ${COUNTRY_CODE} | Modules: ${MODULES}"

# --- Phase 1: create the DB with base only (no chart yet) ----------------------
# FAIL CLOSED, BEFORE ANYTHING IS BUILT — same reason as build_demo.sh. A
# tenant handed over with the launcher "installed" but undelivered is worse
# than one without it: the config line says it is there.
if ! assert_addons_path "${REPO_ROOT}"; then
  echo "!! Aborting before phase 1 — the vendored launcher could not be reached." >&2
  exit 1
fi

echo ">> [1/6] Creating database (base only)..."
$COMPOSE run --rm odoo \
  odoo -d "${DB_NAME}" -i base --without-demo=all --stop-after-init

# --- Phase 2: set the company country BEFORE any chart loads -------------------
echo ">> [2/6] Setting company country to '${COUNTRY_CODE}'..."
printf "%s\n" \
  "company = env['res.company'].search([], limit=1)" \
  "country = env['res.country'].search([('code','=','${COUNTRY_CODE}'.upper())], limit=1)" \
  "company.country_id = country" \
  "env.cr.commit()" \
  "print('>> country set to', company.country_id.code)" \
  | $COMPOSE run --rm -T odoo odoo shell -d "${DB_NAME}" --no-http

# --- Phase 3: install the real modules — 'et' chart auto-loads now -------------
echo ">> [3/6] Installing modules (chart auto-loads for the country)..."
$COMPOSE run --rm odoo \
  odoo -d "${DB_NAME}" -i "${MODULES}" --without-demo=all --stop-after-init

# --- Phase 4: close public sign-up -----------------------------------------
# Odoo's default for "Customer Account" is b2c — FREE SIGN UP — declared on
# res.config.settings.auth_signup_uninvited (auth_signup/models/
# res_config_settings.py:13). On a private company ERP that puts "Don't have an
# account?" on the login page of every client we provision.
#
# b2b = invitation only. Existing users can still be sent a signup link, a
# stranger cannot make themselves one.
#
# THIS WRITE IS NO LONGER WHAT KEEPS THE TENANT CLOSED, and that matters more
# than the write does. `sapian_theme_auth_signup` (and `sapian_theme_website`
# once `website` is on) override res.users._get_signup_invitation_scope() and
# serve b2b unless sapian_theme.allow_public_signup is set — read on every
# request, so a database that never ran this script is closed too. A backup
# restored onto a new host, a second database created from the database
# manager, or a tenant provisioned before this phase existed all used to be
# open; measured in CI, job "A stranger cannot get an account".
#
# It is still written, for two reasons: Settings > General should not read
# "Free sign up" on a tenant where sign-up is closed, and an operator who opts
# in with allow_public_signup should get b2b rather than Odoo's b2c.
#
# The parameter KEY is read off Odoo's own field rather than typed in: the
# setting is called auth_signup_uninvited and stores itself under
# auth_signup.invitation_scope, and a literal of either name is a string that
# can silently stop matching.
#
# AND THE READ-BACK IS THE EFFECTIVE SCOPE, not the parameter. Reading back what
# you just wrote proves the write, which nobody doubted; the parameter stopped
# being the authority the moment `website` was installed, and a check that kept
# reading it was green on a database whose login page offered free sign-up.
# _get_signup_invitation_scope() is the method the login controller itself calls.
echo ">> [4/6] Closing public sign-up (invitation only)..."
SIGNUP_OUT="$(printf "%s\n" \
  "field = env['res.config.settings']._fields.get('auth_signup_uninvited')" \
  "key = getattr(field, 'config_parameter', None) or 'auth_signup.invitation_scope'" \
  "env['ir.config_parameter'].sudo().set_param(key, 'b2b')" \
  "env.cr.commit()" \
  "print('SIGNUP %s=%s' % (key, env['ir.config_parameter'].sudo().get_param(key)))" \
  "print('SIGNUP effective=%s' % env['res.users']._get_signup_invitation_scope())" \
  | $COMPOSE run --rm -T odoo odoo shell -d "${DB_NAME}" --no-http 2>&1)"
printf '%s\n' "${SIGNUP_OUT}" | grep -E '^SIGNUP ' || true
if ! printf '%s\n' "${SIGNUP_OUT}" | grep -q '^SIGNUP effective=b2b$'; then
  echo "!! Public sign-up is NOT closed on ${DB_NAME} — the login page will offer" >&2
  echo "   account creation to anyone who can reach it. The value the served" >&2
  echo "   page honours is what was read back, and it is not b2b." >&2
  exit 1
fi

# --- Phase 5: the launcher this tenant's users actually land on --------------
# Installing web_responsive is NOT enough, and the reason is measured rather
# than argued: the admin was created back in phase [1/6] by `-i base`, at which
# point `is_redirect_home` does not exist on res.users, so sapian_theme's
# product default never sees it and web_responsive's column default (False,
# 'milk') wins. The only user this tenant is handed over with would land on the
# Module Catalog, in Odoo's lilac — see
# addons/sapian_theme/models/res_users.py.
#
# This is provisioning, not a migration: it is called by name, it moves only
# users still on web_responsive's own defaults, and it prints the count, so a
# run that moved nobody is distinguishable from a run that worked.
echo ">> [5/6] Putting this tenant's users on the app launcher..."
LAUNCHER_OUT="$(printf "%s\n" \
  "moved = env['res.users']._sapian_apply_launcher_defaults(dry_run=False)" \
  "env.cr.commit()" \
  "print('LAUNCHER moved=%d' % len(moved))" \
  | $COMPOSE run --rm -T odoo odoo shell -d "${DB_NAME}" --no-http 2>&1)"
printf '%s\n' "${LAUNCHER_OUT}" | grep -E '^LAUNCHER ' || true
if ! printf '%s\n' "${LAUNCHER_OUT}" | grep -qE '^LAUNCHER moved=[0-9]+$'; then
  echo "!! The launcher defaults step never reported on ${DB_NAME}. It did not run," >&2
  echo "   so this tenant's users may still land on a configuration screen." >&2
  exit 1
fi

# --- Phase 6: the login page and the launcher this tenant actually serves -----
# THE SAME CHECK build_demo.sh RUNS, from the same file. A config line saying
# `-i sapian_theme` is exactly what an unthemed tenant would also have: the
# demo was verified from the served bytes for a week while the thing we sell
# was verified from nothing at all, and the gap was a client login page still
# carrying Odoo's footer. Verify the artefact, never the config line.
echo ">> [6/6] Verifying the login page and launcher this tenant serves..."
if ! verify_login_page "${COMPOSE}" "${DB_NAME}" "${REPO_ROOT}"; then
  echo "!! ${DB_NAME} does not serve a SapianERP-branded login page. Do not hand" >&2
  echo "   this tenant over." >&2
  exit 1
fi

# THE SAME CHECK build_demo.sh RUNS, from the same file — see verify_launcher
# in scripts/lib/preflight.sh.
if ! verify_launcher "${COMPOSE}" "${DB_NAME}" "${REPO_ROOT}"; then
  echo "!! ${DB_NAME} will not put its users on the app launcher. Do not hand this" >&2
  echo "   tenant over — it opens on a configuration screen." >&2
  exit 1
fi

# Acceptance: a client database must carry no demo content. This replaces the
# implicit guard that existed while the demo tenant shipped in demo/ (see
# scripts/check_no_demo_modules.sh). The rest of the acceptance check is
# still outstanding.
echo ">> Acceptance check: no demo modules on the new database..."
"${REPO_ROOT}/scripts/check_no_demo_modules.sh" "${DB_NAME}"

echo ">> Done. The company is on the '${COUNTRY_CODE}' chart of accounts."
echo ">> Next: configure company profile/branding/roles via the onboarding wizard,"
echo ">>       set the fiscal year + TIN, import master data from data-templates/,"
echo ">>       and confirm scripts/backup.sh is scheduled."
