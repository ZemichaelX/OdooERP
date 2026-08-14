# -*- coding: utf-8 -*-
"""Every app tile must carry an icon.

WHY THIS IS AN INVARIANT AND NOT A COUNT
----------------------------------------
The obvious version of this test — "assert there are 23 apps" — is the trap.
Installing the full Odoo Community catalogue takes the root-app count from ~23
to ~36, and a client installing one more module moves it again. A test pinned to
a number goes red on a perfectly correct change, and a guard that cries wolf is
a guard everyone learns to skip. The property that must hold at 14 apps, at 23
and at 36 is that NONE of them is blank.

WHY IT MATTERS
--------------
`ir.ui.menu.load_menus()` returns `web_icon_data` for each root menu. The app
drawer draws it with

    <img t-if="app.webIconData" .../>

so a menu with no icon renders NOTHING — not a placeholder, not a default glyph.
In a dropdown that is invisible. In a persistent sidebar rail it is a hole on
every screen, all day. Measured on the demo tenant before the icons existed: 21
root menus, exactly one without an icon, and it was ours.

WHAT IT ASSERTS AGAINST
-----------------------
`load_menus()`, not the `ir.ui.menu` table. That is the payload the web client
actually receives; a `web_icon` attribute in XML is not an icon in the database,
and a row in the database is not bytes on the wire. The icon is resolved from
the module's file into an `ir.attachment` at install time, so reading it back
out of `load_menus` is what proves the whole chain worked.
"""

import base64

from odoo.tests import TransactionCase, tagged

# Pointer, not prose: whoever trips this test needs the drawing rules, and they
# live in one place.
ICON_GUIDE = "brand/icons/README.md"

# Quoted from that file so the failure message carries the rules rather than
# merely citing them. Kept short on purpose — the file is the source of truth.
ICON_RULES_DIGEST = (
    "512 canvas exported to 256x256 PNG with alpha; tints never multiply; "
    "three colours max (identity hue + its tint + one palette accent); "
    "corner radius ~14% of the short side; white cut-outs never thinner than "
    "26/512; no text or glyphs; one accent breaks one corner; distinct "
    "silhouettes, not colour variants"
)

# The modules this repo owns and promotes to apps. Their icons get the stronger
# checks: really a PNG, really the file on disk, not a stub that happens to be
# non-empty.
SAPIAN_APP_MODULES = ("sapian_core", "l10n_et_payroll", "l10n_et_reports")

# Smallest core Odoo icon measured in the 19.0 image is 587 bytes; ours are
# 1612-4165. A floor of 400 catches a truncated or stub image without being so
# tight that a legitimately simple third-party icon trips it.
MIN_ICON_BYTES = 400

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _root_apps(env):
    """Return the app dicts exactly as the web client receives them."""
    menus = env["ir.ui.menu"].load_menus(False)
    root = menus["root"]
    apps = []
    for child_id in root["children"]:
        # load_menus keys are ints, but have been strings in some versions;
        # accept either rather than depending on the representation.
        entry = menus.get(child_id, menus.get(str(child_id)))
        if entry:
            apps.append(entry)
    return apps


@tagged("post_install", "-at_install")
class TestAppIconInvariant(TransactionCase):
    """The guard itself, plus proof that it discriminates."""

    def test_every_root_menu_has_an_icon(self):
        """No app tile may be blank. Holds at any number of installed apps."""
        apps = _root_apps(self.env)

        # Assert the positive first: a run that found no apps at all would
        # otherwise satisfy "none of them is blank" by doing nothing.
        self.assertGreaterEqual(
            len(apps),
            1,
            "load_menus returned no root menus at all — the menu payload is "
            "empty, so this test would pass by checking nothing.",
        )

        missing = sorted(a["name"] for a in apps if not a.get("web_icon_data"))
        self.assertEqual(
            missing,
            [],
            "\n"
            "These root menus have NO icon and will render as a blank tile in "
            "the app drawer:\n"
            "    %s\n"
            "\n"
            "%d of %d apps are fine; the ones above are not.\n"
            "\n"
            "Fix: put a 256x256 PNG at addons/<module>/static/description/"
            "icon.png and declare it on the ROOT <menuitem>:\n"
            '    web_icon="<module>,static/description/icon.png"\n'
            "\n"
            "Do NOT freehand one — the set is a system. Generate it with "
            "brand/icons/draw.py and read %s first.\n"
            "The rules, in short: %s.\n"
            "Judge it at 23 px in brand/icons/PROOF.png, never at full size — "
            "every failed pass of this icon set failed because it was judged "
            "large."
            % (
                "\n    ".join(missing),
                len(apps) - len(missing),
                len(apps),
                ICON_GUIDE,
                ICON_RULES_DIGEST,
            ),
        )

    def test_sapian_app_icons_are_real_images(self):
        """Our own three carry decodable PNG bytes, not merely something."""
        apps_by_xmlid = {}
        for app in _root_apps(self.env):
            xmlid = app.get("xmlid") or ""
            if xmlid:
                apps_by_xmlid[xmlid.split(".")[0]] = app

        checked = []
        for module in SAPIAN_APP_MODULES:
            app = apps_by_xmlid.get(module)
            if not app:
                # Not installed in this database — genuinely nothing to assert.
                # Counted below so the test cannot pass by checking nothing.
                continue
            with self.subTest(module=module):
                data = app.get("web_icon_data")
                # Check truthiness BEFORE decoding: web_icon_data is False (a
                # bool) when absent, and b64decode(False) raises TypeError,
                # which reports as an ERROR with a traceback about bytes-like
                # objects instead of telling the reader their icon is missing.
                self.assertTrue(
                    data,
                    "%s: has no web_icon_data at all. Declare it on the root "
                    '<menuitem>: web_icon="%s,static/description/icon.png". '
                    "See %s." % (module, module, ICON_GUIDE),
                )
                raw = base64.b64decode(data)
                self.assertEqual(
                    raw[:8],
                    _PNG_MAGIC,
                    "%s: web_icon_data is not a PNG. The bytes served to the "
                    "browser are not the icon file on disk." % module,
                )
                self.assertGreaterEqual(
                    len(raw),
                    MIN_ICON_BYTES,
                    "%s: icon is only %d bytes (floor %d) — that is a stub or "
                    "a truncated file, not a drawn icon. See %s."
                    % (module, len(raw), MIN_ICON_BYTES, ICON_GUIDE),
                )
                checked.append(module)

        # sapian_core is a dependency of this test's own module, so it is
        # always installed. If even that was not checked, the lookup is broken
        # (an xmlid shape change, say) and every subTest above was skipped —
        # a pass produced by doing nothing.
        self.assertIn(
            "sapian_core",
            checked,
            "No Sapian app icon was checked at all. sapian_core is always "
            "installed here, so failing to find it means the root-menu lookup "
            "is broken and this test verified nothing. Checked: %s" % checked,
        )

    def test_the_guard_discriminates(self):
        """Make the bad thing happen on purpose and watch the check go red.

        An untested guard is another thing that passes by doing nothing. This
        creates a root menu with no icon — exactly the defect the invariant
        exists to catch — and fails if the invariant does not notice.

        The plant needs an ACTION. `_filter_visible_menus` drops a root menu
        that has neither an action nor a visible child, so a bare
        `{"name": ..., "parent_id": False}` never reaches load_menus and cannot
        be a blank tile in the first place. The first version of this test did
        exactly that and failed — correctly, and usefully: it means the
        invariant's blast radius is only menus a user can actually reach, which
        is the right scope but not the one assumed here at first.
        """
        action = self.env["ir.actions.act_window"].create(
            {"name": "Iconless Probe", "res_model": "res.partner", "view_mode": "list"}
        )
        blank = self.env["ir.ui.menu"].create(
            {
                "name": "Deliberately Iconless App",
                "parent_id": False,
                "action": "ir.actions.act_window,%d" % action.id,
            }
        )
        self.addCleanup(action.unlink)
        self.addCleanup(blank.unlink)

        apps = _root_apps(self.env)
        names = [a["name"] for a in apps]
        self.assertIn(
            "Deliberately Iconless App",
            names,
            "The planted menu did not reach load_menus, so this test cannot "
            "prove anything about the guard.",
        )

        missing = [a["name"] for a in apps if not a.get("web_icon_data")]
        self.assertIn(
            "Deliberately Iconless App",
            missing,
            "The invariant did NOT flag a root menu with no icon. The guard is "
            "decoration — every green run of "
            "test_every_root_menu_has_an_icon means nothing until this passes.",
        )
