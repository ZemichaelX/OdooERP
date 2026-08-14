# SapianERP app icons — the design system

These icons are **generated, not hand-drawn**. To add an icon, write a function
in `draw.py` and run the script. Do not open a graphics editor and freehand one:
the value of the set is that it is a system, and a hand-drawn eleventh icon is
what breaks it.

## Why generated

The icon is only ever rendered at **23–39 px**:

| Where | Size |
|---|---|
| Command palette (Ctrl-K) | 1.8rem ≈ 23 px |
| Current-app header, drawer | 2em ≈ 26 px |
| App tiles, and the rail | 3em ≈ 39 px |

Nothing is ever drawn at 100 px. Everything below exists because of that number.

## The rules

1. **512 canvas**, exported to 256×256 PNG with alpha. Odoo core uses 100×100;
   256 downsamples cleanly to every render size and costs ~2 KB.
2. **Tints, never multiply.** Depth comes from blending a colour toward white
   (`tint()`), never from darkening or overlaying. Multiply produced mud — that
   is the single thing that made the first attempt look cheap.
3. **Three colours maximum**: one identity hue, a tint of it, and one palette
   accent. Never two darks together — teal and green next to each other are
   indistinguishable at 23 px.
4. **Corner radius ≈ 14 % of the short side.** Blade-cornered, not pill.
5. **Cut-outs are white and never thinner than 26/512.** Anything finer
   disappears at 23 px.
6. **No text, no glyphs, no numerals.** The birr sign was tried and became mush.
7. **One accent breaks one corner.** That is what makes the set read as a family
   while keeping each icon distinct in silhouette.
8. **Distinct silhouettes, not colour variants.** Two icons that differ only in
   hue are the same icon to someone scanning a sidebar.

## The palette

    TEAL   #14454F      GREEN  #2F7E4F
    ORANGE #C05628      AMBER  #E39A42

## Files

    sys_.py      palette, tint()/shade(), SVG scaffolding
    draw.py      one function per icon — the geometry
    *.svg        generated source
    deliver/     *__icon.png, ready to copy to addons/<module>/static/description/icon.png
    PROOF.png    all icons at 23, 26 and 39 px side by side
    IN-SITU.png  the set rendered in an actual Odoo app drawer

## Adding icon #11

1. Add a function to `draw.py` returning the SVG body for the new module.
2. Choose a silhouette no existing icon already owns. Check `PROOF.png` first —
   "Invoicing owns *document*" is why compliance became a shield.
3. Run the script. Open `PROOF.png` and look at the **23 px** column. If you
   cannot tell it apart from its neighbours at that size, it has failed,
   regardless of how it looks large.
4. Copy `deliver/<module>__icon.png` to
   `addons/<module>/static/description/icon.png`.
5. Declare it: `web_icon="<module>,static/description/icon.png"` on the root
   `<menuitem>`.

Step 3 is the one people skip. Every failed pass of this icon set failed because
it was judged at full size.

## The guard

`addons/sapian_core/tests/` asserts that every root menu has non-empty
`web_icon_data`. A module promoted to an app without an icon fails the build
rather than shipping a blank tile. The test asserts the **invariant**, never a
count of apps — the count changes every time a client installs a module.
