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

### Icon + label, 200px, with a collapse toggle

Built from `docs/SPEC-navigation-chrome.md` section 1. The values are the
spec's, and they are asserted as numbers rather than described:

| | Spec | Measured |
|---|---|---|
| Width | 200 expanded / 56 collapsed | 200 / 56, and `.o_web_client` padding tracks it |
| Row | 44px | 44px, checked on **every** row |
| Label | 13px / 600 | 13px / 600 |
| Rest | transparent, brand label | `rgba(0, 0, 0, 0)` / `rgb(20, 69, 79)` |
| Hover | brand at ~8% alpha, 6px pill | `rgba($sapian-brand, .08)`, radius 6px |
| **Active** | **solid brand, white label** | `rgb(20, 69, 79)` / `rgb(255, 255, 255)` |
| Focus | visible ring | `2px solid` brand, `:focus-visible` only |

**The active state is the point of the section.** The competitor's active and
inactive links have byte-identical computed styles — there is no way to tell
which app you are in from their sidebar. `TestSapianSidebarStates` compares the
two from `getComputedStyle`, never from the class list, because the class list
is exactly what they also have.

Three decisions worth stating, because each had an alternative:

- **The scroll container is still `<nav>` itself**, and the collapse toggle is
  `position: sticky` rather than living in a pinned header. The obvious
  structure would move `scrollTop`/`scrollHeight` onto an inner element, and
  `TestSapianAppRailOverflow` and `TestSapianAppRailKeepsScroll` both measure
  them on `.o_sapian_rail`. Those two are the only reason we know the rail
  neither truncates at 40 apps nor loses the user's scroll position; a
  structure that quietly moved what they measure would leave them green and
  measuring the wrong box.
- **Labels stay in the DOM when collapsed** and are hidden in CSS. The tile
  count therefore never changes with the state — `TestSapianAppRailRendered`
  checks it against `load_menus` — and the strings never stop being translated.
- **Collapse state is per BROWSER** (`localStorage`), not per user. The same
  person wants it open on a 27" monitor and shut on a laptop, so it does not
  belong in a `res.users` column that would follow them between the two.

Icons render at 24px, not the 39px in the spec table: a 39px icon in a 44px row
leaves 2.5px of vertical air and forces the row taller than the 44px the same
table specifies. The row height was taken as the binding constraint.

### The header is the mark — the first thing anyone sees

The top row of the sidebar is the product's logo, its wordmark, and the
collapse chevron, all inside one `<button>`.

What sat there before was a chevron and the word "Collapse". The top-left of
the screen — the position every desktop application uses for its identity —
was a UI control. And in the app list immediately below it, the first tile was
`sapian_core`'s app icon, because SapianERP is menu sequence 5, so the closest
thing to a mark on the page meant "the SapianERP **configuration** app".

Three things about how it is built:

- **The SVG is inline, not an `<img>`.** An `<img>` renders in a document of
  its own, where `currentColor` falls back to black; the mark takes the brand
  from `color` on the button. Same reasoning as the login page's mark.
- **The four `d` attributes are copied from `brand/Sapian Logo.svg`**, byte for
  byte, and they now appear in the repo twice: once in `views/sapian_mark.xml`
  (server QWeb, for the login page and the portal attribution) and once here,
  because an OWL template cannot `t-call` a server-side one. Two *renderings*,
  one source. `TestTheMarkIsTheCommittedLogo` asserts **both** copies against
  the committed file, so neither can drift into a redrawing —
  `brand/README.md`: *"Never recreate or trace them."*
- **The brand area is the toggle**, rather than a fourth row of chrome. It
  costs nothing in a panel that is already 1,634px of content at 36 apps, keeps
  the control where it cannot scroll away, and is a common pattern. A real
  `<button>`, so Enter and Space work with no key handling of our own.

#### `aria-expanded` had to be written as strings, and only the browser said so

The obvious spelling, `t-att-aria-expanded="!state.collapsed"`, is wrong. Read
off a running client:

| State | Served attribute |
|---|---|
| expanded | `aria-expanded=""` — OWL stringifies `true` to the empty string |
| collapsed | *attribute absent* — OWL drops it on `false` |

An empty value is not a valid ARIA state, and an absent one announces "this
control expands nothing" — the opposite of the truth in the state where it
matters most. Nothing in the template or the DOM tree looked wrong; only
reading the served attribute did. It is
`state.collapsed ? 'false' : 'true'` now, and `TestSapianSidebarHeader` asserts
both literals with `getAttribute` (the *property* would coerce and hide exactly
this).

That test also proves the mark **survives to the screen**, which the template
test cannot: an SVG can be in the DOM at 0×0, or painted in the browser's
default black because `color` never reached it, and a source-level check stays
green either way. Three breaks, each proved red:

| Break | What the test said |
|---|---|
| `t-att-aria-expanded="!state.collapsed"` | `aria-expanded is "" expanded and "null" collapsed` |
| `.o_sapian_rail_brand { width: 0; height: 0 }` | `the mark is in the DOM but renders at 0x0, so nobody sees it` |
| `fill="#000000"` instead of `currentColor` | `the mark paints "rgb(0, 0, 0)" — currentColor did not reach it` |

Collapsed, the mark stays and the wordmark and chevron go: at 56px the mark
alone is the affordance, and the tooltip says what the control does. Measured
on the 36-app database: `paths=4 mark=24x24 fill="rgb(20, 69, 79)"
word="SapianERP" expandedOpen="true" expandedShut="false" markShut=24x24`.

### CI runs the rail against 36 apps, not 14

The rail job used to install eight modules and get **14 root apps**, and at 14
apps *everything fits*: `scrollHeight` never exceeds `clientHeight`. So every
scroll and truncation assertion was either forced artificially
(`TestSapianAppRailOverflow` sets a height) or vacuous (`RAIL_RENDERS_JS`
scrolled a rail with nothing to scroll). Nothing in CI exercised a naturally
overflowing rail at the scale we ship — and both rail defects found on
2026-08-15 were about behaviour at that scale, both found by accident.

**14 apps is a configuration no client will ever run.** The job now installs
`sapian.module.catalog`'s own set — the same one `build_demo.sh --all-apps`
uses — with the country-before-chart phase the provisioning scripts do, and
gets **36**:

```
apps=36 tiles=36 loaded=36 visibleWithoutScrolling=19
overflows=true lastReachableByScrolling=true allVisibleWithoutScrolling=false
```

**19 of 36 visible. It overflows naturally.**

Two job-level assertions keep it that way, and both were proved red against a
real 14-app log before being trusted:

| Assertion | 14 apps | 36 apps |
|---|---|---|
| `MIN_RAIL_TILES=30` | RED — 14 < 30 | PASS |
| `overflows=true` present | RED — vacuous | PASS |

The second matters more than the first. A job that still had the apps but
stopped overflowing — a shorter row, a taller viewport — would satisfy every
marker while the reachability assertion quietly went back to proving nothing.

**The cost, measured rather than estimated.** Same machine, same suite: 14 apps
157s, 36 apps 425s. Calibrated against CI's own 14-app step (145s there vs 157s
here, so CI runs at 0.92×), the projected job is **8m41s against 4m58s**. The
14-app job is REPLACED rather than joined, so runner minutes go 20m01s ->
23m44s (**+19%**) and wall clock 4m58s -> 8m41s. The 14-app job's only unique
coverage was "few modules installed", which the theme-alone step already
provides.

### Measuring a client mid-boot — the defect that has now bitten twice

`browser_js`'s ready condition is satisfied as soon as the element you asked
for exists. That is *before* the default action has resolved, and until it does
the current app keeps changing — so the rail pulls the newly current app into
view, which is the rail doing its job and is indistinguishable, from a test's
point of view, from the rail losing your scroll position.

Any test that scrolls and then measures inside that window is measuring a
system mid-boot and calling the result a property of the system.

- `TestSapianAppRailKeepsScroll` was written with this defect and failed on
  correct code. Fixed in PR #35 by waiting on `action.currentController`.
- `TestSapianAppRailOverflow` had the same defect and was **passing by luck**.
  Before the wait: **3 red of 4 runs**. After it: **0 red of 10 consecutive
  runs**. (The sample sizes differ because the before-figure is what was
  observed when the flake was found, not a matched experiment.) The geometry
  was identical in every run, red and green alike —
  `forcedRailHeight=572 contentHeight=666 tiles=14 visibleWithoutScrolling=12`
  — with only `lastReachableByScrolling` flipping. The rail was never
  truncating.

The fix is always the same and it is never a sleep: wait on
`action.currentController`. A `setTimeout` passes on a slow runner by accident
rather than because the thing it waits for has happened.

#### Which `browser_js` blocks still lack the wait

Swept across the repo. Listed rather than fixed, because each needs its own
before/after run to prove the change did something:

| Block | Test | Status |
|---|---|---|
| `RAIL_RENDERS_JS` | `TestSapianAppRailRendered.test_the_rail_renders_one_loaded_icon_per_app` | **Fixed** — and the reason was not the one predicted. See below. |
| `RAIL_DISCRIMINATES_JS` | `TestSapianAppRailRendered.test_the_rail_check_discriminates` | **Fixed** — same wait. (There is no `TestSapianAppRailDiscriminates` class; an earlier version of this table invented one. Both blocks are methods of `TestSapianAppRailRendered`.) |
| `RAIL_HIDDEN_JS` | `TestSapianAppRailSmallScreen` | Left alone. Reads `display` and `padding-left` only — both CSS-static, no scroll, no active state, nothing that moves after first paint. |
| `FOOTER_REPORT_JS` and its two callers | `TestSapianBackendFooter*` | Left alone. Footer text and `paddingBottom`-vs-height; same reasoning. |

Already waiting, and safe: `RAIL_OVERFLOWS_JS`, `RAIL_KEEPS_SCROLL_JS`, all
four `SIDEBAR_*` blocks, and `LANDING_JS` / `STAYS_PUT_JS` / `OCCLUSION_JS`
(which wait through `ACTION_PROBE`).

#### `RAIL_RENDERS_JS` was not flaky. It was vacuous, which is worse.

Predicted high-risk by shape — `scrollTop = scrollHeight`, one frame, assert.
Measured instead of assumed:

| | runs | red |
|---|---|---|
| 14 apps (what CI ran) | 10 | **0** |
| 36 apps (what we ship) | 8 | **0** |

It never failed, and the 14-app line says why:

```
apps=14 tiles=14 loaded=14 visibleWithoutScrolling=14 lastReachableByScrolling=true
```

**Fourteen of fourteen visible.** The rail never overflowed, so
`scrollTop = scrollHeight` was a no-op and `lastReachableByScrolling=true` was
produced by there being nothing to scroll. It could not flake, and for exactly
the same reason it could not catch truncation. A test that cannot fail is not
passing.

At 36 apps it does overflow (19 of 36 visible) and still never failed — because
`sapianRailReport()` polls up to 10s for icon decode, which happens to give the
client time to settle first. Protection by accident, which disappears the moment
the icons are already decoded and which no reader could know was load-bearing.

So the fix is two things, not one: the settle wait made **explicit**, and the
assertion made **non-vacuous** by branching, with neither branch a skip —

```
overflows      -> the last app must be reachable by scrolling
does not       -> EVERY app must be visible without scrolling
```

— and the marker now reports `overflows=` so "it did not overflow" stops being
invisible. Both branches are proved to go red, on both a 14-app and a 36-app
database, by forcing each condition rather than depending on which database the
test happens to meet:

```
unreachable-tail  -> the rail overflows and the last app is NOT reachable ...
tile-outside-box  -> ... every one of its N apps should be visible ..., but only N-1 are
restored          -> clean
```

Two things that broke nothing on the first attempt, kept here because both look
like they should work: `overflow-y: hidden` does **not** stop a programmatic
`scrollTop` in Chrome, and displacing a tile with `top: 4000px` extends the
rail's scrollable overflow, which flips it into the *other* branch where the
tile is perfectly reachable. The breaks are geometric and horizontal instead.
Finding the second of those also showed the containment test was only checking
top and bottom, so a tile pushed sideways counted as visible; it now tests all
four edges.

### It clears the fixed footer

Both the sidebar and the footer are `position: fixed`, both are removed by the
same fullscreen guard, and the sidebar is `top: 0; bottom: 0` — so without a
clearance its last row sits behind the 28px strip: reachable by scrolling, and
unreadable once you get there.

The rule lives in `sapian_footer.scss`, not `sapian_rail.scss`.
`$o-sapian-footer-height` is declared there and that file loads *after* the
rail's (see `__manifest__.py`), so a clearance written in the rail's file would
compile against an undefined variable — and what the footer reserves is the
footer's business. Same `:has()` technique as the padding rules, so it appears
and disappears with the footer itself.

Measured at 1366x900 on the 36-app database: `railBottom 872`, `footerTop 872`.
`SIDEBAR_DISCRIMINATES_JS` sets `bottom: 0` on purpose and requires the check
to go red.

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

#### On app switch — not on every render

The first version of that scroll ran from `onPatched` unconditionally, and
`onPatched` fires for things that have nothing to do with which app you are in:
an action finishing, `state.fullscreen` flipping, the app list reloading. Every
one of those threw away wherever the USER had scrolled to. Measured on this
tree, with the rail scrolled to the bottom and one re-render forced:

| Root apps | `scrollTop` before | after, unguarded | after, guarded |
|---|---|---|---|
| 12 | 0 (no overflow) | 0 | 0 |
| 36 | 828 of 828 | **0** | 828 |
| 40 | 1020 of 1020 | **0** | 1020 |

So at 36 apps — the product target — the bottom twelve tiles left the viewport
on a re-render nobody connected to the rail. `scrollCurrentIntoView` now
compares the current app's ID against the last one it scrolled for and returns
early when it has not moved; an actual app switch still scrolls (switching to
Employees on the 40-app database leaves `scrollTop` at 156, not 0).

This is also what made `TestSapianAppRailOverflow` intermittent rather than
merely strict. That test sets `scrollTop` and measures a frame later, so a
re-render landing inside that window reset the position and the last tile read
as unreachable — same geometry, opposite result, on identical code. The rail
was never truncating; the measurement was being moved out from under itself.
`TestSapianAppRailKeepsScroll` covers the behaviour directly, and was proved red
against the unguarded code (`scrollAfter=0`) before being taken as green
(`scrollAfter=48`).

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

## The app launcher: two defaults, and why they live here

`vendor/oca_web/web_responsive` (pinned upstream code — see `vendor/README.md`)
adds a fullscreen app launcher and two **per-user** fields to control it. Both
ship at values that are wrong for this product, so `models/res_users.py`
re-defaults them:

| field | upstream | SapianERP | why |
|---|---|---|---|
| `is_redirect_home` | `False` | `True` | Otherwise login lands on the default app, which on our databases is a configuration screen — the Module Catalog on a provisioned tenant, the onboarding wizard on a fresh one. The launcher is the reason the module was vendored. |
| `apps_menu_theme` | `'milk'` | `'community'` | `'milk'` paints the launcher a pale lilac. `'community'` derives the same background from `$o-brand-primary`, which `sapian_variables.scss` already sets to `$sapian-brand`. `'milk'` is Odoo's colour on our screen — the login-page defect one layer up. |

Three properties are deliberate:

- **They stay per-user.** A default is what you get when nobody has expressed a
  preference; anyone who wants the old behaviour sets their own record and keeps
  it. `default_<field>` in the context also still wins, so scripted user
  creation and the demo builders can ask for something else.
- **No `depends` on `web_responsive`.** This module installs on a database
  carrying nothing else of ours, and adding the dependency would drag the
  launcher into every database that wants our branding. The fields are looked
  up at call time (`name in self._fields`), so the defaults simply do nothing
  until `web_responsive` is installed, and start applying the moment it is —
  with no update of this module.
- **Existing users are not touched.** `default_get` supplies a value only where
  none was given. An already-built tenant keeps every user as it found them,
  including an admin who will still land on the Module Catalog until someone
  sets the field. Rewriting a stored preference is a migration, not a default.

### Installing the module is not enough — measured

`default_get` fills a value only where none was given, so it never reaches a
user that already exists. On the databases we actually ship, that is the admin:

```
[1] odoo -d demo -i base                    admin created here.
                                            'is_redirect_home' in u._fields = False
[3] odoo -d demo -i ...,web_responsive      admin      -> False / milk
                                            new user   -> True  / community
```

Both `build_demo.sh` and `provision_client.sh` create the company and the admin
in an `-i base` phase, *before* the module that owns the field exists, so the
column default wins for the one user who is in every screen recording and every
handover. A build that installs the launcher and stops has a launcher nobody
lands on.

So provisioning applies them explicitly:

```python
env['res.users']._sapian_apply_launcher_defaults(dry_run=False)
```

It is a provisioning command, not a migration: called by name, never on install,
`dry_run=True` by default, and it logs the logins it moved so a run that moved
nobody is distinguishable from a run that worked. It is idempotent, it skips
`share` users, and it deliberately does **not** claim to tell a deliberate
opt-out from the shipped default — `is_redirect_home = False` is the same stored
value either way, which is exactly why the dry run prints the list first.

**For a tenant that already exists** (including the `sapianerp` build database),
that one call is the whole fix:

```bash
docker compose -f docker/docker-compose.yml run --rm -T odoo \
  odoo shell -d <db> --no-http --stop-after-init <<'PY'
env['res.users']._sapian_apply_launcher_defaults(dry_run=False)
env.cr.commit()
PY
```

Drop `dry_run=False` to see who would move without moving them.

### The third field, which outranks both and is not one of them

`res.users.action_id` — **Home Action**, on the Preferences tab of the user form
— decides the landing page *before* either setting above is consulted, by a
path that never reaches `web_responsive`:

```
session_info['home_action_id']              base/models/ir_http.py
  -> user.homeActionId                      web/static/src/core/user.js
  -> action_service._getActionParams()      falls back to it when the URL
                                            carries no action
  -> loadState() returns TRUE
  -> WebClient.loadRouterState() SKIPS _loadDefaultApp()
```

`_loadDefaultApp` is the only method `web_responsive` patches, and that patch is
the only code in the stack that reads `is_redirect_home`. So a user with a home
action never reaches the branch that would honour the launcher.

What it looks like is why it went unnoticed. `AppsMenu.setup()` opens the
launcher on its own, off `user.context.is_redirect_to_home`, independently of
`_loadDefaultApp` — so **the launcher paints, correctly, with every tile**. Then
the home action's controller mounts, fires `ACTION_MANAGER:UI-UPDATED`, and
`AppsMenu` closes itself on that event. Measured on `demo_selam` at 1366x900,
admin with `is_redirect_home = True` and the Module Catalog as home action:

| t | URL | what is on screen |
|---|---|---|
| 1205 ms | `/odoo` | launcher visible, 12 tiles |
| 1442 ms | `/odoo` | list view mounted underneath |
| 1562 ms | `/odoo/action-101` | launcher gone |

Roughly one second of a correct launcher, then a configuration screen, with
nobody touching the mouse. With `action_id` empty the same measurement holds at
the launcher indefinitely — 8 boots at 6× CPU throttling and 300 ms latency, 12
tiles every time, no navigation.

The destination is the Module Catalog for a reason that is worth writing down,
because it makes two different faults look identical: `sapian_core`'s root menu
is `sequence 5`, so **SapianERP is the first app**; its first leaf is Onboarding,
whose server action routes to the module catalogue once
`sapian_onboarding_done` is set. So both this fault and a plain
`is_redirect_home = False` land on `/odoo/action-101`, and the URL alone does not
tell you which one you have.

`_sapian_apply_launcher_defaults` therefore **clears the home action** on the
users it moves, and treats a home action as a reason to move a user. Writing
`is_redirect_home = True` and leaving `action_id` behind manufactures exactly
this defect — a stored setting that says launcher and a page that shows a list
view. It is the one thing the command removes that a person deliberately chose,
so the dry run names it per user (`login -> action name`) rather than counting
it. Nothing in this repository sets `action_id`; a person does, in Preferences.

Two smaller measured facts, both asserted in the tests because both are
counter-intuitive:

- Creating a user *with* a home action leaves `is_redirect_home = True`, not
  False. `_compute_redirect_home` is a stored **editable** compute, and our
  `default_get` supplies an explicit `True` at create time, which wins. Upstream's
  compute does not protect us.
- *Writing* `action_id` onto an existing user does flip the flag to False.

### How they are guarded

`tests/test_launcher_defaults.py`, and the guard is **the page, not the field**.
`assertTrue(user.is_redirect_home)` proves a column holds `True`; it does not
prove a teal pixel reached the screen, which is precisely the distance the login
defect hid in. So the browser tests log in as real users and assert what the
client loaded and what the launcher actually computed:

```
SAPIAN-LAUNCHER user=launcher.default.user launcherOpen=true actionLoaded=false
                theme=community items=12 brandInBackground=true milkInBackground=false
SAPIAN-LAUNCHER user=launcher.control.user launcherOpen=false actionLoaded=true
                action="dialog: Onboarding"
SAPIAN-LAUNCHER user=launcher.milk.user    launcherOpen=true
                brandInBackground=false milkInBackground=true
```

The second and third lines are **control users**, created with the opposite
value through `default_<field>`. Without them the first line would pass on a
database where the default did nothing at all — every user would reach the
launcher for some unrelated reason and no one would know. The expected brand is
read out of `sapian_variables.scss` at test time, so a re-brand does not leave
the test asserting the old colour and passing for the wrong reason.

One upstream test fails because of this, deliberately: `web_responsive`'s own
`TestResUsers.test_compute_redirect_home` asserts a new user has
`is_redirect_home == False`, which is the default being overridden. It cannot be
fixed — vendored code is never edited. The `launcher-defaults` CI job runs
upstream's *other* tests against our stack and requires them to pass; the
divergence itself is covered by `TestLauncherDefaultValues` on our side and by
the vendor tree-hash pin on upstream's. Asserting that upstream's test *fails*
was tried and removed — on a database with `account` it errors before running
rather than failing, for reasons in `vendor/README.md`, "Known divergence".

**Landing once is not the assertion.** Every line above samples inside the first
second, which is exactly the window in which the home-action defect looks
perfect. `TestLauncherStaysOnTheLauncher` therefore gives its user a home
action, hands it to the provisioning command, waits for the client to go quiet,
and then **sits still for another 2.5 s** before it looks — at
`location.pathname` as well as the DOM, because the URL is what an operator
reports and what a screen recording shows.

```
SAPIAN-LAUNCHER-STAYS user=launcher.stays.user earlyUrl=/odoo earlyLauncher=true
                      url=/odoo launcher=true items=6 actionLoaded=false action=""
```

It was proved to discriminate against the code before this change, in a browser,
not asserted to:

```
SAPIAN-LAUNCHER-STAYS user=launcher.stays.user earlyUrl=/odoo earlyLauncher=true
                      url=/odoo/users launcher=false items=0 actionLoaded=true action="Users"
FAIL: the client navigated away from the launcher on its own:
      /odoo -> /odoo/users (action "Users"). Nobody clicked anything.
```

Note `earlyLauncher=true` in the red run: the launcher did render first. That is
the whole reason a single sample cannot catch this.

The same file adds the assertion the rail's own suite does not make: with the
launcher open the rail is **covered**, and on dismiss it is reachable again,
with its tile count unchanged throughout.

```
SAPIAN-RAIL-OCCLUSION closed=true open=false owner="DIV.app-menu-container"
                      reopened=true tiles=12/12/12
```

`test_app_rail.py` asserts geometry and content — tile count, icon decoding,
padding — all of which stay true while something paints on top of the rail. It
would therefore stay green if the launcher started covering the rail
permanently, or stopped covering it and let the rail paint over the app grid.
Both are things a client sees immediately and CI would not.

Provisioning has its own guard, from the artefact rather than the config line:
`verify_launcher` (`scripts/lib/preflight.sh` + `scripts/lib/check_launcher.py`)
is called by both build scripts and reads the stored user values and the
compiled backend bundle — the launcher's CSS is present, and the `community`
theme's background carries the brand hex while `milk`'s does not, so "the brand
is in there somewhere" cannot pass by matching a rule no user's theme selects.
Proved to discriminate by resetting a tenant's admin to the upstream values and
watching it go red.

It also reads the **home action off the wire** — `"home_action_id"` in the
`session_info` embedded in the served `/odoo` page — rather than the field. That
is the byte the client reads to make this decision, and it is the only check in
the set that notices the defect above. On `demo_selam` with the home action set:

```
CHECK launcher_users_not_redirected=0        <- green
CHECK launcher_users_not_branded=0           <- green
CHECK launcher_home_action_on_wire=101       <- red
CHECK launcher_users_with_home_action=1
CHECK launcher_home_action_logins=admin -> Module Catalog
VERIFY_LAUNCHER_EXIT=1
```

and after `_sapian_apply_launcher_defaults(dry_run=False)`,
`launcher_home_action_on_wire=false` with exit 0. Two checks that were green
throughout, and a tenant that navigated away from the launcher every login.

The browser classes are tagged `-standard` and selected by the bare
`sapian_launcher` tag, because they need `web_responsive` installed and this
module does not depend on it. `/module` and `/module:Class` selectors implicitly require the
`standard` tag (`odoo/tests/tag_selector.py`), so they never run — and never
*skip* — in a suite with no launcher to look at. The `launcher-defaults` CI job
installs both on the demo tenant's module set and greps the log for the marker
lines above, so a run where the browser never reported cannot come out green.

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

1. **Anchor in the least contested template.** The logo and the support line
   live in `web.login` (the page *content*), not `web.login_layout` (the
   *card*). Content is passed through `<t t-out="0"/>` into whichever wrapper
   wins, so it survives both the stock card and website's.

   > **Amended, August 2026.** `sapian_theme_website` now deactivates
   > website's inheritance outright — it was serving the login page inside the
   > marketing site's header and footer (see that module's README). The card is
   > therefore no longer contested, and the ATTRIBUTION moved back into its
   > footer: on the form it reached `/web/login` only, while the card footer
   > also reaches `/web/signup` and `/web/reset_password`, which have no login
   > form and which lost their only attribution when the website footer went.
   > The logo and support line stay on the form — they read correctly there and
   > moving them would be churn. The rule survives its own amendment: anchor a
   > thing where every page that needs it will find it.
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
| `web.login_layout` | the login card — `/web/login`, `/web/signup` and `/web/reset_password`, in **every** configuration since `sapian_theme_website` stopped website replacing that card |
| `web.brand_promotion_message` | the customer portal and surveys |

> **Amended, August 2026.** The second row used to end "— and the login page
> itself when `website` is installed". That is no longer true, and the reason
> matters: the auth pages no longer render the website footer at all, so
> `brand_promotion_message` never reaches them. It is emphatically **not**
> deleted — the portal is the surface it exists for.

The second one is here because it was measured, not assumed: with `website`
installed the login page came back carrying **two** attributions, because
website replaces the login card with its own layout whose footer calls
`web.brand_promotion`. Overriding the shared message template fixes every
surface that emits it, once.

**The customer portal is deliberately in scope, and must stay there.** It reads
like over-reach, so the reasoning is written down in the template itself as
well: the login page is seen by the client's own staff, who know what software
they bought; the **portal is seen by the client's customers** — the quotation
they accept, the invoice they pay, the delivery they track. It is the one
screen in the product a third party looks at, which makes it *more*
brand-sensitive than the login page, not less. De-branding the login page and
leaving the portal alone fixes the private screen and leaves the public one.

## The backend footer

A fixed bar across the bottom of every backend page: `© <year> <Company>. All
Rights Reserved.` plus `For Support: …`. Same shape as the app rail — a
component in the `main_components` registry, `position: fixed`, one
`padding-bottom` rule on `.o_web_client` guarded by `:has()`, nothing patched
and nothing inherited — and hidden below md and during a fullscreen action for
the same reasons.

Its text arrives through `session_info` (`models/ir_http.py`), because the
backend is an OWL application and server-side QWeb never runs there.

### It signs itself SAPIAN, from constants a tenant cannot reach

It used to read `res.company.name` and the tenant's
`sapian_theme.support_contact`. Measured on the demo tenant, on every backend
page:

```
© 2026 Selam General Trading PLC. All Rights Reserved.
For Support: +251 11 123 4567 / support@selamtrading.example
```

Install that for Golbon Trading and it says Golbon, with Golbon's number. It is
the login page's "Powered by Odoo" defect pointed the other way — the product
on screen is not the product being sold — and the competitor gets this one
right: their footer carries the **consultancy's** name and the consultancy's
support lines. Now:

```
© 2026 Sapian Technologies PLC. All Rights Reserved.
For Support: +251 11 668 1234 / support@sapiantech.com
```

The values live in `vendor.py` as Python constants. Two alternatives were
considered and rejected:

| Home | Why not |
|---|---|
| `ir.config_parameter` | Technical > System Parameters is open to `base.group_system`, which on a client's own database **is the client**. The brief is that a client editing their own installation must not be able to change our footer. |
| A field on `res.company` | Same problem, one form earlier — and it would be per company, when there is one vendor. |

It is also not configuration. There is one vendor; a release is how a vendor's
own phone number changes, and a release is already the delivery mechanism.

`sapian_theme.support_contact` is **not** deleted. It is the tenant's own
number and still drives the **login** page, where the tenant's users are the
audience. The two contacts stopped meaning the same thing, so they stopped
sharing a setting.

The keys were renamed at the same time — `sapian_footer_company` and
`sapian_support_contact` became `sapian_vendor_company` / `sapian_vendor_support`
/ `sapian_vendor_url`. The old names said *the* company and *the* support
contact, which is precisely the ambiguity that let the tenant's values sit
there unnoticed; a component still reading an old key would have kept working
and kept being wrong.

`TestVendorFooterIsNotTheTenants` does not check that a constant equals itself.
It performs the two edits that used to move the footer — renaming the company,
setting the parameter — and asserts the served payload does not move.
Discrimination proved by putting the tenant-driven code back: **4 of 5 vendor
tests go red**, naming the company rename and the parameter individually.

## Configuration

| Setting | Where | Empty behaviour |
|---|---|---|
| Support contact — **login page only** | `ir.config_parameter` → `sapian_theme.support_contact` | renders nothing at all — no empty box, no stray rule, no "For Support:" label |
| Login logo | `res.company.logo` | falls back to the company **name as text**, never Odoo's stock placeholder |
| Vendor attribution — backend footer | **not configurable.** `vendor.py` constants; see above | n/a |

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
