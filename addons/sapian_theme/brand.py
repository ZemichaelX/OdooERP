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

# Bootstrap's shade-color($c, 15%) == mix(black, $c, 15%) == 85% of each
# channel. Kept in step with the SCSS by test_python_shade_matches_scss_recipe.
_SECONDARY_SHADE_WEIGHT = 0.15


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


def shade(hex_colour, weight=_SECONDARY_SHADE_WEIGHT):
    """Bootstrap's ``shade-color`` in Python: mix ``weight`` of black in."""
    raw = hex_colour.lstrip("#")
    channels = (int(raw[i : i + 2], 16) for i in (0, 2, 4))
    return "#%02X%02X%02X" % tuple(round(c * (1 - weight)) for c in channels)


@lru_cache(maxsize=1)
def brand_secondary():
    """The secondary/document colour: the same shade the CSS hover state uses."""
    return shade(brand_primary())
