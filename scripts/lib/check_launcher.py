# -*- coding: utf-8 -*-
"""What the BROWSER is actually served for the app launcher. Read by `odoo shell`.

ONE DEFINITION, called by build_demo.sh and provision_client.sh through
`verify_launcher` in preflight.sh — the same arrangement as check_login_page.py.

WHY THIS FILE WAS REWRITTEN
---------------------------
Its first version asked the server which files it *resolves* into the bundle and
whether a CSS class appeared in a compiled attachment. Every one of those checks
passed on a demo where NOT ONE LINE of web_responsive's JavaScript reached the
browser: the apps grid opened Odoo's stock dropdown, login landed on the Module
Catalog, and `[...odoo.loader.modules.keys()].filter(k => k.includes(
'web_responsive'))` returned `[]` with a clean console.

The cause, reproduced: `ir.asset._fill_asset_paths` reads manifests with

    for addon in addons:                       # addons <- _get_installed_addons_list()
        for command in Manifest.for_addon(addon)['assets'].get(bundle, ()):

and `_get_installed_addons_list()` returns `registry._init_modules` — the
modules THIS PROCESS loaded into its graph, which requires them to be on THIS
PROCESS's addons path. A module that is `state = installed` in the database but
absent from the serving process's addons path is skipped there in total
silence: no warning, no exception, no failed module. Measured on one database,
two processes:

    with the vendor dir on the path:     web_responsive js=16 css=15
    without it:                          web_responsive js=0  css=0
                                         ir_module_module.state = installed
                                         sapian_theme css=4   (still branded!)

So the old checks were not merely weak, they were reading a DIFFERENT PROCESS
from the one the browser talks to: they run inside `docker compose run --rm`,
a fresh container with the correct configuration, while the user's browser is
served by the long-running container. Two processes, one database, opposite
answers, and the check believed the wrong one.

WHAT IT DOES NOW
----------------
It authenticates as admin, fetches the backend bundle the webclient actually
loads, and looks in the bytes:

  * `@web_responsive/components/apps_menu/apps_menu.esm` present BY NAME in the
    delivered JavaScript — that module IS the launcher, so its absence is the
    defect and its presence cannot be faked by a stylesheet;
  * web_responsive's CSS and sapian_theme's CSS asserted SEPARATELY, so neither
    can stand in for the other;
  * `web_responsive in registry._init_modules`, the variable that actually
    decides whether any of the above can happen, reported outright.

`werkzeug.test.Client(odoo.http.root)` is the same real-dispatcher technique
check_login_page.py uses. It is still in-process, which is why
`assert_addons_path` runs in build_demo.sh BEFORE phase 1: that is what catches
a serving container configured differently from the build.
"""

import re

import odoo
from odoo.http import root as http_root
from odoo.service import security
from werkzeug.test import Client

from odoo.addons.sapian_theme import brand

# The launcher component itself. Named exactly, because "some web_responsive
# file is in there" is the assertion that was already passing while the feature
# did not exist.
LAUNCHER_MODULE = "@web_responsive/components/apps_menu/apps_menu.esm"
WEB_RESPONSIVE_CSS_MARKER = "o_grid_apps_menu"   # web_responsive/apps_menu.scss
SAPIAN_THEME_CSS_MARKER = "o_sapian_rail"        # sapian_theme/sapian_rail.scss
MILK_RGB = "#e9e6f9"

# ---- 1. what the database says, and what THIS PROCESS actually loaded -------
module = env["ir.module.module"].search([("name", "=", "web_responsive")], limit=1)
print("CHECK launcher_module=%s" % (module.state if module else "missing"))

# The decisive variable. `state = installed` with this False is exactly the
# defect: the module exists in the database and does not exist to the asset
# pipeline.
init_modules = env.registry._init_modules
print("CHECK launcher_in_init_modules=%s" % ("web_responsive" in init_modules))

# ---- 2. the users this tenant is handed over with --------------------------
users = env["res.users"].with_context(active_test=False).search([("share", "=", False)])
print("CHECK launcher_users=%d" % len(users))
if "is_redirect_home" in env["res.users"]._fields:
    off = users.filtered(lambda u: not u.is_redirect_home)
    lilac = users.filtered(lambda u: u.apps_menu_theme != "community")
    print("CHECK launcher_users_not_redirected=%d" % len(off))
    print("CHECK launcher_users_not_branded=%d" % len(lilac))
    if off:
        print("CHECK launcher_not_redirected_logins=%s" % ", ".join(sorted(off.mapped("login"))))
    if lilac:
        print("CHECK launcher_not_branded_logins=%s" % ", ".join(sorted(lilac.mapped("login"))))
else:
    # Its own value, so "0 users are missing it" cannot be produced by a
    # database where the field does not exist at all.
    print("CHECK launcher_users_not_redirected=NOFIELD")
    print("CHECK launcher_users_not_branded=NOFIELD")

print("CHECK brand_expected=%s" % brand.brand_primary())

# ---- 3. the artefact the browser is served ---------------------------------
admin = env.ref("base.user_admin")
session = http_root.session_store.new()
session.update(odoo.http.get_default_session(), db=env.cr.dbname)
session.uid = admin.id
session.login = admin.login
session.session_token = security.compute_session_token(session, env)
session.context = dict(env["res.users"].with_user(admin).context_get())
http_root.session_store.save(session)

client = Client(http_root)
client.set_cookie("session_id", session.sid, domain="localhost")
headers = {"Host": "localhost"}

page = client.get("/odoo", headers=headers, follow_redirects=True)
html = page.get_data(as_text=True)
print("CHECK launcher_page_http=%s" % page.status_code)
print("CHECK launcher_page_bytes=%d" % len(html))

js_urls = re.findall(r'src="(/web/assets/[^"]*\.js)"', html)
css_urls = re.findall(r'(?:href|data-src)="(/web/assets/[^"]*\.css)"', html)
# The backend bundle, not the frontend one: an unauthenticated page serves
# web.assets_frontend and would report a confident zero for everything below.
backend_js = [u for u in js_urls if "assets_web" in u]
backend_css = [u for u in css_urls if "assets_web.min.css" in u]
print("CHECK launcher_backend_js_bundles=%d" % len(backend_js))
print("CHECK launcher_backend_css_bundles=%d" % len(backend_css))

js_body = "".join(client.get(u, headers=headers).get_data(as_text=True) for u in backend_js)
css_body = "".join(client.get(u, headers=headers).get_data(as_text=True) for u in backend_css)
print("CHECK launcher_js_bytes=%d" % len(js_body))
print("CHECK launcher_css_bytes=%d" % len(css_body))

modules = sorted(set(re.findall(r"@web_responsive/[A-Za-z0-9_/.-]+", js_body)))
print("CHECK launcher_js_modules=%d" % len(modules))
print("CHECK launcher_js_named=%s" % (LAUNCHER_MODULE in modules))
if not modules:
    print("CHECK launcher_js_none_delivered=1")

# Asserted separately, so a green from one cannot be a green for the other.
print("CHECK launcher_css_web_responsive=%s" % (WEB_RESPONSIVE_CSS_MARKER in css_body))
print("CHECK launcher_css_sapian_theme=%s" % (SAPIAN_THEME_CSS_MARKER in css_body))


def theme_colour(theme):
    match = re.search(
        r"\.o_grid_apps_menu\[data-theme=.?%s.?\]\{[^}]*linear-gradient\([^)]*?(#[0-9A-Fa-f]{3,8})"
        % theme,
        css_body,
    )
    return match.group(1) if match else "ABSENT"


print("CHECK launcher_community_colour=%s" % theme_colour("community").upper())
print("CHECK launcher_milk_colour=%s" % theme_colour("milk").upper())
