# -*- coding: utf-8 -*-
"""What an anonymous visitor is served on /web/login. Piped into `odoo shell`.

ONE DEFINITION, TWO CALLERS: scripts/build_demo.sh and
scripts/provision_client.sh. It used to live inline in build_demo.sh only, and
the consequence was that the demo was checked and the thing we sell was not —
a real client was provisioned without sapian_theme at all and served Odoo's
own footer.

WHY IT RENDERS THROUGH WSGI RATHER THAN OVER A SOCKET
-----------------------------------------------------
`werkzeug.test.Client(odoo.http.root)` runs the real dispatcher, the real
routing, the real session and the real QWeb, and returns exactly the bytes a
browser would get — with no port to bind, no background container to reap, and
no behavioural difference on Windows, where these scripts are run from Git
Bash. The request carries no session cookie, so the page is served to the
anonymous visitor a prospect or a client's staff member actually is.

Prints CHECK lines only. The assertions live in preflight.sh::verify_login_page,
so the messages an operator reads stay in one place too.
"""

import re

from werkzeug.test import Client

from odoo.addons.sapian_theme import brand
from odoo.http import root as http_root

BRAND = brand.brand_primary()


def brand_rgb(hexcolour):
    """'#14454F' -> '20, 69, 79', the form Bootstrap's focus ring uses."""
    value = hexcolour.lstrip("#")
    return ", ".join(str(int(value[i : i + 2], 16)) for i in (0, 2, 4))


def bundle_css(name):
    """The compiled CSS a browser would be served for ``name``.

    `_get_asset_bundle(...).css()` COMPILES and stores; `_generate_asset_links`
    does not, and on a freshly built database (where nobody has loaded a page
    yet) it leaves the attachment absent — which reads as "the brand is
    missing" when the brand is fine.
    """
    attachment = env["ir.qweb"]._get_asset_bundle(name, css=True, js=False).css()  # noqa: F821
    return (attachment.raw or b"").decode("utf-8", "ignore") if attachment else ""


def first(text, pattern):
    found = re.findall(pattern, text)
    return found[0] if found else "ABSENT"


print("CHECK brand_expected=%s" % BRAND)
print("CHECK brand_expected_rgb=%s" % brand_rgb(BRAND))

theme = env["ir.module.module"].search([("name", "=", "sapian_theme")], limit=1)  # noqa: F821
print("CHECK theme=%s" % (theme.state if theme else "missing"))

# ---- the sign-in button, in EVERY state ------------------------------------
# --btn-bg alone was asserted for weeks while the button turned Odoo purple the
# moment it was clicked: login.js adds `disabled` on submit, and an unset
# --btn-disabled-bg falls through to Odoo's colour. The focus ring is the same
# shape of miss.
frontend = bundle_css("web.assets_frontend")
login_rule = first(frontend, r"(\.oe_login_form \.btn-primary\{[^}]*\})")
print("CHECK login_primary=%s" % first(login_rule, r"--btn-bg: (#[0-9A-Fa-f]{6})"))
print("CHECK login_disabled=%s" % first(login_rule, r"--btn-disabled-bg: (#[0-9A-Fa-f]{6})"))
print(
    "CHECK login_focus_rgb=%s"
    % first(login_rule, r"--btn-focus-shadow-rgb: ([0-9]+, [0-9]+, [0-9]+)")
)

# ---- the page itself, as it comes back on the wire -------------------------
response = Client(http_root).get("/web/login", headers={"Host": "localhost"})
html = response.get_data(as_text=True)
print("CHECK login_http=%s" % response.status_code)
# A zero-length page satisfies every "must not contain" check below it, so the
# size is asserted first and absence is only ever measured on a real page.
print("CHECK login_bytes=%d" % len(html))
print(
    "CHECK login_odoo_refs=%d"
    % (html.count("odoo.com") + html.count("Powered by <span>Odoo"))
)
print("CHECK login_powered_sapian=%d" % html.count("Powered by SapianERP"))
print("CHECK login_mark=%d" % html.count("o_sapian_mark"))
print("CHECK login_signup=%d" % html.count("/web/signup"))

support = env["ir.config_parameter"].sudo().get_param("sapian_theme.support_contact") or ""  # noqa: F821
print("CHECK login_support_configured=%d" % bool(support))
# Not "is it configured" but "if it is configured, does it reach the page" —
# so the same check is meaningful on a demo (which configures one) and on a
# fresh client tenant (which has not been told the number yet).
print("CHECK login_support_rendered=%d" % (bool(support) and support in html))

scope_field = env["res.config.settings"]._fields.get("auth_signup_uninvited")  # noqa: F821
scope_key = getattr(scope_field, "config_parameter", None) or "auth_signup.invitation_scope"
print(
    "CHECK login_signup_scope=%s"
    % (env["ir.config_parameter"].sudo().get_param(scope_key) or "unset")  # noqa: F821
)
