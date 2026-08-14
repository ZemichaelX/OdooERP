#!/usr/bin/env bash
# Build a SapianERP sales-demo database FROM NOTHING, with Odoo demo data OFF.
# Usage: ./scripts/build_demo.sh <db_name> [demo_module]
#   demo_module   defaults to sapian_demo_trader (building materials).
#                 Pass sapian_demo_pharma for the pharma pitch once that
#                 module is converted to the same data/ pattern.
#
# WHY IT IS PHASED, and why not just `-i <module> --with-demo`:
# Odoo's own demo data ships US placeholder companies and a website bound to
# the wrong company — a prospect must never see a US company list in software
# sold as Ethiopian. So demo data stays OFF and the tenant ships as module
# data. But with demo off the single company is created on generic_coa with
# country US, and Odoo does NOT allow switching charts afterwards; so the
# country must be set BEFORE the accounting modules install. That is the same
# two-phase dance scripts/provision_client.sh does for a real client — which
# means recording the demo is a rehearsal of the actual deployment.
#
# Result: exactly ONE company, Selam General Trading PLC, on the 'et' chart.
set -euo pipefail
export MSYS2_ARG_CONV_EXCL='/var/lib/odoo'

DB_NAME="${1:?usage: build_demo.sh <db_name> [demo_module]}"
DEMO_MODULE="${2:-sapian_demo_trader}"
# The provisioning model each demo module exposes.
case "${DEMO_MODULE}" in
  sapian_demo_trader) DEMO_MODEL="sapian.demo.trader" ;;
  sapian_demo_pharma) DEMO_MODEL="sapian.demo.pharma" ;;
  *) echo "!! Unknown demo module '${DEMO_MODULE}'." >&2; exit 1 ;;
esac
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/preflight.sh
. "${REPO_ROOT}/scripts/lib/preflight.sh"
COMPOSE="$(compose_cmd "${REPO_ROOT}/docker/docker-compose.yml")"

if ! ensure_runtime_conf "${REPO_ROOT}"; then
  log_error "!! Aborting — config/odoo.runtime.conf is not usable."
  exit 1
fi
if ! require_docker_stack "${COMPOSE}" db; then
  log_error "!! Aborting — the stack is not available."
  exit 1
fi

log_line ">> [1/5] Dropping '${DB_NAME}' and creating it with base only (no demo data)..."
${COMPOSE} exec -T db psql -U odoo -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid<>pg_backend_pid();" >/dev/null
${COMPOSE} exec -T db dropdb -U odoo --if-exists "${DB_NAME}"
${COMPOSE} run --rm odoo odoo -d "${DB_NAME}" -i base --without-demo=all --stop-after-init

log_line ">> [2/5] Setting the company country to Ethiopia (before any chart loads)..."
printf "%s\n" \
  "company = env['res.company'].search([], limit=1)" \
  "company.country_id = env.ref('base.et')" \
  "env.cr.commit()" \
  "print('>> country set to', company.country_id.code)" \
  | ${COMPOSE} run --rm -T odoo odoo shell -d "${DB_NAME}" --no-http

# sapian_theme is installed WITH the demo module, and it is not optional.
#
# Without it the demo a prospect sees is Odoo purple with no app rail — in the
# same session where the pitch claims white-labelling. That is the same defect
# as the tenant rendering Odoo's default logo, one layer up: the product on
# screen is not the product being described. It went unnoticed for a week
# because nothing checked, which is why step [5/5] below now reads the COMPILED
# stylesheet rather than trusting this line.
#
# It is listed here rather than added to sapian_demo_trader's `depends`: the
# theme is a product module a client may or may not buy, and the demo tenant
# must not force it into every database that installs the demo module. What the
# BUILD does is a build decision.
log_line ">> [3/5] Installing ${DEMO_MODULE} + sapian_theme (the 'et' chart loads onto that company)..."
${COMPOSE} run --rm odoo odoo -d "${DB_NAME}" -i "${DEMO_MODULE}",sapian_theme \
  --without-demo=all --stop-after-init

# Provisioning runs AFTER the install completes, never during it: module data
# loads mid-install, and a company charted at that point collides with the
# account module's end-of-load chart auto-install hook.
log_line ">> [4/5] Provisioning the tenant (adopting the existing company)..."
printf "%s\n" \
  "company = env['${DEMO_MODEL}']._provision_demo_tenant(adopt_existing=True)" \
  "env.cr.commit()" \
  "print('>> provisioned:', company.name, '| chart:', company.chart_template)" \
  | ${COMPOSE} run --rm -T odoo odoo shell -d "${DB_NAME}" --no-http

# The acceptance checks, asserted rather than suggested. Both of these have
# silently regressed before: the company list picked up Odoo's US placeholders,
# and the UoM setting was left off so the quintal/bag conversion — the demo's
# headline moment — was invisible on every form. A build that fails either is
# not a demo you can record, so it exits non-zero here instead of on camera.
log_line ">> [5/5] Verifying the built database..."
# A heredoc rather than the old printf-joined one-liners: the brand checks need
# real statements, and a verification nobody can read is a verification nobody
# maintains.
VERIFY_OUT="$(${COMPOSE} run --rm -T odoo odoo shell -d "${DB_NAME}" --no-http 2>&1 <<'PYEOF' || true
import re

companies = env['res.company'].search([('name', '!=', False)])
print('CHECK companies=%d' % len(companies))
print('CHECK charts=%s' % ','.join(c.chart_template or 'none' for c in companies))
print('CHECK names=%s' % ' | '.join(companies.mapped('name')))
on = env.ref('uom.group_uom') in env.ref('base.group_user').all_implied_ids
print('CHECK group_uom=%s' % on)

# ---- the brand, read out of the COMPILED stylesheet ------------------------
# Not "is sapian_theme in the install list" — that is the config line that was
# already there and still produced a purple demo. These read the bytes a
# browser would be served.
#
# The expected value comes from sapian_theme.brand, which reads the one
# declaration in sapian_variables.scss, so a re-brand moves this check with the
# product instead of stranding a stale hex in a shell script.
from odoo.addons.sapian_theme import brand   # noqa: E402
BRAND = brand.brand_primary()
print('CHECK brand_expected=%s' % BRAND)
theme = env['ir.module.module'].search([('name', '=', 'sapian_theme')], limit=1)
print('CHECK theme=%s' % (theme.state if theme else 'missing'))


def bundle_css(name):
    """The compiled CSS a browser would be served for ``name``.

    `_get_asset_bundle(...).css()` COMPILES and stores; `_generate_asset_links`
    does not, and on a freshly built database (where nobody has loaded a page
    yet) it leaves the attachment absent — which read as "the brand is missing"
    when the brand was fine. Measured: every CHECK below came back ABSENT on
    the first themed build.
    """
    attachment = env['ir.qweb']._get_asset_bundle(name, css=True, js=False).css()
    return (attachment.raw or b'').decode('utf-8', 'ignore') if attachment else ''


def first(css, pattern):
    found = re.findall(pattern, css)
    return found[0] if found else 'ABSENT'


def brand_rgb(hexcolour):
    """'#14454F' -> '20, 69, 79', the form Bootstrap's focus ring uses."""
    value = hexcolour.lstrip('#')
    return ', '.join(str(int(value[i:i + 2], 16)) for i in (0, 2, 4))


print('CHECK brand_expected_rgb=%s' % brand_rgb(BRAND))

backend = bundle_css('web.assets_web')
frontend = bundle_css('web.assets_frontend')
print('CHECK backend_primary=%s' % first(backend, r'--primary: (#[0-9A-Fa-f]{6});'))
print('CHECK backend_navbar=%s'
      % first(backend, r'\.o_main_navbar\{background-color: (#[0-9A-Fa-f]{6})'))
login_rule = first(frontend, r'(\.oe_login_form \.btn-primary\{[^}]*\})')
print('CHECK login_primary=%s' % first(login_rule, r'--btn-bg: (#[0-9A-Fa-f]{6})'))
# EVERY STATE, not just the resting one. --btn-bg was already asserted and was
# already correct while the button turned Odoo purple the moment you clicked it:
# web/static/src/public/login.js adds `disabled` on submit, and an unset
# --btn-disabled-bg falls through to Odoo's own colour. The focus ring is the
# same shape of miss. See sapian_frontend.scss.
print('CHECK login_disabled=%s' % first(login_rule, r'--btn-disabled-bg: (#[0-9A-Fa-f]{6})'))
print('CHECK login_focus_rgb=%s' % first(login_rule, r'--btn-focus-shadow-rgb: ([0-9]+, [0-9]+, [0-9]+)'))
print('CHECK rail_css=%s'
      % bool(re.search(r'\.o_web_client:has\(\.o_sapian_rail\)\{padding-left', backend)))
# REPORTED, not checked — a known open item kept in front of whoever builds a
# demo rather than filed away. The FRONTEND bundle's :root --primary is still
# Odoo's #714B67: html_editor (auto_install) rebuilds Bootstrap's $theme-colors
# from the website editor's palette and $o-brand-primary is never consulted
# there. The login BUTTON is branded by an explicit rule in
# sapian_frontend.scss, which is what CHECK login_primary above asserts.
print('NOTE frontend_root_primary=%s (Odoo default; see sapian_frontend.scss)'
      % first(frontend, r'--primary: (#[0-9A-Fa-f]{6});'))

# ---- the LOGIN PAGE, as an anonymous visitor is served it ------------------
# THIS IS THE GAP THAT LET THREE CLIENT-FACING DEFECTS THROUGH.
#
# Every check above this line talks to the database or to a compiled asset.
# None of them asks what comes back on the wire. So the build could report
# `login_primary=#14454F` — correctly — while the page that colour was on said
# "Powered by Odoo", offered a stranger an account, and showed no support
# number. All three were found by a human opening the page.
#
# Rendered through Odoo's own WSGI application rather than over a socket:
# `werkzeug.test.Client(odoo.http.root)` runs the real dispatcher, the real
# routing, the real session and the real QWeb, and returns exactly the bytes a
# browser would get — with no port to bind, no background container to reap and
# no behavioural difference on Windows, where these scripts are run from Git
# Bash. The request carries no session cookie, so it is served as the anonymous
# visitor a prospect is.
from werkzeug.test import Client                    # noqa: E402
from odoo.http import root as http_root             # noqa: E402

login_response = Client(http_root).get('/web/login', headers={'Host': 'localhost'})
login_html = login_response.get_data(as_text=True)
print('CHECK login_http=%s' % login_response.status_code)
# A zero-length page satisfies every "must not contain" below. Assert the size
# first, so absence can only be measured on a page that actually rendered.
print('CHECK login_bytes=%d' % len(login_html))
print('CHECK login_odoo_refs=%d'
      % (login_html.count('odoo.com') + login_html.count('Powered by <span>Odoo')))
print('CHECK login_powered_sapian=%d' % login_html.count('Powered by SapianERP'))
print('CHECK login_mark=%d' % login_html.count('o_sapian_mark'))
print('CHECK login_signup=%d' % login_html.count('/web/signup'))
support = env['ir.config_parameter'].sudo().get_param('sapian_theme.support_contact') or ''
print('CHECK login_support_configured=%d' % bool(support))
print('CHECK login_support_rendered=%d' % (bool(support) and support in login_html))
scope_field = env['res.config.settings']._fields.get('auth_signup_uninvited')
scope_key = getattr(scope_field, 'config_parameter', None) or 'auth_signup.invitation_scope'
print('CHECK login_signup_scope=%s'
      % (env['ir.config_parameter'].sudo().get_param(scope_key) or 'unset'))

# The rail's data precondition: one tile per root app, every one with an icon.
# The RENDERED assertion lives in sapian_theme's browser tests; this is the
# part a build script can prove without a browser, and it is the part that
# breaks when a new app ships without an icon.
menus = env['ir.ui.menu'].load_web_menus(False)
apps = menus['root']['children']
iconless = [menus[a]['name'] for a in apps if not menus[a].get('webIconData')]
print('CHECK rail_apps=%d' % len(apps))
print('CHECK rail_iconless=%d' % len(iconless))
if iconless:
    print('CHECK rail_iconless_names=%s' % ', '.join(iconless))
PYEOF
)"

printf '%s\n' "${VERIFY_OUT}" | grep -E '^(CHECK|NOTE) ' || true
verify_failed=0
check() {  # check <grep pattern> <what went wrong>
  if ! printf '%s\n' "${VERIFY_OUT}" | grep -q "$1"; then
    log_error "!! $2"
    verify_failed=1
  fi
}
check '^CHECK companies=1$' \
  "Expected exactly ONE active company. A prospect must never see a US"$'\n'"   placeholder in the company switcher — see the CHECK names line above."
check '^CHECK charts=et$' \
  "The company is not on the Ethiopian chart 'et'. Odoo cannot switch charts"$'\n'"   afterwards, so this database has to be rebuilt, not repaired."
check '^CHECK group_uom=True$' \
  "Settings > Inventory > 'Units of Measure & Packagings' is OFF, so Odoo"$'\n'"   hides every unit field and the quintal->bag conversion is invisible."
check '^CHECK theme=installed$' \
  "sapian_theme is NOT installed, so the demo is Odoo purple with no app rail"$'\n'"   — in the session where the pitch claims white-labelling."

# The brand comparisons are done in shell against the value the theme itself
# reports, so a re-brand needs no edit here.
BRAND_EXPECTED="$(printf '%s\n' "${VERIFY_OUT}" | sed -n 's/^CHECK brand_expected=//p' | tr -d '\r')"
if [ -z "${BRAND_EXPECTED}" ]; then
  log_error "!! Could not read the brand colour from sapian_theme — the theme is"$'\n'"   not importable, so nothing below was actually checked."
  verify_failed=1
else
  # ASSERT THE POSITIVE, never "the purple is absent". Odoo's brand purple
  # #714B67 still appears ~13 times in a CORRECTLY themed backend bundle
  # (html_editor palettes and friends), so "must not contain #714B67" fails on
  # a good build. What matters is that the three rules a prospect actually sees
  # carry OUR colour. Unthemed, they read #71639e.
  check "^CHECK backend_primary=${BRAND_EXPECTED}\$" \
    "The backend --primary is not the brand. Every primary button in the demo"$'\n'"   is Odoo purple — see the CHECK backend_primary line above."
  check "^CHECK backend_navbar=${BRAND_EXPECTED}\$" \
    "The backend navbar is not the brand colour. It is in every frame of a"$'\n'"   screen recording."
  check "^CHECK login_primary=${BRAND_EXPECTED}\$" \
    "The LOGIN page's sign-in button is not the brand colour. The frontend"$'\n'"   bundle never consults \$o-brand-primary — see sapian_frontend.scss."
  check "^CHECK login_disabled=${BRAND_EXPECTED}\$" \
    "The sign-in button's DISABLED colour is not the brand — which is the"$'\n'"   colour it turns the moment a prospect clicks it, because login.js adds"$'\n'"   \`disabled\` while the request is in flight."
  BRAND_RGB="$(printf '%s\n' "${VERIFY_OUT}" | sed -n 's/^CHECK brand_expected_rgb=//p' | tr -d '\r')"
  check "^CHECK login_focus_rgb=${BRAND_RGB}\$" \
    "The sign-in button's FOCUS RING is not the brand. Keyboard users and"$'\n'"   anyone who tabs into the form see Odoo purple."
fi

# ---- the login page as a visitor is served it -------------------------------
# Ordered so the "did it render at all" checks come first: every absence check
# below them is meaningless on an empty page.
check '^CHECK login_http=200$' \
  "The login page did not return 200. Nothing below this line was checked on"$'\n'"   a real page."
LOGIN_BYTES="$(printf '%s\n' "${VERIFY_OUT}" | sed -n 's/^CHECK login_bytes=//p' | tr -d '\r')"
if [ -z "${LOGIN_BYTES}" ] || [ "${LOGIN_BYTES}" -lt 2000 ]; then
  log_error "!! The login page came back at ${LOGIN_BYTES:-0} bytes — too small to be the"$'\n'"   real page, and small enough that every 'must not contain' check below"$'\n'"   would pass by having nothing in it."
  verify_failed=1
fi
check '^CHECK login_powered_sapian=1$' \
  "The login footer does not say 'Powered by SapianERP'. The page a client"$'\n'"   opens every morning is unsigned — or still signed by somebody else."
check '^CHECK login_mark=1$' \
  "The Sapian mark is not on the login page beside the attribution."
check '^CHECK login_odoo_refs=0$' \
  "The login page still attributes the product to Odoo, or still links to"$'\n'"   odoo.com. See sapian_theme/views/login_templates.xml."
check '^CHECK login_signup=0$' \
  "The login page offers ACCOUNT CREATION to anonymous visitors. Odoo's"$'\n'"   default for 'Customer Account' is b2c (free sign up) — see the"$'\n'"   CHECK login_signup_scope line above; it must read b2b."
check '^CHECK login_signup_scope=b2b$' \
  "Public sign-up is not set to invitation-only on this database."
check '^CHECK login_support_configured=1$' \
  "No support contact is configured, so sapian_theme renders nothing —"$'\n'"   which is exactly how a feature with a passing test shipped invisible."
check '^CHECK login_support_rendered=1$' \
  "A support contact IS configured but does not appear in the served page."
check '^CHECK rail_css=True$' \
  "The app rail's CSS is not in the served backend bundle, so the rail cannot"$'\n'"   render and the app icons stay invisible on desktop."
check '^CHECK rail_iconless=0$' \
  "At least one root app has no icon, so the rail draws a blank tile for it"$'\n'"   — see the CHECK rail_iconless_names line above."
if [ "${verify_failed}" -ne 0 ]; then
  log_error "!! Demo database '${DB_NAME}' FAILED verification — do not record it."
  exit 1
fi

log_line ">> Done. Demo database '${DB_NAME}' is ready and verified."
log_line ">>   Log in with admin / admin — deliberate for a local demo."
