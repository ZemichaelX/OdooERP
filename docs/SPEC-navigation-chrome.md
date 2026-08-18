# SapianERP — navigation chrome specification

Status: **ready to become a job** once the `web_responsive` evaluation reports.

## Provenance

Derived from a survey of conventional Odoo ERP navigation chrome, carried out
14 August 2026 at the owner's direction. The specific system surveyed, and the
measurements taken from it, are recorded in the internal notes and are not
reproduced here.

**The rule for this document: structure from them, values from us, and where
they got it wrong we do it properly rather than faithfully.** Nothing of their
palette, type or spacing is adopted. What is adopted is the *shape*, which is
conventional ERP chrome rather than anything proprietary.

Two facts that bound what we can copy:

- **The surveyed system runs Odoo 17 or earlier.** Its URLs use the pre-18 hash
  router, `/web#action=…&model=…`. Ours are `/odoo/action-101`. We are a full
  major version ahead.
- **Their sidebar comes from `muk_web_theme`** — fingerprints
  `body.mk_sidebar_type_large`, `div.mk_apps_sidebar_panel`, `img.mk_app_icon`,
  and their own logo served from `muk_web_theme/static/src/img/logo-01.png`.
  The public repo `muk-it/muk_web` has branches 8.0 → **16.0 only**. There is
  no 17, 18 or 19. That theme is not available to us, and will not be
  available to them either if they upgrade.

So the labelled sidebar cannot be downloaded. It is ours to build, on top of
the app rail already shipped in `sapian_theme`.

---

## Division of labour

| Capability | Source |
|---|---|
| Full-viewport app launcher | `web_responsive` (OCA, LGPL-3, 19.0.1.1.0) |
| In-place app search | `web_responsive` — and better than theirs, see below |
| Sticky list headers | `web_responsive` |
| Redirect after login | `web_responsive` |
| Labelled sidebar with states | **ours** — extend the existing rail |
| Fixed backend footer | **done**, PR #29 |
| Login page branding | **done**, PR #29 |

---

## 1 · The sidebar

Their measured values are given only as a reference point for proportion.

| Property | Theirs | **Ours** |
|---|---|---|
| Visibility | always visible, no collapse control exists | always visible, **with** a collapse toggle |
| Width | 185px | 200px expanded, 56px collapsed |
| Panel | `#FFFFFF`, `2px solid #DAD8D8`, radius 5px, `position: fixed`, `overflow-y: auto` | `#FFFFFF`, `1px` hairline, radius 6px, fixed, scrolls |
| Icon | 30×30, `border-radius: 50%`, 5px right margin | our 39px app icons, square with our own radius — they are drawn as tiles, not avatars |
| Label | Poppins 13px, weight 700, `#334756` | 13px, weight 600, `#14454F` |
| Row | padding `10px 11px`, height 61.6px | tighter — 44px row, labels do not need that much air |
| Overflow | scrolls, 1361px of content in a 646px panel | scrolls, ordered by menu sequence (decided in PR #25) |
| Bottom | client logo, **clipped off-screen at x = −39px** | **DEFERRED — see below.** Not built. |

#### The client logo at the bottom: deferred, 15 August 2026

Recorded as a decision so it is not re-derived as an oversight. Three reasons:

1. **It costs about 60px of a rail that already scrolls.** At 36 apps — the app
   count that matters, and the one CI now runs against — the sidebar is already
   1,634px of content in an 872px panel. Spending 60px of that on a logo takes
   it from the apps.
2. **The client's name is already in the navbar, top right.** The chrome does
   not need to say it twice.
3. **The footer now carries SAPIAN's attribution** (Item 2), so the chrome's
   identity question is answered elsewhere and answered once.

The competitor ships this element clipped at `x = −39px`, which is what
prompted the row in the table above. Not shipping it at all is a better answer
than shipping it correctly.

### States — the part they do not have

The extension checked directly: their active `<li>` receives `class="active"`
and **the computed styles of the active and inactive links are byte-identical.**
No fill, no bar, no colour change. There is no way to tell which app you are in
from their sidebar.

Ours:

| State | Treatment |
|---|---|
| Rest | transparent, label `#14454F` |
| Hover | brand teal `#14454F` fill at ~8% alpha, radius 6px pill, 150ms ease |
| **Active** | **solid `#14454F` fill, white label, persistent** |
| Focus | visible focus ring, keyboard-reachable |

Their hover is a solid `#1968AC` pill at radius 7px — the *shape* is good and
worth keeping; the colour is theirs.

---

## 2 · The app launcher

Theirs is a full-viewport Bootstrap dropdown: `position: fixed`, edge to edge
below a 46px navbar, `display: flex; flex-flow: wrap`, `padding-left/right:
20vw` at ≥992px, background a dark navy constellation image at `cover`.
Tiles are `width: 16.6667%` (six per row), icons `max-width: 70px` with
`box-shadow: inset 0 0 0 1px rgba(0,0,0,.2), 0 4px 4px rgba(0,0,0,.02)`,
labels white 14px weight 400.

**Take:** full-viewport rather than a dropdown; six per row at desktop; icon
above label; generous side padding.

**Do not take:** the constellation artwork, the white-on-dark label treatment,
the tile shadow stack.

**And fix what they got wrong:** *their launcher has no search.* Typing does
not filter the tiles — the first keystroke drops the user into Odoo's command
palette instead, which pre-seeds a `/` namespace and is a different mental
model entirely. `web_responsive` has real in-place filtering. That is a
capability we get for free and they do not have.

Hover on a tile: icon `translateY(-2px)`, shadow deepens from `0 4px 4px` to
`0 8px 8px`, 100ms ease-in. Tile background stays transparent. That is a good
interaction and worth matching exactly.

---

## 3 · Landing after login

**Theirs is not a dashboard.** Post-login lands on `#action=422 …
purchase.order` — the default action of whatever app happens to be first in
the sidebar. And loading bare `/web` throws a modal: *"Odoo Client Error — An
error occurred"*, with every network call returning 200, so it is a client-side
failure they ship.

Ours currently lands on the Module Catalog's list view, which is a
configuration screen and worse.

**DECIDED, 14 August 2026: land on `web_responsive`'s home — the app launcher.**

Free, immediate, and better than the competitor's, which lands on whichever
app happens to be first. A purpose-built compliance dashboard (VAT period
status, payroll due, withholding to declare, cash-cap breaches) remains a real
feature worth building, but as its own piece of work — not as a blocker on
navigation.

---

## 4 · The footer — already shipped in PR #29

The conventional shape: `position: fixed`, height 40px, white ground, a 1px top
rule, a soft upward shadow, and `body { padding-bottom: 40px }` to clear it. A
centred copyright line at 13px weight 600 in a muted grey; a right-aligned
`For Support:` label followed by `tel:` links in the house accent. Stacks to a
column at ≤1024px with `min-height: 70px`.

Ours matches the shape, in brand teal. One thing they get wrong and we should
not: their loading pill overlaps the fixed footer strip.

#### Whose name it carries: SAPIAN's, from constants — 15 August 2026

PR #29 drove it from `res.company.name` and the tenant's
`sapian_theme.support_contact` parameter, which is the wrong half of the
competitor's idea. Measured on the demo tenant before Item 2:

```
© 2026 Selam General Trading PLC. All Rights Reserved.
For Support: +251 11 123 4567 / support@selamtrading.example
```

Install that for Golbon Trading and every backend page signs itself Golbon,
with Golbon's support number. It is the login page's "Powered by Odoo" defect
pointed the other way — the product on screen is not the product being sold —
and the competitor gets this one right: their footer carries the
**consultancy's** name and the consultancy's numbers.

The values are Python constants in `addons/sapian_theme/vendor.py`, not
`ir.config_parameter` and not `res.company`. Technical > System Parameters is
open to `base.group_system`, which on a client's own database is the client;
so is the company form. A client editing their own company must not be able to
change our attribution, and constants are the only home where they cannot.
It is also not configuration: there is one vendor, and a release is how a
vendor's own details change.

`sapian_theme.support_contact` is NOT deleted — it is the tenant's number and
still drives the login page, where the tenant's own users need it.

Guarded by `TestVendorFooterIsNotTheTenants`, which does not check that a
constant equals itself: it renames the company and sets the parameter — the
two edits that used to move the footer — and asserts the served payload does
not move.

---

## 5 · Sticky list headers

Theirs: the document does not scroll; scrolling happens inside
`div.o_list_renderer` (`overflow: auto`), and `thead` is `position: sticky;
top: 0; z-index: 1; background-color: #F8F9FA`. The control panel — New
button, breadcrumb, search, pager, view switcher — sits outside the scroll
container and stays put.

`web_responsive` provides this. Nothing bespoke required.

---

## 6 · Things they do that we deliberately will not

| Theirs | Why not |
|---|---|
| Login page prints demo credentials in a box on the page | Harmless on a throwaway instance, but exactly the kind of thing that reaches a client by accident. Assert against it in provisioning. |
| Database selector visible on the login page | `list_db = False` and a pinned `dbfilter` per deployment |
| Bare `/web` throws a client error | Land somewhere deliberate, with no error path |
| Client logo clipped at x = −39px | Position it properly |
| Loading pill overlaps the fixed footer | It should not |
| No collapse control, width hardcoded per breakpoint | A real toggle, useful at 36 apps |
| Idle auto-logout with a visible countdown in the navbar | Not copying, but worth noting they have one; it is a genuine ERP requirement and may be a later feature |

---

## 7 · Best practice they lack, and so do we

- Keyboard navigation through the rail, with a visible focus ring
- Contrast checked at the sizes actually rendered, not at full size
- The rail's 36-app scroll behaviour, already decided in PR #25: scroll,
  nothing hidden, ordered by menu sequence, current app scrolled into view

---

## Open before this becomes a job

One thing only: **whether `web_responsive`'s launcher and our rail can
coexist.** That is the question the pending evaluation answers, and everything
above assumes the default outcome — we keep our rail and take only the
launcher. If they fight irreconcilably, the fallback is to build the launcher
ourselves from this spec, which is a larger job but not a different one.

Landing target is settled: the launcher.
