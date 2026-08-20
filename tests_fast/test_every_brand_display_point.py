# -*- coding: utf-8 -*-
"""Every place the product shows a logo, mark, icon or avatar is OURS.

THE INVENTORY, AS A TEST
------------------------
An operator found three brand defects on one build, and the reason all three had
survived is that nobody had ever counted the places a logo appears. Individual
checks existed — the mark matched the committed SVG, the bot avatar matched a
brand asset — and each passed while six app tiles showed Odoo's placeholder, the
favicon was Odoo's, and the bot and the Settings app wore the same image.

So this asserts the LIST, not a sample of it. A new module with no icon fails
here on the day it is added, which is the only moment the fix is cheap.

WHY A FAST TEST. Everything below is a fact about files in the repository, and
`brand/` is not on the addons path, so an Odoo test cannot see half of it. The
runtime half — that the favicon and logo actually reach `res.company`, on
install AND on upgrade — is proved separately in
`sapian_theme/tests/test_brand_assets.py`, because that is a fact about records
and only Odoo can answer it.
"""

import os
import re

_HERE = os.path.dirname(__file__)
_REPO = os.path.abspath(os.path.join(_HERE, ".."))

# Every module that ships an app tile. This list is the inventory: 16 modules,
# 16 tiles. It is compared against the addons directory below, so it cannot
# quietly fall behind.
MODULES_WITH_TILES = [
    "l10n_et_base",
    "l10n_et_calendar",
    "l10n_et_calendar_account",
    "l10n_et_calendar_purchase",
    "l10n_et_payroll",
    "l10n_et_reports",
    "sapian_core",
    "sapian_demo_pharma",
    "sapian_demo_trader",
    "sapian_dress_rehearsal",
    "sapian_sentry",
    "sapian_theme",
    "sapian_theme_auth_signup",
    "sapian_theme_mail",
    "sapian_theme_website",
    "vertical_pharma",
]

# The display points that are not app tiles. Each is (label, path).
SINGLE_ASSETS = [
    ("bot avatar", "addons/sapian_theme_mail/static/src/img/sapian_bot.png"),
    ("favicon", "addons/sapian_theme/static/src/img/favicon.png"),
    ("company logo", "addons/sapian_theme/static/src/img/sapian_logo.png"),
]

MARK_RENDERINGS = [
    ("navbar / login mark", "addons/sapian_theme/views/sapian_mark.xml"),
    ("app rail mark", "addons/sapian_theme/static/src/xml/app_rail.xml"),
]

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _path(rel):
    return os.path.join(_REPO, rel)


def _addon_dirs():
    addons = os.path.join(_REPO, "addons")
    return sorted(
        name
        for name in os.listdir(addons)
        if os.path.isfile(os.path.join(addons, name, "__manifest__.py"))
    )


def test_the_module_list_is_the_whole_addons_directory():
    """The inventory cannot fall behind the product.

    Without this, adding a module and forgetting its icon would pass every
    other test in this file — the list would simply not mention it, which is
    exactly how six modules came to ship Odoo's placeholder.
    """
    assert sorted(MODULES_WITH_TILES) == _addon_dirs(), (
        "the tile inventory and the addons directory disagree.\n"
        "  only in the list:    %s\n"
        "  only in addons/:     %s"
        % (
            sorted(set(MODULES_WITH_TILES) - set(_addon_dirs())),
            sorted(set(_addon_dirs()) - set(MODULES_WITH_TILES)),
        )
    )


def test_every_module_ships_its_own_app_tile():
    """No module falls back to Odoo's placeholder."""
    missing = [m for m in MODULES_WITH_TILES
               if not os.path.exists(_path("addons/%s/static/description/icon.png" % m))]
    assert not missing, (
        "%d module(s) ship no icon.png, so Odoo serves its own placeholder in "
        "the app rail, the tiles and the command palette: %s. Run "
        "scripts/build_brand_assets.py." % (len(missing), ", ".join(missing))
    )


def test_every_single_asset_exists_and_is_a_real_png():
    """A zero-byte or missing file is a fallback with extra steps."""
    for label, rel in SINGLE_ASSETS:
        full = _path(rel)
        assert os.path.exists(full), "%s is missing (%s)" % (label, rel)
        with open(full, "rb") as handle:
            head = handle.read(8)
        assert head == _PNG_MAGIC, "%s is not a PNG (%s)" % (label, rel)
        assert os.path.getsize(full) > 512, (
            "%s is %d bytes — too small to be the rendered mark"
            % (label, os.path.getsize(full))
        )


def test_the_bot_does_not_share_the_settings_app_icon():
    """The defect that started this, asserted directly.

    The bot avatar and sapian_core's tile were byte-identical, so the product
    showed one image doing two jobs. Equality here is not a near-miss; it is
    the exact regression.
    """
    with open(_path("addons/sapian_theme_mail/static/src/img/sapian_bot.png"), "rb") as handle:
        bot = handle.read()
    with open(_path("addons/sapian_core/static/description/icon.png"), "rb") as handle:
        tile = handle.read()
    assert bot != tile, (
        "the bot avatar is byte-identical to sapian_core's app icon again — "
        "one image cannot be both the product's voice and the Settings tile"
    )


def test_no_app_tile_is_a_duplicate_of_another():
    """Sixteen modules, sixteen distinguishable tiles.

    Two modules sharing a tile is the same defect as the bot sharing one, one
    step removed: the rail stops being readable.
    """
    seen = {}
    for module in MODULES_WITH_TILES:
        with open(_path("addons/%s/static/description/icon.png" % module), "rb") as handle:
            seen.setdefault(handle.read(), []).append(module)
    clashes = {tuple(v) for v in seen.values() if len(v) > 1}
    assert not clashes, "modules sharing one icon: %s" % sorted(clashes)


def test_every_mark_rendering_carries_the_brand_colours():
    """Neither rendering may fall back to a flat colour.

    `test_sapian_mark_is_the_logo` proves the marks equal the committed SVG.
    This proves the weaker but different thing the inventory cares about: that
    a mark is present at all in each place the product paints one.
    """
    with open(_path("brand/sapian-logo.svg"), encoding="utf-8") as handle:
        expected = set(re.findall(r'fill="(#[0-9A-Fa-f]{6})"', handle.read()))
    assert len(expected) == 4
    for label, rel in MARK_RENDERINGS:
        with open(_path(rel), encoding="utf-8") as handle:
            markup = handle.read()
        svg = markup[markup.index("<svg"): markup.index("</svg>")]
        found = set(re.findall(r'fill="(#[0-9A-Fa-f]{6})"', svg))
        assert found == expected, (
            "%s does not paint the mark's four colours (found %s). A mark that "
            "is not ours, or a monochrome fallback, is what this catches."
            % (label, sorted(found))
        )


def test_the_display_point_count_is_what_we_claim():
    """26 display points: 16 tiles, 3 single assets, 2 mark renderings, and the
    5 surfaces `res.company` feeds — navbar, login, PDF header, e-mail, tab.

    Stated as a number so a silent shrink is visible. The company-fed surfaces
    are counted once each because they are separate places a human looks, even
    though one field feeds four of them.
    """
    company_fed_surfaces = 5
    total = (
        len(MODULES_WITH_TILES) + len(SINGLE_ASSETS) + len(MARK_RENDERINGS) + company_fed_surfaces
    )
    assert total == 26, "the inventory is %d display points, not 26" % total
