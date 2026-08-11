# Sapian brand assets

The house identity. This directory is the source of truth for the logo files and
the palette; `addons/sapian_theme` consumes the primary colour and nothing else
reads from here automatically.

## Files

| File | What it is |
|---|---|
| `Sapian Logo.svg` | the mark alone — the four-petal pinwheel |
| `Sapian Logo+Name+Tag.svg` | mark, wordmark and tagline lockup |

> **STATUS: the two SVGs are NOT yet in this directory.** They live on the
> owner's Windows machine at `C:\Users\Dell\Downloads` and this repository is
> worked on from a Linux container that cannot reach that path. They must be
> copied in as-is — **do not recreate or trace them**, because a redrawn logo
> that looks close is worse than a missing one: it propagates silently into
> every client deployment. Everything else in this file is written and correct;
> only the two binaries are outstanding.

## Palette

Four colours, read from the logo SVG source.

| Colour | Hex | Role |
|---|---|---|
| Deep teal | `#14454F` | **PRIMARY.** The brand. Buttons, accents, document colour. |
| Green | `#2F7E4F` | palette member — icon petal, accent |
| Burnt orange | `#C05628` | palette member — icon petal, accent |
| Amber | `#E39A42` | palette member — icon petal. **Fill only.** |

### Contrast, measured

| Pair | Ratio | WCAG AA normal text |
|---|---|---|
| white on `#14454F` | **10.53:1** | PASS |
| white on `#2F7E4F` | 4.98:1 | PASS |
| white on `#C05628` | 4.56:1 | PASS |
| white on `#E39A42` | **2.34:1** | **FAIL** |

**The rule for amber: fill only.** `#E39A42` is never a button, never a text
background, never carries white text. It is a shape colour — an icon petal, a
chart series, a swatch. Anything a user has to *read* against needs one of the
other three.

For reference, the primary it replaced (`#C416D3`, a placeholder chosen before
the logo existed) measured 4.77:1 — a bare AA pass. `#14454F` more than doubles
that headroom.

## The logo mark, and the icon system

The mark is a **four-petal pinwheel**: four identical blades rotating about a
common centre, each blade carrying one of the four palette colours.

**Module icons reuse that motif.** Same blade shape, one of the four colours per
module. That is the whole system — a new module icon is the existing blade in a
different palette colour, not a new drawing. Written down here before the second
icon exists, because an icon set stays coherent only while the rule is cheaper
to follow than to break.

## Where the colour is actually used in code

`#14454F` appears in exactly one place in the codebase:

    addons/sapian_theme/static/src/scss/sapian_variables.scss   ->  $sapian-brand

Everything else derives from it — hover, tint, badge ink, the company document
colour — and `test_no_raw_hex_outside_palette` fails the build if a second
literal appears. The other three palette colours are **not** currently used by
any module; they are recorded here for the icon system and future accents.

To re-brand, edit that one variable. See
`addons/sapian_theme/README.md` for the procedure, including what happens to
companies that already exist.
