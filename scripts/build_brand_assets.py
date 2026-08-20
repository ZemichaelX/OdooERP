#!/usr/bin/env python3
"""Generate EVERY raster brand asset from the committed SVG sources.

ONE COMMAND, and that is the point:

    python3 scripts/build_brand_assets.py

WHY THIS EXISTS. Before it, the rasters were produced by hand from
`brand/icons/draw.py` and copied into place by hand, and the bot avatar was a
hand-made duplicate of one app icon. Three consequences, all of which happened:
the app-icon set drifted into a palette that was not the mark's, the bot and
sapian_core shared one image so the product showed two logos at once, and six
modules had no icon at all because nobody remembered to make one.

Everything below is derived. Nothing here draws: the shapes come from
`brand/icons/draw.py` (the app-icon system) and from `brand/sapian-logo.svg`
(the mark itself). `brand/README.md` forbids redrawing the mark, so the mark is
RASTERISED, never traced.

WHAT IT WRITES

  addons/<module>/static/description/icon.png   the app tile, one per module
  brand/icons/deliver/<module>__icon.png        the same bytes, kept beside the
                                                sources so a reviewer can see
                                                the set without a checkout of
                                                every addon
  addons/sapian_theme_mail/static/src/img/sapian_bot.png
                                                the bot's OWN avatar
  addons/sapian_theme/static/src/img/favicon.png
                                                the browser tab
  addons/sapian_theme/static/src/img/sapian_logo.png
                                                the default company logo, used
                                                by the navbar, the login page,
                                                every PDF header and outgoing
                                                mail

THE BOT IS NOT AN APP ICON. It is rasterised from the mark, at a size that
suits a 40px chatter avatar. Sharing sapian_core's tile was the defect; a
second copy of the tile under a different filename would be the same defect
with an extra file.

Requires `cairosvg` and `pillow`. Both are dev-time only: nothing in the
product imports them, and CI regenerates and compares rather than installing
them into the runtime image.
"""

import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(REPO, "brand", "icons")
DELIVER = os.path.join(ICONS, "deliver")
MARK = os.path.join(REPO, "brand", "sapian-logo.svg")
LOCKUP = os.path.join(REPO, "brand", "sapian-logo-name-tag.svg")

# Every module that ships an app tile. The list is asserted against the addons
# directory below, so adding an addon without an icon fails here rather than
# showing Odoo's placeholder in a client's rail.
MODULES = [
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

ICON_PX = 256  # Odoo core ships 100; 256 downsamples cleanly to 23-39px
BOT_PX = 256  # chatter avatars are served through /web/image at <=128
FAVICON_PX = 64  # browsers ask for 16/32; 64 covers retina without bloat
LOGO_PX = 512  # the company logo is scaled down by every layout that uses it


def _svg2png(svg_bytes, px):
    import cairosvg  # noqa: PLC0415 - dev-time only

    return cairosvg.svg2png(bytestring=svg_bytes, output_width=px, output_height=px)


def _write_png(data, path, px):
    from PIL import Image  # noqa: PLC0415 - dev-time only

    image = Image.open(io.BytesIO(data)).convert("RGBA")
    if image.size != (px, px):
        image = image.resize((px, px), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, optimize=True)
    return os.path.getsize(path)


def run_icon_script():
    """Run the committed icon script in its own directory, as it expects."""
    result = subprocess.run(
        [sys.executable, "draw.py"], cwd=ICONS, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit("brand/icons/draw.py failed; no asset was written")
    return [
        line.split()[-1] for line in result.stdout.splitlines() if line.startswith("rendered")
    ]


def main():
    rendered = run_icon_script()
    missing = sorted(set(MODULES) - set(rendered))
    if missing:
        raise SystemExit(
            "draw.py rendered no icon for: %s. Every module in MODULES needs a "
            "render() call, or it ships Odoo's placeholder." % ", ".join(missing)
        )

    written = 0
    for module in MODULES:
        source = os.path.join(ICONS, module + ".svg")
        with open(source, "rb") as handle:
            png = _svg2png(handle.read(), ICON_PX)
        for target in (
            os.path.join(REPO, "addons", module, "static", "description", "icon.png"),
            os.path.join(DELIVER, module + "__icon.png"),
        ):
            _write_png(png, target, ICON_PX)
            written += 1
        print("icon   %-28s %d px" % (module, ICON_PX))

    with open(MARK, "rb") as handle:
        mark_svg = handle.read()

    for path, px, label in (
        (
            os.path.join(
                REPO, "addons", "sapian_theme_mail", "static", "src", "img", "sapian_bot.png"
            ),
            BOT_PX,
            "bot avatar",
        ),
        (
            os.path.join(REPO, "addons", "sapian_theme", "static", "src", "img", "favicon.png"),
            FAVICON_PX,
            "favicon",
        ),
        (
            os.path.join(
                REPO, "addons", "sapian_theme", "static", "src", "img", "sapian_logo.png"
            ),
            LOGO_PX,
            "company logo",
        ),
    ):
        size = _write_png(_svg2png(mark_svg, px), path, px)
        written += 1
        print("mark   %-28s %d px  %d bytes" % (label, px, size))

    print("\n%d files written, all derived from committed SVG sources." % written)


if __name__ == "__main__":
    main()
