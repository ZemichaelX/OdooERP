# SapianERP Theme

The house identity: one brand colour driving the backend, the login page and
printed documents. Horizontal by design — nothing here assumes a client, a
sector or a company.

## Where the palette lives

**`static/src/scss/sapian_variables.scss`. That is the only file to edit.**

Change `$sapian-brand`, rebuild assets, done. Every other colour in the module
is derived from it with Bootstrap's own functions, and Python reads the same
declaration out of that file (`brand.py`) so the company record default cannot
drift from the compiled CSS.

```scss
$sapian-brand: #C416D3;                              // the one value
$sapian-brand-hover: shade-color($sapian-brand, 15%);  // derived
$sapian-brand-tint:  tint-color($sapian-brand, 90%);   // derived
```

`test_no_raw_hex_outside_palette` fails the build if a colour literal appears
anywhere else in the module, so "one edit" stays true rather than decaying into
a find-and-replace.

## How to re-brand

```bash
# 1. edit the one value
$EDITOR addons/sapian_theme/static/src/scss/sapian_variables.scss

# 2. rebuild assets on the tenant
docker compose -f docker/docker-compose.yml run --rm odoo \
  odoo -d <db> -u sapian_theme --stop-after-init
```

Verified: changing the value once moved `web.assets_backend` (160 occurrences),
`web.assets_frontend` (12) and `web.report_assets_common` (81) together, plus
the colour handed to newly created companies.

### After a re-brand: existing companies

Companies that **already exist** keep the colour stored on their record — the
same rule that protects a white-label client's colour also protects a stale
house colour. `sapian_brand_applied` tells the two apart: it stores the exact
pair we last wrote, so a company is "ours and stale" only when **both** colours
still match what we wrote.

**Nothing is ever rewritten automatically.** On every module update the theme
only *detects* drift and logs a warning naming the companies. Fixing colours on
a client's invoices as a side effect of an upgrade is the same class of fault as
a migration that silently skips a company: it works until the day it is wrong,
and nobody is watching when it is.

```python
# 1. see what would change — this is the DEFAULT, it writes nothing
env['res.company']._sapian_apply_brand()

# 2. apply, only when you mean it
env['res.company']._sapian_apply_brand(dry_run=False)
```

Both log what they did, including "nothing to apply", so a run that changed
nothing is distinguishable from a run that worked.

**Edge case, accepted and not solved:** a client who chooses a colour *identical*
to our house brand is indistinguishable from an untouched default, and will be
re-branded by a later `_sapian_apply_brand`. Their colour and ours are the same
value; nothing in the data can separate them. Also note a company whose pair was
half-edited by hand is left alone entirely — syncing one half would produce a
document in two brands.

## The two colour systems

Both reach a printed PDF and they are independent:

| | Source | Colours |
|---|---|---|
| **Assets** | `$sapian-brand` → compiled CSS | buttons, badges, statusbar, login |
| **Data** | `res.company.primary_color` | the document itself — header, headings, rules |

They never fight over the same pixel, but they can disagree about what the brand
*is*, which is why Python reads the SCSS rather than restating the value.

**Only two of Odoo's seven layouts use the colour at all.** Measured, by
grepping every `external_layout_*` template and by rendering the same invoice
through each:

| Layout | colour refs | rendered PDF |
|---|---|---|
| standard (the default), boxed, bold, striped, folder | **0** | byte-identical, 40,048 |
| wave | 2 | 40,571 |
| bubble | 2 | 40,519 |

`web.external_layout` falls back to `external_layout_standard` when a company has
chosen no layout (`report_templates.xml:830`). So a client on the default — or on
Boxed, Bold or Striped — gets a **monochrome document no matter what colour is
set**. And in Wave and Bubble the colour is purely **decorative**: two SVG
background shapes at `fill-opacity=".1"`, roughly 20% and 16% of the page. It is
never structural — no coloured rules, headings, table headers or totals.

*(Method note: the layouts do all render differently. An earlier version of this
file claimed Boxed, Bold and Striped produced byte-identical PDFs; they produce
different documents that coincidentally share a byte length of 40,048. Compare
hashes, not sizes.)*

### The default report layout

New companies get **Boxed** (`web.external_layout_boxed`): conservative
structure that suits documents carrying many required fields, and it survives
photocopying and mono printing — which is what actually happens to an Ethiopian
invoice, rather than being admired on a screen.

Set through the **same marker machinery as the colour**, for the same reason:
`sapian_layout_applied` records that we chose it, so a company that picked its
own layout is never touched, and a future change of house default can tell ours
from theirs. **New companies only** — nothing back-fills a layout onto an
existing company, and `test_existing_companies_keep_their_layout` enforces that.

**Treat as temporary.** Boxed does not use the brand colour at all. The
MoR-required invoice elements are a separate task that outranks the aesthetics
and will likely produce a custom layout that moots this choice.

## Contrast — measured, not assumed

| Pair | Ratio | WCAG AA (normal text) |
|---|---|---|
| white on brand | 4.77:1 | PASS |
| white on hover shade | 6.20:1 | PASS |
| brand on white | 4.77:1 | PASS |
| **brand on tint** | **4.08:1** | **FAIL** |
| hover shade on tint | 5.30:1 | PASS |

This is why badge text uses `$sapian-brand-ink-on-tint` (the shade) and never
the raw brand. A re-brand keeps the pair in step because both derive from the
one value — but **re-check these numbers after changing it**, since a lighter
brand can push white-on-brand below 4.5:1.

## If dark mode ever becomes reachable

Odoo 19 Community hardcodes the light scheme — `web/models/ir_http.py:72` is
`def color_scheme(self): return "light"`, with no override anywhere in Community
and no `web_enterprise` installed. The dark bundle compiles and is never served,
so this module ships **no** dark-mode variant.

`test_color_scheme_is_light_on_this_stack` encodes that assumption. When it
fails, dark mode has become reachable and the numbers below are live:

| brand as ink on | ratio | AA |
|---|---|---|
| Bootstrap `$gray-900` `#212529` | 3.23:1 | FAIL |
| Bootstrap `$gray-800` `#343a40` | 2.41:1 | FAIL |
| `#1a1a1a` | 3.65:1 | FAIL |

**The fix:** add a `.dark.scss` deriving a lighter variant from the same single
source — `color.scale($sapian-brand, $lightness: 30%)` measures 4.75:1 on
`$gray-900` and 5.36:1 on `#1a1a1a`. Do not paste a second hex.

**Read this part carefully, because it is the bit that gets misremembered:**
it is **brand-as-ink** that breaks, not the buttons. White text on a brand
*fill* is 4.77:1 in either mode — button fills are fine. The failure is the
brand used as text or as an accent line against a dark surface.

## Check these on upgrade

Ordered by how likely they are to break, worst first. All three fail *silently*
— the UI stays correct and usable, it just stops being branded.

1. **Active notebook tab indicator** — `sapian_backend.scss` overrides
   `.o_notebook .nav-tabs .nav-link.active`. This is the module's only
   class-based selector override. If Odoo renames those classes the rule stops
   matching and the tab reverts to Odoo's default underline.
2. **Form statusbar** — overrides the `--o-statusbar-background-active` /
   `--o-statusbar-border-active` custom properties declared in
   `web/static/src/views/fields/statusbar/statusbar_field.scss`. If Odoo renames
   them the declaration is ignored and the statusbar falls back to its neutral
   grey. **That fallback is a feature, not a caveat** — the form stays perfectly
   readable, it just loses the accent.
3. **`web._assets_primary_variables`** — the bundle we prepend into. The leading
   underscore marks it internal, but ten shipped Odoo modules extend it
   (`account`, `mail`, `portal`, `website`, `html_builder`, …), so breaking it
   would break Odoo's own code. Lowest risk of the three.

Only the statusbar is branded on its **active** stage; the rest stay neutral on
purpose, so the loudest element on a form is not the one carrying the least
information.

## Configuration

| Setting | Where | Empty behaviour |
|---|---|---|
| Support contact on the login page | `ir.config_parameter` → `sapian_theme.support_contact` | renders nothing at all — no empty box, no stray rule |
| Login logo | `res.company.logo` | falls back to the company **name as text**, never Odoo's stock placeholder |

## Scope

Colour and the primary-action treatment only. No layout, no spacing, no
typography. No sidebar, dashboard or menu work.
