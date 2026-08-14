# SapianERP app icons — the design system

These icons are **generated, not hand-drawn**. To add one, write a function in
`draw.py` and run the script. Do not open a graphics editor and freehand an
eleventh icon: the value of the set is that it is a system, and one hand-drawn
member is what breaks it.

## The constraint everything follows from

The icon is only ever rendered at **23–39 px**:

| Where | Size |
|---|---|
| Command palette (Ctrl-K) | 1.8rem ≈ 23 px |
| Current-app header, drawer | 2em ≈ 26 px |
| App tiles, and the rail | 3em ≈ 39 px |

Nothing is ever drawn at 100 px. Every rule below exists because of that number,
and **every failed pass of this set failed because it was judged large**.

## The rules

1. **512 canvas**, subject fills **32–480**, exported to 256×256 PNG with alpha.
   Odoo core is 100×100; 256 downsamples cleanly to every render size at ~3 KB.
2. **Cool + warm in every icon.** Pair contrasting hues — never a hue with a
   tint of itself. A hue against its own tint has almost no separation at 23 px
   and reads as one dull blob. This was the single biggest defect in v2.
3. **Icon-weight colour, not print-weight colour.** `vivid()` raises lightness
   and saturation while preserving hue. The brand values are correct for text
   and print; as a 39 px tile beside Odoo's turquoise and magenta they read as
   dour. Same hues, higher values.
4. **No more than three of ten share a dominant hue.** v2 was six-of-ten
   teal-dominant and the sidebar read as one smear.
5. **Distinct silhouettes, not colour variants.** Two icons that differ only in
   hue are the same icon to someone scanning a sidebar. Silhouette does more
   work than colour at 23 px.
6. **Cut-outs are white, never thinner than 30/512.** Anything finer disappears.
7. **No text, no glyphs, no numerals.** The birr sign was tried and became mush.

## The palette

Brand values (print, text, reports):

    TEAL #14454F   GREEN #2F7E4F   ORANGE #C05628   AMBER #E39A42

Derived icon values, via `vivid()` — same hues, tile-weight:

    T  #1F8CA3   T2 #4DB6CB   G  #30A660   G2 #60C78A   O  #DD622C   A  #EEA64F

## Why the mark is simplified

`sapian_core` does **not** use the four-blade logo pinwheel. That was tested at
nudge 34, 55, 75 and 95 and every setting collapsed into an orange blob — the
blades carry their mass at the outer end, so pulling them together makes them
occlude each other. Two blades read as two disconnected dots; three the same.

The tile mark is therefore four swirled quarters with a white hub: it keeps what
the logo *means* — four parts, rotational, the full palette — and drops what does
not survive downscaling. **The full pinwheel remains the print and lockup mark.**
This is the normal fate of a detailed logo at favicon size, not a compromise
unique to us.

## Files

    sys_.py             palette, vivid()/tint(), SVG scaffolding
    draw.py             one function per icon — the geometry
    *.svg               generated source
    deliver/            *__icon.png, ready to copy into addons/
    PROOF.png           the set at 23 px and 39 px
    PROOF-VS-ODOO.png   the set beside Odoo's core icons, and interleaved
                        with them — this is the sheet that matters

## Adding icon #11

1. Add a function to `draw.py`.
2. Choose a silhouette no existing icon owns, and a hue pair that keeps rule 4
   true. Check `PROOF-VS-ODOO.png` first — Invoicing owns "document", which is
   why Compliance became a shield.
3. Run the script, then regenerate `PROOF-VS-ODOO.png`.
4. Look at the **23 px row, with Odoo's icons in the same frame**. If you cannot
   tell it apart from its neighbours there, it has failed — however good it
   looks large. Judging our own proof sheet in isolation is what let v2 ship.
5. Copy `deliver/<module>__icon.png` to
   `addons/<module>/static/description/icon.png`.
6. Declare it: `web_icon="<module>,static/description/icon.png"` on the root
   `<menuitem>`.

## Two things that will bite you

**Replacing a PNG may not update a live database.** Odoo recomputes
`web_icon_data` only when `web_icon` is *written*. A module whose icon file
changes on disk can keep serving the old attachment through `-u` indefinitely.
Verify icon changes on an **upgraded** database, never only a fresh one.

**Verify the delivered file, not the render.** Exporting these to a palette PNG
via `quantize()` on an RGB image silently produced files whose transparency
index was declared but not honoured — they looked correct in the source render
and were opaque as delivered. `quantize(colors=64, method=FASTOCTREE)` on the
RGBA image is the form that preserves alpha into `tRNS`. The check is opening
the written file and reading a corner pixel's alpha.

## The guard

`addons/sapian_core/tests/test_app_icons.py` asserts that every root menu has
non-empty `web_icon_data`. A module promoted to an app without an icon fails the
build rather than shipping a blank tile. It asserts the **invariant**, never a
count of apps — the count changes every time a client installs a module.
