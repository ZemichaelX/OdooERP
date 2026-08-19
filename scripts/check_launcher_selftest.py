#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prove that check_launcher.py refuses to report a launcher it did not measure.

WHY THIS EXISTS
---------------
`scripts/lib/check_launcher.py` gained a gate: when the fetch of `/odoo` does
not reach the backend it emits `launcher_measured=0` and prints NOTHING
downstream. An untested guard is another thing that passes by doing nothing, so
this makes the bad thing happen on purpose and requires the gate to fire — and,
just as important, requires the good case to still print everything, because a
gate that never opens would also make this file pass.

It needs no Odoo, no database and no Docker: the module under test is exec'd
against stub `odoo` packages and a stub WSGI client, which is exactly how
`odoo shell` execs it when stdin is a pipe (odoo/cli/shell.py).

Run: python3 scripts/check_launcher_selftest.py
"""

import io
import contextlib
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "lib", "check_launcher.py")

# The bytes a browser gets when the session was refused: /odoo redirects to
# /web/login and `website` renders it. Taken from the shape of the real failure
# (title "Login | My Website", data-website-id="1", frontend bundles only).
WEBSITE_LOGIN_HTML = (
    '<!DOCTYPE html> <html lang="en-US" data-website-id="1" '
    'data-main-object="ir.ui.view(189,)"><head><title>Login | My Website</title>'
    '<script src="/web/assets/1/5a20860/web.assets_frontend_minimal.min.js"></script>'
    '<script src="/web/assets/1/d5870bb/web.assets_frontend_lazy.min.js"></script>'
    '<link href="/web/assets/1/0f9dea5/web.assets_frontend.min.css"/>'
    "</head><body>assets_frontend</body></html>"
)

BACKEND_HTML = (
    '<!DOCTYPE html><html><head><title>Odoo</title>'
    '<script src="/web/assets/9ee87e7/web.assets_web.min.js"></script>'
    '<link href="/web/assets/cd0a0e8/web.assets_web.min.css"/>'
    '</head><body><script>{"home_action_id": false}</script></body></html>'
)

BACKEND_JS = " ".join(
    "@web_responsive/components/apps_menu/apps_menu.esm"
    if i == 0
    else "@web_responsive/file%d.esm" % i
    for i in range(16)
)
BACKEND_CSS = (
    ".o_grid_apps_menu[data-theme=community]{background:linear-gradient(90deg,#14454F 0%)}"
    ".o_grid_apps_menu[data-theme=milk]{background:linear-gradient(90deg,#E9E6F9 0%)}"
    ".o_sapian_rail{display:flex}"
)

# The checks that describe the LAUNCHER. None of them may appear when the fetch
# did not reach the backend — that is the whole point of the gate.
DOWNSTREAM_KEYS = [
    "launcher_backend_js_bundles",
    "launcher_backend_css_bundles",
    "launcher_js_bytes",
    "launcher_css_bytes",
    "launcher_js_modules",
    "launcher_js_named",
    "launcher_css_web_responsive",
    "launcher_css_sapian_theme",
    "launcher_community_colour",
    "launcher_milk_colour",
    "launcher_home_action_on_wire",
]


class Response:
    def __init__(self, body, status=200, location=None, path="/odoo", history=()):
        self.body = body
        self.status_code = status
        self.headers = {"Location": location} if location else {}
        self.request = types.SimpleNamespace(path=path)
        self.history = history

    def get_data(self, as_text=False):
        return self.body if as_text else self.body.encode()


class FakeClient:
    """Serves one page for /odoo and the asset bodies for everything else."""

    def __init__(self, page_html, first_status, first_location, final_path):
        self.page_html = page_html
        self.first_status = first_status
        self.first_location = first_location
        self.final_path = final_path

    def set_cookie(self, *args, **kwargs):
        pass

    def get(self, url, headers=None, follow_redirects=False):
        if url == "/odoo":
            if not follow_redirects:
                return Response("", self.first_status, self.first_location)
            history = () if self.first_status == 200 else (Response("", 303),)
            return Response(self.page_html, 200, path=self.final_path, history=history)
        if url.endswith(".js"):
            return Response(BACKEND_JS)
        return Response(BACKEND_CSS)


class Recs(list):
    def filtered(self, func):
        if isinstance(func, str):
            return Recs(r for r in self if getattr(r, func))
        return Recs(r for r in self if func(r))

    def mapped(self, name):
        return [getattr(r, name) for r in self]


class Users:
    _fields = {"is_redirect_home": object(), "apps_menu_theme": object()}

    def __init__(self, recs):
        self._recs = recs

    def with_context(self, **kwargs):
        return self

    def with_user(self, user):
        return self

    def context_get(self):
        return {"lang": "en_US"}

    def search(self, domain):
        return self._recs


def build_env():
    admin = types.SimpleNamespace(
        id=2, login="admin", is_redirect_home=True, apps_menu_theme="community", action_id=None
    )
    users = Users(Recs([admin]))
    module = types.SimpleNamespace(state="installed")

    class Env:
        cr = types.SimpleNamespace(dbname="demo_v3")
        registry = types.SimpleNamespace(_init_modules={"web_responsive", "sapian_theme"})

        def __getitem__(self, name):
            if name == "ir.module.module":
                return types.SimpleNamespace(search=lambda *a, **k: module)
            if name == "res.users":
                return users
            raise KeyError(name)

        def ref(self, xmlid):
            return admin

    return Env()


def install_stubs(client):
    session_store_data = {}

    class Session(dict):
        sid = "SID"

        def update(self, other, **kwargs):
            dict.update(self, other)
            dict.update(self, kwargs)

        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError:
                raise AttributeError(name)

        def __setattr__(self, name, value):
            self[name] = value

    class Store:
        def new(self):
            return Session()

        def save(self, session):
            session_store_data[session.sid] = session

        def get(self, sid):
            return session_store_data.get(sid)

    odoo_mod = types.ModuleType("odoo")
    http_mod = types.ModuleType("odoo.http")
    http_mod.root = types.SimpleNamespace(session_store=Store())
    http_mod.get_default_session = lambda: {"uid": None, "db": None}
    http_mod.db_filter = lambda dbs, host=None: list(dbs)
    odoo_mod.http = http_mod

    service_mod = types.ModuleType("odoo.service")
    security_mod = types.ModuleType("odoo.service.security")
    security_mod.compute_session_token = lambda session, env: "TOKEN"
    service_mod.security = security_mod
    odoo_mod.service = service_mod

    tools_mod = types.ModuleType("odoo.tools")
    tools_mod.config = {"dbfilter": "", "db_name": ["demo_v3"], "list_db": False}
    odoo_mod.tools = tools_mod

    addons_mod = types.ModuleType("odoo.addons")
    theme_mod = types.ModuleType("odoo.addons.sapian_theme")
    brand_mod = types.ModuleType("odoo.addons.sapian_theme.brand")
    brand_mod.brand_primary = lambda: "#14454F"
    theme_mod.brand = brand_mod

    werkzeug_mod = types.ModuleType("werkzeug")
    test_mod = types.ModuleType("werkzeug.test")
    test_mod.Client = lambda root: client
    werkzeug_mod.test = test_mod

    return {
        "odoo": odoo_mod,
        "odoo.http": http_mod,
        "odoo.service": service_mod,
        "odoo.service.security": security_mod,
        "odoo.tools": tools_mod,
        "odoo.addons": addons_mod,
        "odoo.addons.sapian_theme": theme_mod,
        "odoo.addons.sapian_theme.brand": brand_mod,
        "werkzeug": werkzeug_mod,
        "werkzeug.test": test_mod,
    }


def run(client):
    """Exec the module the way `odoo shell` does and capture what it printed."""
    saved = {name: sys.modules.get(name) for name in install_stubs(client)}
    sys.modules.update(install_stubs(client))
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            with open(TARGET, encoding="utf-8") as handle:
                source = handle.read()
            exec(compile(source, TARGET, "exec"), {"env": build_env(), "__name__": "__main__"})
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    return buffer.getvalue()


def keys(output):
    return {
        line.split("=", 1)[0][len("CHECK "):]
        for line in output.splitlines()
        if line.startswith("CHECK ") and "=" in line
    }


def main():
    failures = []

    # ---- THE BAD THING, ON PURPOSE ----------------------------------------
    # The exact page the operator's --all-apps demo served: the website login,
    # 200, frontend bundles only.
    bad = run(FakeClient(WEBSITE_LOGIN_HTML, 303, "/web/login?redirect=/odoo", "/web/login"))
    bad_keys = keys(bad)
    if "launcher_measured" not in bad_keys or "CHECK launcher_measured=0" not in bad:
        failures.append("the gate did not fire: no `launcher_measured=0` on the website login page")
    leaked = sorted(k for k in DOWNSTREAM_KEYS if k in bad_keys)
    if leaked:
        failures.append(
            "the gate fired but %d launcher check(s) were still printed from a page that "
            "could not contain them: %s" % (len(leaked), ", ".join(leaked))
        )
    for expected in ("launcher_served_title", "launcher_first_location", "launcher_dbfilter_accepts",
                     "launcher_session_uid_stored", "launcher_session_token_matches"):
        if expected not in bad_keys:
            failures.append("the abort path did not report `%s`, so the next run cannot "
                            "name the mechanism" % expected)

    # ---- AND THE GOOD CASE, because a gate that never opens also "passes" --
    good = run(FakeClient(BACKEND_HTML, 200, None, "/odoo"))
    good_keys = keys(good)
    if "CHECK launcher_measured=1" not in good:
        failures.append("the backend page was not recognised as measured")
    missing = sorted(k for k in DOWNSTREAM_KEYS if k not in good_keys)
    if missing:
        failures.append(
            "the gate stayed shut on a real backend page — %d check(s) missing: %s"
            % (len(missing), ", ".join(missing))
        )
    if "CHECK launcher_js_named=True" not in good:
        failures.append("the launcher component was not found in a bundle that contains it")

    print("--- abort path ---")
    print(bad.rstrip())
    print("--- measured path ---")
    print(good.rstrip())

    if failures:
        for problem in failures:
            print("FAIL: %s" % problem, file=sys.stderr)
        return 1
    print("OK — the gate fires on a null measurement, prints nothing downstream, "
          "and stays open on a real backend page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
