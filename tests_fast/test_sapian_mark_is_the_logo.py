# -*- coding: utf-8 -*-
"""The inline Sapian mark must be the committed logo, not a lookalike.

WHY THIS IS A FAST TEST AND NOT AN ODOO ONE
-------------------------------------------
It compares two files, one of which lives OUTSIDE the addons directory:
`brand/Sapian Logo.svg` is the repository's source of truth for the logo and is
deliberately not shipped inside a module. Odoo's test runner only ever sees the
addons path — inside the container `brand/` does not exist — so the Odoo copy of
this test failed with a FileNotFoundError rather than an assertion. It belongs
here, where the whole repository is on disk and no Odoo is needed.

WHAT IT PROTECTS
----------------
brand/README.md is explicit:

    Never recreate or trace them — a redrawn logo that looks close is worse than
    a missing one, because it propagates silently into every client deployment.

`addons/sapian_theme/views/sapian_mark.xml` carries the four petal paths INLINE,
because only an inline SVG can take `fill="currentColor"` and therefore inherit
the one palette colour. That is a real duplication of the shapes, and this is
what keeps the copy honest: same paths, byte for byte; only the per-petal fill
is allowed to differ.
"""

import os
import re

_HERE = os.path.dirname(__file__)
_LOGO = os.path.join(_HERE, "..", "brand", "Sapian Logo.svg")
_MARK = os.path.join(_HERE, "..", "addons", "sapian_theme", "views", "sapian_mark.xml")

_PATH = re.compile(r'<path d="([^"]+)"')
_HEX = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b")


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def test_the_inline_mark_has_the_committed_paths():
    committed = _PATH.findall(_read(_LOGO))
    shipped = _PATH.findall(_read(_MARK))
    assert len(committed) == 4, "brand/Sapian Logo.svg is not four petals any more"
    assert shipped == committed, (
        "the inline mark's paths differ from brand/Sapian Logo.svg. Either the "
        "logo has been redrawn — which brand/README.md forbids — or the source "
        "file changed and the inline copy was not updated with it."
    )


def test_the_inline_mark_carries_no_colour_of_its_own():
    """`currentColor` is what lets one file be brand-coloured on the login page
    and in the backend footer with no second definition of the colour."""
    mark = _read(_MARK)
    assert 'fill="currentColor"' in mark
    assert not _HEX.search(mark), (
        "the inline mark contains a colour literal, which would be a second "
        "definition of the brand and would fail sapian_theme's own hex guard"
    )


def test_the_guard_discriminates():
    """A near-miss must be caught. Nudge one coordinate and compare again."""
    committed = _PATH.findall(_read(_LOGO))
    redrawn = list(committed)
    redrawn[0] = redrawn[0].replace("250.88", "250.87", 1)
    assert redrawn != committed, "the tamper did not change anything"
    assert redrawn[0] != committed[0]
