# -*- coding: utf-8 -*-
"""The bridge between the two colour systems that both reach a printed PDF.

There are genuinely two of them, and they are independent:

1. **Assets.** ``$sapian-brand`` in ``static/src/scss/sapian_variables.scss``
   compiles into the CSS used by the backend, the login page and the report
   bundle. This colours *rendered chrome* — buttons, badges, the statusbar.
2. **Data.** Odoo's external report layouts read ``res.company.primary_color``
   and ``secondary_color`` as ordinary field values and inline them into the
   PDF (``web/models/base_document_layout.py``). This colours the *document*
   — header bar, footer rule, headings.

Which wins where: on a printed document the DATA wins for anything the layout
templates paint from the company fields, and the ASSETS win for anything drawn
by report CSS. They never fight over the same pixel, but they can disagree
about what "the brand" is — and a client whose PDF header is one magenta and
whose badges are another has noticed a bug we shipped.

So there is exactly one source: the SCSS file. Python reads the value out of
it rather than restating it, which is why re-branding stays a single edit in a
single file. A duplicated constant with a test comparing the two would also
work, but it would still be two edits, and the kickoff asked for one.
"""

import re
from functools import lru_cache
from pathlib import Path

_PALETTE_FILE = Path(__file__).parent / "static" / "src" / "scss" / "sapian_variables.scss"
_BRAND_RE = re.compile(r"^\s*\$sapian-brand\s*:\s*(#[0-9A-Fa-f]{6})\s*;", re.MULTILINE)

# Bootstrap's shade-color($c, w) == mix(black, $c, w); tint-color($c, w) ==
# mix(white, $c, w). 15% either way, matching sapian_variables.scss.
_SHADE_WEIGHT = 0.15
# The same threshold the SCSS uses for $sapian-brand-is-dark. Below it a brand
# lightens on hover instead of darkening, because darkening an already-dark
# colour reads as disabled rather than hovered.
_DARK_LIGHTNESS_THRESHOLD = 40.0


@lru_cache(maxsize=1)
def brand_primary():
    """The brand colour, read from the one file that defines it.

    Raises rather than falling back to a hard-coded default: a silent fallback
    would mean a re-brand that "worked" in CSS and quietly left every new
    company on the old colour — the exact drift this module exists to prevent.
    """
    try:
        text = _PALETTE_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            "sapian_theme: cannot read the palette file %s. It is the single "
            "source of the brand colour; without it the company default and "
            "the compiled CSS would disagree." % _PALETTE_FILE
        ) from exc
    match = _BRAND_RE.search(text)
    if not match:
        raise ValueError(
            "sapian_theme: no `$sapian-brand: #RRGGBB;` declaration found in %s. "
            "If the variable was renamed, update _BRAND_RE here in the same "
            "commit." % _PALETTE_FILE
        )
    return match.group(1).upper()


def _channels(hex_colour):
    raw = hex_colour.lstrip("#")
    return [int(raw[i : i + 2], 16) for i in (0, 2, 4)]


def shade(hex_colour, weight=_SHADE_WEIGHT):
    """Bootstrap's ``shade-color`` in Python: mix ``weight`` of black in."""
    return "#%02X%02X%02X" % tuple(round(c * (1 - weight)) for c in _channels(hex_colour))


def tint(hex_colour, weight=_SHADE_WEIGHT):
    """Bootstrap's ``tint-color`` in Python: mix ``weight`` of white in."""
    return "#%02X%02X%02X" % tuple(
        round(c * (1 - weight) + 255 * weight) for c in _channels(hex_colour)
    )


def hsl_lightness(hex_colour):
    """HSL lightness as a percentage — the same measure SCSS ``lightness()`` uses."""
    channels = [c / 255 for c in _channels(hex_colour)]
    return (max(channels) + min(channels)) / 2 * 100


def is_dark(hex_colour):
    """Mirror of ``$sapian-brand-is-dark`` in sapian_variables.scss."""
    return hsl_lightness(hex_colour) < _DARK_LIGHTNESS_THRESHOLD


@lru_cache(maxsize=1)
def brand_secondary():
    """The companion colour: exactly the CSS hover value.

    The document's secondary colour and the interface hover state are supposed
    to be the same colour, so this implements the identical luminance-aware
    rule as the SCSS — lighten a dark brand, darken a light one.
    ``test_python_derivation_matches_the_scss_recipe`` pins the two together;
    if they ever diverge, a company prints one teal while the UI shows another.
    """
    primary = brand_primary()
    return tint(primary) if is_dark(primary) else shade(primary)
