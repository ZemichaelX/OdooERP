# Sapian brand assets

The house identity. This directory is the source of truth for the logo files and
the palette; `addons/sapian_theme` consumes the primary colour and nothing else
reads from here automatically.

## Files

| File | What it is |
|---|---|
| `Sapian Logo.svg` | the mark alone — the four-petal pinwheel |
| `Sapian Logo+Name+Tag.svg` | mark, wordmark and tagline lockup |

Both are committed here as the originals. **Never recreate or trace them** — a
redrawn logo that looks close is worse than a missing one, because it propagates
silently into every client deployment.

## Palette

Four colours, read from the logo SVG source — and verified against the committed
files: `Sapian Logo.svg` contains exactly four colour literals, one per petal.

| Colour | Hex | Role |
|---|---|---|
| Deep teal | `#14454F` | **PRIMARY.** The brand. Buttons, accents, document colour. |
| Green | `#2F7E4F` | palette member — icon petal, accent |
| Burnt orange | `#C05628` | palette member — icon petal, accent |
| Amber | `#E39A42` | palette member — icon petal. **Fill only.** |
| Hairline grey | `#AAAAAA` | a 0.5px `stroke` outlining the petals, in the lockup only. Decorative — **not a text colour**: it measures 2.32:1 on white and fails AA at any size. |

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
common centre, each blade carrying one of the four palette colours. The SVG
confirms it — `Sapian Logo.svg` is a 512×512 viewBox with exactly one colour
literal per petal and no others.

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
