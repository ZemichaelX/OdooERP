# -*- coding: utf-8 -*-
"""What this database serves for the app launcher. Read by `odoo shell`.

ONE DEFINITION, called by build_demo.sh and provision_client.sh through
`verify_launcher` in preflight.sh — the same arrangement as
check_login_page.py, and for the same reason: the demo used to be verified from
the served bytes while the thing we actually sell was verified from nothing.

WHAT IS CHECKED HERE, AND WHAT DELIBERATELY IS NOT
--------------------------------------------------
The launcher is an OWL component. `/odoo` serves a bootstrap shell, so no HTTP
client can fetch the rendered grid, and a provisioning script has no browser.
The RENDERED assertion — a real user logging in and landing on a launcher
painted in the brand — lives in sapian_theme's browser tests and the
`launcher-defaults` CI job, which print SAPIAN-LAUNCHER lines from inside the
page.

What a build script CAN prove is everything that decides the outcome, read from
the artefact rather than from the config line that produced it:

  * the module is installed;
  * the users this tenant is handed over with are on the launcher defaults —
    not the config line that was supposed to set them, the stored values;
  * the compiled backend bundle a browser is served carries the launcher's own
    CSS, and the 'community' theme's background carries OUR brand hex. Milk's
    lilac is read out too, so "the brand is present" cannot pass by matching a
    rule that no user's theme selects.

That last one is the same technique the brand checks already use: the bytes,
not the intent.
"""

import re

# ---- 1. is it even installed ----------------------------------------------
module = env["ir.module.module"].search([("name", "=", "web_responsive")], limit=1)
print("CHECK launcher_module=%s" % (module.state if module else "missing"))

# ---- 2. the users this tenant is handed over with --------------------------
# Internal users only; portal/public never see a backend launcher. Archived
# included, because base.template_user is inactive and is what the invite flow
# copies.
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
    # Reported as a distinct value rather than as 0, so "nobody is missing the
    # default" cannot be produced by a database where the field does not exist.
    print("CHECK launcher_users_not_redirected=NOFIELD")
    print("CHECK launcher_users_not_branded=NOFIELD")

# ---- 3. the bytes a browser is served --------------------------------------
from odoo.addons.sapian_theme import brand  # noqa: E402

BRAND = brand.brand_primary()
print("CHECK brand_expected=%s" % BRAND)


def bundle_css(name):
    """The compiled CSS a browser would get for ``name``.

    `.css()` COMPILES and stores; `_generate_asset_links` does not, and on a
    freshly built database nobody has loaded a page yet — which reads as
    "absent" when everything is fine. Same trap as build_demo.sh's own note.
    """
    attachment = env["ir.qweb"]._get_asset_bundle(name, css=True, js=False).css()
    return (attachment.raw or b"").decode("utf-8", "ignore") if attachment else ""


backend = bundle_css("web.assets_web")
print("CHECK backend_bytes=%d" % len(backend))

# The launcher's own CSS reached the bundle at all.
print(
    "CHECK launcher_css=%s"
    % bool(re.search(r"\.o_grid_apps_menu__button\{", backend))
)

# The theme rules, and the colour each one actually carries. Matched
# case-insensitively because libsass emits the hex as authored while Odoo's own
# rules are lowercased elsewhere in the same file.
def theme_colour(theme):
    match = re.search(
        r"\.o_grid_apps_menu\[data-theme=.?%s.?\]\{[^}]*linear-gradient\([^)]*?(#[0-9A-Fa-f]{3,8})" % theme,
        backend,
    )
    return match.group(1) if match else "ABSENT"


print("CHECK launcher_community_colour=%s" % theme_colour("community").upper())
print("CHECK launcher_milk_colour=%s" % theme_colour("milk").upper())
