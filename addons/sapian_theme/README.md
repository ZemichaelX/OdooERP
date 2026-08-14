# SapianERP Theme

The house identity: one brand colour driving the backend, the login page and
printed documents, plus the **app rail** that makes the app icons visible on
desktop. Horizontal by design — nothing here assumes a client, a sector or a
company.

## The app rail

### Why it exists at all

**Odoo 19's desktop apps menu renders no icons.** `web.NavBar.AppsMenu` has two
branches: the small-screen one draws
`<img t-attf-src="{{app.webIconData}}"/>`, and the desktop one is a plain
`DropdownItem` with `t-esc="app.name"` — a text list
(`web/static/src/webclient/navbar/navbar.xml`). Icons therefore appear only in
the narrow-screen drawer and in the Apps list.

So the ten icons in `brand/icons/` were invisible on the screen a user actually
works in. The rail is what makes them exist.

### Why `main_components`, and not the navbar or the web client

Measured on this Odoo 19 tree, not assumed:

```bash
docker compose -f docker/docker-compose.yml exec -T odoo bash -lc \
  'cd /usr/lib/python3/dist-packages/odoo/addons && python3 - <<PY
import re, pathlib
pat = re.compile(r"registry\s*\.\s*category\(\s*\"main_components\"\s*\)\s*\.\s*add\(")
sites = []
for p in sorted(pathlib.Path(".").rglob("*.js")):
    if "/tests/" in str(p) or p.name.endswith(".test.js"):
        continue
    flat = re.sub(r"\s+", " ", p.read_text(errors="ignore"))
    n = len(pat.findall(flat))
    for a in set(re.findall(r"(?:const|let|var)\s+(\w+)\s*=\s*registry\s*\.\s*category\(\s*\"main_components\"\s*\)", flat)):
        n += len(re.findall(re.escape(a) + r"\s*\.\s*add\(", flat))
    if n:
        sites.append((str(p), n))
print("call sites:", sum(c for _, c in sites))
print("modules   :", len({s.split("/")[0] for s, _ in sites}))
PY'
```

| Extension point | Shipped Odoo modules using it |
|---|---|
| `main_components` registry | **20 registration call sites across 7 modules** — web, mail, website, html_editor, html_builder, point_of_sale, base_import |
| `patch(NavBar.prototype, …)` | **1** — website, which is also the only module to extend the `web.NavBar` template |
| inherit the `web.WebClient` template | **0** (mail patches `WebClient.prototype` in JS; nobody touches the template) |

The registry is the extension point Odoo itself reaches for twenty times. The
navbar is contested by exactly one module and the web-client template by none —
which measures how *unusual* those two are, not how safe. Registering a
component costs nothing another module can take away; the login-branding defect
below was precisely a lost inheritance contest.

> **Correction to the recorded number.** This count was previously written down
> as **21**-vs-1-vs-0. Re-measured on 19.0-20260723 with the command above it is
> **20** call sites (7 modules), 1, 0. The shape of the argument is unchanged;
> the number is not, so the number is corrected rather than repeated.

### The five things it depends on, none internal to the navbar

1. the `main_components` registry
2. the `menu` service — `getApps` / `getCurrentApp` / `selectMenu`
3. the `MENUS:APP-CHANGED` bus event
4. the `ACTION_MANAGER:UI-UPDATED` bus event, so a fullscreen action gets the
   whole screen — the same event and the same `mode !== "new"` guard `WebClient`
   uses for its own `state.fullscreen`
5. the `/odoo/<action-path>` URL shape, mirrored from `NavBar.getMenuItemHref`
   so a middle-click still opens a tab

Nothing is patched and nothing is inherited.

### 36 apps and 900 pixels

The design was drawn when a tenant had 14 root apps. It now has **36**. At the
48px pitch the rail uses that is **1,728px of tiles against a ~900px viewport**
— half the apps do not fit.

**The rail scrolls. Nothing is hidden, grouped, collapsed or truncated.**

What the user loses, stated plainly: on a 900px-tall screen roughly the bottom
half of a 36-app install needs a scroll gesture to reach. Measured on the build
database at 1366x900: `scrollHeight` 1728 against `clientHeight` 900, and
**18 of 36 tiles visible without scrolling**.

That is the cost, and it is the cheapest one available, because **36 apps do not
fit and every alternative pays more**:

| Alternative | Why not |
|---|---|
| Truncate with a "more" affordance | An app you cannot see is worse than an app you must scroll to. This is the failure mode the whole design refuses. |
| A pinned / favourites subset | Needs per-user state, a pin UI and a "show everything" escape hatch — three new surfaces — and a user who has pinned nothing sees an arbitrary subset. The unpinned apps still need somewhere to live, which is a scrolling list. |
| Group or collapse by category | Turns a one-click launcher into two clicks, and needs a grouping source we do not have without a new module dependency (below). |
| Smaller tiles | 36 × 28px is still ~1,000px, and the icons stop being legible — which defeats the only reason the rail exists. |

The scrollbar is deliberately left visible (`scrollbar-width: thin`). It is the
affordance that says *there is more below*; a rail that looked complete while
holding half the apps would be the silent truncation this design refuses.

Two things soften the cost:

- **The current app is scrolled into view** on arrival and after every app
  switch, so wherever you are, you can see where you are.
- **Order is menu sequence**, which is already the order of Odoo's own apps
  dropdown and its small-screen drawer. Two lists of the same things in two
  different orders is worse than one long list.

### Ordering: menu sequence, and why NOT the catalogue tier

`sapian.module.catalog` carries a `tier` (core / common / optional) and it is
the obvious ordering source. **It is not used, and should not be.**

Reaching for it would mean `sapian_theme` declaring a manifest dependency on
`sapian_core`. That is the exact dependency removed from `l10n_et_payroll` in
PR #21, on the principle that **a manifest describes what code NEEDS**. The rail
does not need the catalogue: it needs an order, and `load_menus` already carries
one. Three further reasons, none of them merely tidy:

- This module installs on a database carrying **no other sapian module** — that
  is a stated property of it, and a `sapian_core` dependency would end it.
- `tier` is per-company configuration a consultant edits for packaging reasons.
  Wiring it to the rail would make the app order jump when somebody re-tiers a
  catalogue entry for a reason that has nothing to do with navigation.
- Menu sequence is editable per client with **no code and no dependency**:
  Settings ▸ Technical ▸ User Interface ▸ Menu Items, change `sequence`.

And it already lands well. Measured on the build database, sequence alone puts
all three SapianERP apps in the visible band — SapianERP at position 1,
Ethiopian Compliance at 10, Ethiopian Payroll at 12 of 36 — with Apps and
Settings at the bottom where convention puts them.

### Below md

The rail is hidden below Bootstrap's `md` breakpoint and Odoo's own drawer
(`web.NavBar.AppsMenu.Sidebar`) handles small screens — and it *does* draw the
icons, so nothing is lost there.

The show/hide rule and the `padding-left` that makes room for the rail live in
**one media query** in `sapian_rail.scss`, because they cannot be allowed to
disagree: hiding the rail with Bootstrap's `d-none` would leave the element in
the DOM, the `:has(.o_sapian_rail)` padding would still match, and the web
client would be indented 52px around an empty strip.

The padding keys off `:has()` rather than a class on `<body>` so that it
appears and disappears **with the rail itself**, including when a fullscreen
action removes it. There is no second piece of state to keep in step.

### How it is guarded

`tests/test_app_rail.py` drives real headless Chrome, logs in, loads `/odoo` and
looks at the DOM the user gets — because a source assertion would have passed
straight through the login defect below, and would pass through an unrendered
rail for exactly the same reason.

There is **no expected tile count** in the file. The expectation is read per run
from `/web/webclient/load_menus`, so the guard stays correct on a database with
3 apps or 60; a fixed 36 would go red the first time a client installed one more
module.

`browser_js` *skips* when Chrome is missing, and a skip is a success signal
produced by doing nothing. So the `rail-render` CI job installs Chrome
(`scripts/install_test_browser.sh`) and then greps the log for the
`SAPIAN-RAIL …` lines the tests print **from inside the page**. A skipped run
cannot produce them, and the job fails when they are absent.

The guard is proved to discriminate by breaking, in the live DOM, each thing it
claims to check, and asserting it complains about each — then that it recovers.
What the browser printed on the 36-app build database:

```
SAPIAN-RAIL viewport=1366x900 apps=36 tiles=36 loaded=36 \
    visibleWithoutScrolling=18 lastReachableByScrolling=true
SAPIAN-RAIL-OVERFLOW forcedRailHeight=1680 contentHeight=1728 tiles=36 \
    visibleWithoutScrolling=35 lastReachableByScrolling=true
SAPIAN-RAIL-SMALL viewport=375x667 display=none padding-left=0

SAPIAN-RAIL-DISCRIMINATION no-rail       -> no .o_sapian_rail element in the DOM
SAPIAN-RAIL-DISCRIMINATION missing-tile  -> rail shows 35 tiles for 36 root apps
SAPIAN-RAIL-DISCRIMINATION iconless-tile -> sapian_core.menu_sapian_root: no
                                            <img> — fell back to the text initial
SAPIAN-RAIL-DISCRIMINATION restored      -> clean
```

**Two things that cost a debugging session, recorded so they do not cost
another:**

1. **A `ready` expression must evaluate to a BOOLEAN.**
   `ChromeBrowser._wait_ready` compares the CDP result against
   `{'type': 'boolean', 'value': True}` (`odoo/tests/common.py:1877`), so
   `document.querySelector(…)` — which returns an Element — is *never* ready.
   The test then times out after 60s with a websocket `TimeoutError` that looks
   like infrastructure trouble rather than a wrong expression. Use `!!`.
2. **Odoo's onboarding tour hijacks `/odoo`.** With `res.users.tour_enabled`
   stored `True`, the tour starts on page load and clicks its way into another
   app — moving the very highlight these tests assert on. `RailBrowserCase`
   turns it off in `setUp`.

## Where the palette lives

**`static/src/scss/sapian_variables.scss`. That is the only file to edit.**

Change `$sapian-brand`, rebuild assets, done. Every other colour in the module
is derived from it with Bootstrap's own functions, and Python reads the same
declaration out of that file (`brand.py`) so the company record default cannot
drift from the compiled CSS.

```scss
$sapian-brand: #14454F;                     // the one value — deep teal
$sapian-brand-is-dark: lightness($sapian-brand) < 40%;
$sapian-brand-hover: if($sapian-brand-is-dark,      // derived, luminance-aware
                        tint-color($sapian-brand, 15%),
                        shade-color($sapian-brand, 15%));
$sapian-brand-tint:  tint-color($sapian-brand, 90%);   // derived
```

The hover derivation is **luminance-aware and has to be**. Darkening is the
conventional hover, but on a dark brand it is invisible: `shade-color(15%)` moves
`#14454F` by −2.9pp of HSL lightness and reads as *disabled*. Lightening moves it
+12.0pp. The rule is general, not tuned to teal — for the previous mid-tone
magenta it takes the shade branch and reproduces exactly the value that was in
use. The full palette and the amber fill-only rule live in `brand/README.md`.

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

# 3. restart the server. The upgrade invalidates the compiled asset bundles and
#    a already-running process keeps serving the OLD asset hash, so reports
#    render unstyled until it restarts. Observed, not theorised.
docker compose -f docker/docker-compose.yml restart odoo
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

## Verifying a report — use the guard, never a bare render

**A PDF rendered outside a live server is not the PDF a client gets.**
wkhtmltopdf fetches the report stylesheet over HTTP from `web.base.url`, and when
it cannot it says nothing and renders the document unstyled — valid PDF, exit 0,
plausible size, and every layout identical. That fault cost three wrong
conclusions here before it was found.

`report_render.py` makes it impossible to hit by accident:

```python
from odoo.addons.sapian_theme.report_render import render_pdf_checked
pdf = render_pdf_checked(env, "account.report_invoice", invoice.ids)
```

It GETs the exact stylesheet URL the document links and raises
`ReportAssetsUnreachable` — naming the cause and the usual fix — rather than
returning a document that merely looks fine. Use it for any report verification.

## Contrast — measured, not assumed

| Pair | Ratio | WCAG AA (normal text) |
|---|---|---|
| white on brand `#14454F` | **10.53:1** | PASS |
| white on hover `#376169` | 6.83:1 | PASS |
| brand as ink on tint `#E8ECED` | 8.85:1 | PASS |

Badge ink is `$sapian-brand-ink-on-tint`, which follows the same dark/light
predicate: a dark brand is legible on its own tint and is used directly, a
mid-tone one is not — the previous magenta measured 4.08:1 and FAILED, so the
shade was substituted. Both cases stay correct from the one value.

**Re-check these numbers after any re-brand**, since a lighter brand can push
white-on-brand below 4.5:1. The other three palette colours and the amber
fill-only rule are in `brand/README.md`.

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

## The design lesson: prefer assets to template inheritance

Installing `website` proved this the expensive way, and the two halves of the
login page came out differently:

| Feature | Mechanism | Survived `website`? |
|---|---|---|
| Sign-in button colour | **asset-level CSS** — a scoped rule in `sapian_frontend.scss` | **yes** |
| Company logo | template xpath on `web.login_layout` | **no** — vanished silently |
| Support-contact line | template xpath on `web.login_layout` | **no** — vanished silently |

`website` inherits `web.login_layout` at **priority 20** and replaces the entire
`t[@t-call]` subtree with its own wrapper. Every node our xpaths anchored into —
the card, the card-body, the stock logo div — ceased to exist, and everything we
had injected went with them. Nothing errored. The page rendered, unbranded.

The CSS rule survived because a stylesheet does not care who built the DOM. It
matches whatever is there.

**So: on a layout that other modules also inherit, prefer asset-level styling.
When inheritance is unavoidable, expect a priority contest and test for it.**

Three concrete rules that follow, each of which cost a measured failure:

1. **Anchor in the least contested template.** The branding now lives in
   `web.login` (the page *content*), not `web.login_layout` (the *card*).
   Content is passed through `<t t-out="0"/>` into whichever wrapper wins, so it
   survives both the stock card and website's. Only the stock-logo deletion
   still touches the layout, because that node exists nowhere else.
2. **A priority bump is not automatically the fix.** Raising ours above
   website's 20 was tried: the login tests went from 2 failures to **4**, and at
   render time the page returned **HTTP 500** — `Element ... cannot be located
   in parent view`. Applying later means operating on a subtree that has already
   been thrown away. Where order *does* matter, state the priority explicitly
   and say what number it is defending against.
3. **A stored priority is not reset when the XML stops specifying it.** A
   database that ever carried a different value keeps it through every later
   upgrade — measured. Same class of trap as `web_icon_data` surviving the
   removal of `web_icon`. Specifying the number is what lets such a database
   heal itself.

The guard that now enforces this is the `theme-with-website` CI job: it installs
`website` *with* `sapian_theme` and runs `TestSapianThemeLogin`. Before it
existed the login tests passed on every CI run while being broken in any
database that had `website` — which is not academic, since `website_sale` pulls
`website` in and is a plausible client purchase.

## Check these on upgrade

Ordered by how likely they are to break, worst first. Every one of them fails
*silently* — the UI stays correct and usable, it just stops being branded.

0. **The app rail's three contact points with Odoo.** Highest risk in the
   module, because it is JavaScript against a framework rather than a colour.
   - `menuService.getApps()` and the `MENUS:APP-CHANGED` /
     `ACTION_MANAGER:UI-UPDATED` bus events. A rename empties the rail or
     leaves it stuck on the wrong highlight.
   - `.o_web_client` on `<body>` (`web/views/webclient_templates.xml:309`) —
     the padding hook. If it is renamed the rail overlaps the content.
   - `:has()` support in the CSS. Already relied on by Odoo's own backend
     bundle, so this breaks only if Odoo drops it.

   None of these fails quietly for long: `TestSapianAppRailRendered` renders
   the real page and asserts a tile per app with a decoded icon, and it asserts
   the padding is at least the rail's width.
1. **Login sign-in button** — `sapian_frontend.scss` overrides
   `.oe_login_form .btn-primary`. The frontend bundle **never** consults
   `$o-brand-primary`: `html_editor` (auto_install) rebuilds Bootstrap's
   `$theme-colors` map from the website editor's palette, and `.btn-primary` is
   generated from that map. If `.oe_login_form` is renamed the button reverts
   to Odoo's purple. `TestLoginPageIsActuallyBranded` asserts the brand in the
   **served** stylesheet, so this fails loudly rather than silently.
2. **Active notebook tab indicator** — `sapian_backend.scss` overrides
   `.o_notebook .nav-tabs .nav-link.active`. This is the module's only
   class-based selector override. If Odoo renames those classes the rule stops
   matching and the tab reverts to Odoo's default underline.
3. **Form statusbar** — overrides the `--o-statusbar-background-active` /
   `--o-statusbar-border-active` custom properties declared in
   `web/static/src/views/fields/statusbar/statusbar_field.scss`. If Odoo renames
   them the declaration is ignored and the statusbar falls back to its neutral
   grey. **That fallback is a feature, not a caveat** — the form stays perfectly
   readable, it just loses the accent.
4. **`web._assets_primary_variables`** — the bundle we prepend into. The leading
   underscore marks it internal, but ten shipped Odoo modules extend it
   (`account`, `mail`, `portal`, `website`, `html_builder`, …), so breaking it
   would break Odoo's own code. Lowest risk of the three.

Only the statusbar is branded on its **active** stage; the rest stay neutral on
purpose, so the loudest element on a form is not the one carrying the least
information.

## Odoo attribution

The login footer used to read **"Powered by Odoo"**, linking to
`odoo.com?utm_source=db&utm_medium=auth`. It is now "Powered by SapianERP" with
the Sapian mark, linking to sapiantech.com. The licensing position, established
before the change:

* **`web` is LGPL-3.** LGPL-3 incorporates GPL-3's terms plus additional
  permissions. The only clause about user interfaces is GPL-3 §5(d), and it is
  about *Appropriate Legal Notices* — defined in §0 as a copyright notice, the
  absence-of-warranty statement, the licence notice, and how to view the
  licence. "Powered by Odoo" with a UTM-tagged marketing link is none of those.
  §5(d) also says in terms: *"if the Program has interactive interfaces that do
  not display Appropriate Legal Notices, your work need not make them do so."*
  Odoo's login page displays no such notices. **Nothing in the licence requires
  the attribution.**
* **The licence conveys no trademark rights either way.** GPL-3 §7(e)
  explicitly contemplates a licensor *"declining to grant rights under
  trademark law for use of some trade names, trademarks, or service marks"*.
  The Odoo word mark and logo remain Odoo S.A.'s, and a copyright licence does
  not hand them over. That cuts towards removal, not against it: the risky act
  is *using* somebody's mark, not declining to.
* **Odoo S.A. publishes a separate trademark policy** at odoo.com/page/trademark
  governing use of the name and logo. **UNVERIFIED HERE:** that page could not
  be read from the environment this work was done in (the egress proxy blocks
  odoo.com), so it is not quoted, and no claim is made about its contents.
  Nothing in this change depends on it — the change *removes* every use of the
  Odoo name and mark from our surfaces rather than adding one — but if the
  question ever becomes "may we say we are built on Odoo", read that page
  first. Do not treat this paragraph as having answered it.

Nothing in Odoo is modified. Both templates are overridden by inheritance from
this module:

| Template | Emits the line on |
|---|---|
| `web.login_layout` | the login card, on a database without `website` |
| `web.brand_promotion_message` | the customer portal, surveys — and the login page itself when `website` is installed |

The second one is here because it was measured, not assumed: with `website`
installed the login page came back carrying **two** attributions, because
website replaces the login card with its own layout whose footer calls
`web.brand_promotion`. Overriding the shared message template fixes every
surface that emits it, once.

## The backend footer

A fixed bar across the bottom of every backend page: `© <year> <Company>. All
Rights Reserved.` plus `For Support: …`. Same shape as the app rail — a
component in the `main_components` registry, `position: fixed`, one
`padding-bottom` rule on `.o_web_client` guarded by `:has()`, nothing patched
and nothing inherited — and hidden below md and during a fullscreen action for
the same reasons.

Its text arrives through `session_info` (`models/ir_http.py`), because the
backend is an OWL application and server-side QWeb never runs there. It reads
**the same** `sapian_theme.support_contact` parameter as the login page: two
settings meaning the same thing is how one of them goes stale.

## Configuration

| Setting | Where | Empty behaviour |
|---|---|---|
| Support contact — login page **and** backend footer | `ir.config_parameter` → `sapian_theme.support_contact` | renders nothing at all — no empty box, no stray rule, no "For Support:" label |
| Login logo | `res.company.logo` | falls back to the company **name as text**, never Odoo's stock placeholder |

Neither is set by this module. `sapian_demo_trader` configures both for the
demo tenant (`_configure_login_page`), and `scripts/provision_client.sh` closes
public sign-up on a real client. A support contact that nobody configures
renders nothing — which is exactly how this feature shipped invisible for weeks
with a passing test.

## Scope

Two things, and nothing else:

1. **Colour** — the brand and the primary-action treatment. No spacing, no
   typography, no view layout, no dashboards.
2. **The app rail** — a persistent icon launcher, because Odoo 19's desktop
   apps menu draws no icons and the module already owns the icon assets.
3. **Whose product it looks like** — the login attribution and the backend
   footer. A theme that colours the buttons and leaves the page signed by
   somebody else has done half a job.

> This section previously read *"No sidebar, dashboard or menu work."* The rail
> makes half of that false, so it is rewritten rather than left standing.
> Dashboards and view layout are still out.

The rail lives here rather than in a module of its own because it must use the
palette — `$sapian-brand` and its derivations — and a separate module would
have to declare a dependency on this one to reach it, or restate the colour and
break the "one edit to re-brand" property that `test_no_raw_hex_outside_palette`
enforces. It adds no manifest dependency: `base` + `web`, as before.
