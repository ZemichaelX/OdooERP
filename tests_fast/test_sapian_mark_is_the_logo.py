# -*- coding: utf-8 -*-
"""The inline Sapian mark must be the committed logo, not a lookalike.

WHY THIS IS A FAST TEST AND NOT AN ODOO ONE
-------------------------------------------
It compares two files, one of which lives OUTSIDE the addons directory:
`brand/sapian-logo.svg` is the repository's source of truth for the logo and is
deliberately not shipped inside a module. Odoo's test runner only ever sees the
addons path — inside the container `brand/` does not exist — so the Odoo copy of
this test failed with a FileNotFoundError rather than an assertion. It belongs
here, where the whole repository is on disk and no Odoo is needed.

WHAT IT PROTECTS
----------------
brand/README.md is explicit:

    Never recreate or trace them — a redrawn logo that looks close is worse than
    a missing one, because it propagates silently into every client deployment.

`addons/sapian_theme/views/sapian_mark.xml` carries the four petal paths
INLINE, and `addons/sapian_theme/static/src/xml/app_rail.xml` carries them a
second time because a server-side QWeb template cannot be `t-call`ed from an
OWL one. That is a real duplication of the artwork, and this is what keeps both
copies honest.

STRENGTHENED 20 Aug 2026. It used to assert the `d` attributes only, because
the inline marks were monochrome — `fill="currentColor"` — and had no colour to
compare. The marks now carry the mark's own four colours, so this asserts the
FILLS as well, for both renderings: same paths and same paint, byte for byte.
That is a stricter check than the one it replaces, not a looser one. Nothing
about the copies is allowed to differ.
"""

import os
import re

_HERE = os.path.dirname(__file__)
_LOGO = os.path.join(_HERE, "..", "brand", "sapian-logo.svg")
_MARK = os.path.join(_HERE, "..", "addons", "sapian_theme", "views", "sapian_mark.xml")
_RAIL = os.path.join(
    _HERE, "..", "addons", "sapian_theme", "static", "src", "xml", "app_rail.xml"
)
# Both renderings of the mark. Named together because every assertion below
# must run against BOTH — the rail copy was the one nobody was checking.
_RENDERINGS = (("views/sapian_mark.xml", _MARK), ("static/src/xml/app_rail.xml", _RAIL))

_PATH = re.compile(r'<path d="([^"]+)"')
_PETAL = re.compile(r'<path d="([^"]+)" fill="(#[0-9A-Fa-f]{6})"')
_HEX = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b")


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _committed_petals():
    petals = _PETAL.findall(_read(_LOGO))
    assert len(petals) == 4, "brand/sapian-logo.svg is not four coloured petals any more"
    return petals


def test_every_rendering_has_the_committed_paths_and_fills():
    """Shape AND paint, for both copies, against the one committed source.

    The previous version compared paths only, because the inline marks were
    monochrome and had no colour to compare, and it looked at one of the two
    copies. Both gaps are closed here.
    """
    committed = _committed_petals()
    for label, path in _RENDERINGS:
        shipped = _PETAL.findall(_read(path))
        assert shipped == committed, (
            "%s does not match brand/sapian-logo.svg. Either the logo has been "
            "redrawn — which brand/README.md forbids — or the source file "
            "changed and this copy was not regenerated with it.\n"
            "  committed: %s\n  shipped:   %s" % (label, committed, shipped)
        )


def test_the_two_renderings_cannot_drift_from_each_other():
    """A server-side template and an OWL one, holding the same artwork.

    Asserted directly rather than only via the source, so a change that edited
    both copies wrongly in the same way still fails.
    """
    first = _PETAL.findall(_read(_MARK))
    second = _PETAL.findall(_read(_RAIL))
    assert first == second, (
        "the QWeb mark and the OWL rail mark have diverged from each other"
    )


def test_no_rendering_falls_back_to_currentcolor():
    """`fill="currentColor"` on a petal is the monochrome mark returning.

    It was the deliberate behaviour until 20 Aug 2026 and is now a regression:
    it would paint the corporate mark in one flat colour again, and the two
    tests above would still pass if the fills were absent rather than wrong.
    """
    for label, path in _RENDERINGS:
        markup = _read(path)
        svg = markup[markup.index("<svg"):markup.index("</svg>")]
        assert 'fill="currentColor"' not in svg, (
            "%s paints the mark with currentColor again" % label
        )
