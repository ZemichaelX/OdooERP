# Changelog

All notable changes to SapianERP. Epics per `docs/plan-2026/10-claude-code-roadmap.md`.

## [Unreleased]

### Ethiopian companies booked every purchase into an asset (2026-08-17)
Core `l10n_et` names **`2301` Goods in Transit**, an `asset_current` account, as
the company's default expense account. Odoo's chart loader copies that into the
product-category default, and `_get_product_accounts` resolves
product → category → company — so every product without an account of its own
booked its purchases into a current asset.

The profit & loss account therefore showed revenue with **no cost of sales**, and
inventory never reached the balance sheet. Nothing complained, because **the books
still balanced**: a balanced ledger cannot tell a misclassified debit from a
correct one. Measured on a demo tenant: `230100` at **453,800.00**, the
inventory-valuation journal **empty**, and a single 54,000.00 purchase overstating
reported profit by **54,000.00**.

`l10n_et_base` now points the default at **`5111` Cost of Goods and Services**
through the template merge, and moves existing companies with
`_l10n_et_base_fix_default_expense_account` (post-init hook + `19.0.1.5.0`
migration) — **only** those still on the core default, so a client's own choice
survives.

Proved red first: **4 of 4** guards failed on the pre-fix tree, including
*"posting a 54000.00 purchase moved the derived profit & loss by 0.00"*. Green on
**both** install paths afterwards — fresh `-i` and `-u` upgrade, 71 tests, 0
failed, 0 skipped — because a template change applies at install and is skipped at
upgrade, and CI installs while clients upgrade.

**Core Odoo's defect, not ours: every Odoo-based Ethiopian deployment has it**,
competitors included. Filed upstream as
[odoo/odoo#282865](https://github.com/odoo/odoo/issues/282865); this override
stays the interim measure regardless, since a merged upstream fix would not reach
a database that has already loaded the chart. Defect register entry 26.


### The labelled sidebar (2026-08-15)
The app rail becomes a sidebar: icon **and label**, 200px expanded / 56px
collapsed, 44px rows, 13px/600 labels, and a real collapse toggle. Built from
`docs/SPEC-navigation-chrome.md` section 1 and measured on the 36-app database
`build_demo.sh --all-apps` produces.

The **active** state is the point of the section. The competitor's active and
inactive links have byte-identical computed styles — there is no way to tell
which app you are in from their sidebar. Ours: `rgb(20, 69, 79)` fill with a
white label against a transparent row with a brand label, compared from
`getComputedStyle` rather than from the class list.

Reachable at 36 **and** 40 apps (36/36, 40/40, walked across the whole scroll
range). Clear of the fixed footer — `railBottom 872`, `footerTop 872` — with the
clearance in `sapian_footer.scss`, because `$o-sapian-footer-height` is declared
there and that file loads after the rail's. Keyboard reachable with a 2px
`:focus-visible` ring; the toggle is a real `<button>`.

### TestSapianAppRailOverflow was passing by luck (2026-08-15)
It forced the rail to overflow, scrolled to the bottom and measured — without
waiting for the client to settle. Until the default action resolves the current
app keeps changing, and pulling the newly current app into view is the rail
doing its job; it just lands inside the measurement window. Ten consecutive
runs of the rail job, identical geometry every time
(`forcedRailHeight=572 contentHeight=666 tiles=14`): **3 red of 4 runs before
the fix, 0 red of 10 after**. Nothing about the assertion changed — `lastReachableByScrolling` must
still be `true`. What changed is *when* it measures: it now waits on
`action.currentController`, the same signal `TestSapianAppRailKeepsScroll`
already waited on, and not on a sleep.

Second time a test in this suite has been found passing by luck. The remaining
`browser_js` blocks without a settle wait are listed in
`addons/sapian_theme/README.md`.

### Public sign-up was open on every 36-app installation (2026-08-15)
**Security.** `website_sale` is in `sapian.module.catalog` — something we sell.
Its post-install hook opens public sign-up on the tenant that buys it:

```python
# website_sale/__init__.py:15
env['website'].search([]).auth_signup_uninvited = 'b2c'
```

Measured on the product's own 36-app configuration
(`build_demo.sh <db> --all-apps`): the parameter said `b2b`, the website row
said `b2c`, `/web/login` served "Don't have an account?", and
`CHECK login_signup_scope=b2b` was **green**.

The guard was reading a value that had stopped being the authority. The login
controller asks `res.users._get_signup_invitation_scope()`; `auth_signup` reads
the parameter and `website` overrides it to prefer the per-website column, and
**neither calls `super()`** — so the highest class in the MRO ends the chain.
Third time a check here was right when written and wrong afterwards because the
system moved underneath it (`login_primary` green while the page said "Powered
by Odoo"; `is_redirect_home` True while `action_id` decided the landing).

Closed by `sapian_theme_website`, an `auto_install` bridge — the override has
to sit above `website` in the MRO, and `sapian_theme` depends on base + web
only, so its version of this was dead code in every configuration. Opt back in
with `ir.config_parameter sapian_theme.allow_public_signup`.
`check_login_page.py` now reports `login_signup_effective`, taken from the
method the controller calls, alongside the inputs that feed it.

### The login page carried two attributions (2026-08-15)
With `website` installed, `/web/login` said "Powered by SapianERP" twice: once
from the login form's own block and once from `website.layout`'s footer calling
`web.brand_promotion_message`. The login form's own wins — it is the one that
renders on every database — and the promotion template now stands down on
`/web/login` alone. `/web/signup` and `/web/reset_password` extend
`web.login_layout` rather than `web.login`, so it remains their only
attribution, and the portal is untouched.

### scripts/lint.sh blocked a legitimate push on Windows (2026-08-15)
It hardcoded `python3` for the pylint-odoo import check. On Git Bash `python3`
is the Microsoft Store stub by default: on `PATH`, imports nothing. The only
blocking control in this repo reported "pylint-odoo is NOT INSTALLED" on a
machine where it was installed under `python`. It now tries `$SAPIAN_PYTHON`,
`python3`, `python`, `py` until one can actually import what is needed, and
prints which one it used.

### A database at the real navigation scale (2026-08-15)
`build_demo.sh <db> --all-apps` installs every module in
`sapian.module.catalog` and produces **36 root apps** — the product target.
Without the flag the same script still produces 12, so `demo_selam` is
unaffected. The install list is read from the catalogue rather than typed into
the script, and two floors (≥30 catalogue modules, ≥30 root apps) stop it
reporting success having installed nothing.

### The social welfare levy on imports (2026-08-15)
**3% of the aggregate CIF value of imported goods**, Council of Ministers
Regulation No. 519/2022, effective 6 August 2022 (gazetted 22 August 2022).
Built in the order CLAUDE.md rule 10 requires: reference calculator, golden
tests, effective-dated configuration, and only then the `account.tax`.

Three properties, each held by something that fails rather than by a comment:

* **In addition** to duty, excise, VAT and surtax. Posted bill: CIF 1,250,000
  → total 1,287,500.
* **A cost, not a receivable.** The tax posts to a new expense account `5931`
  *Social Welfare Levy on Imports*, and a constraint refuses any configuration
  whose tax posts to a receivable. A competitor's published guide calls this an
  "Import Advance Income Tax ... offset against income tax"; no authority for
  such a tax was found, and that wiring would capitalise 3% of every consignment
  as an asset that is never recovered. A test builds exactly that tax and
  asserts the refusal.
* **In nobody else's base.** `include_base_amount = False` *and*
  `is_base_affected = False`, asserted against posted amounts: VAT comes out at
  187,500 (15% of CIF) and not 193,125; a surtax stand-in at 125,000 and not
  128,750.

**No threshold**, stated explicitly and pinned — the withholding rules in the
same file have thresholds of 20,000 and 10,000, which is the standing invitation
to invent one here.

**The commencement date is not an Ethiopian month boundary.** 6 August 2022 is
**Hamle 30, 2014 EC** — the last day of the month, one day before Nehase 1. It
joins the enumerated statutory-date guard, xfailed with a dated reason, exactly
like the two seeds already there. Nothing was "fixed" to make it pass.

Also corrected: the note in `l10n_et_wht_config.py` listing taxes that must not
be added from a summary table still named the social welfare levy. It is now
implemented from its instrument, so it is off that list — and the five
withholding categories that remain on it are named, with the reason (rates
known, effective dates not).

### One lint definition, and the theme is not optional (2026-08-14)

**`sapian_theme` joins `provision_client.sh`'s default module list.** It stopped
being decoration when it took on the de-branding, the login layout, the app
rail, the support contact and the backend footer: a tenant provisioned without
it is handed Odoo, with a link to odoo.com on the page its staff open every
morning. Verified from the served bytes, not from the config line — provisioning
now ends by asserting the tenant serves a SapianERP login, and refuses to hand
over a database that does not.

That check is **one definition**, `scripts/lib/check_login_page.py` plus
`preflight.sh::verify_login_page`, called by both `build_demo.sh` and
`provision_client.sh`. It used to be inline in the demo script only, which is
precisely how the demo came to be verified while the thing we sell was not.

**The customer portal stays SapianERP.** The reasoning is now recorded beside
the override, because it reads like over-reach and would otherwise be narrowed
by someone reading a diff: the login page is seen by the client's own staff,
the portal by the client's CUSTOMERS — the quotation they accept, the invoice
they pay. It is the one screen a third party sees, so it is more
brand-sensitive than the login page, not less.

**`scripts/lint.sh` is now the only definition of lint**, called by CI's lint
job and by a new `pre-push` hook. It gates on **exit codes**, never on parsed
output, because a red CI build came from reading pylint's "rated at 10.00/10"
while it was exiting 4. It also refuses to run when a tool — or the
`pylint-odoo` plugin — is missing, since pylint without its plugin prints a
score having checked none of the Odoo rules. Proven to discriminate by putting
the original W8150 import back: `!! lint FAILED: pylint`, exit 1, with
10.00/10 printed directly above it.

### The login page a client actually sees (2026-08-14)
Five defects, all client-facing, all invisible to every check we had — because
every check we had talked to the database or to a compiled asset, and none
asked what comes back on the wire. `build_demo.sh` reported
`login_primary=#14454F`, correctly, about a page that said **Powered by Odoo**.

**Attribution.** The login footer now reads "Powered by SapianERP" with the
Sapian mark, linking to sapiantech.com, in brand teal. The licensing position
was established first and is written down in `addons/sapian_theme/README.md`:
LGPL-3 requires no UI attribution (GPL-3 §5(d) is about *Appropriate Legal
Notices* — copyright, warranty, licence — which a UTM-tagged marketing link is
not), and the licence conveys no trademark rights either way (§7(e)), which
cuts towards removal rather than against it. Odoo's own trademark policy page
could not be reached from this environment and is therefore **not** quoted or
relied on. Nothing in Odoo is modified: two templates are overridden by
inheritance. The second one, `web.brand_promotion_message`, is there because
with `website` installed the page came back carrying **two** attributions.

**Sign-up.** Odoo's default for "Customer Account" is `b2c` — free sign up —
so every demo and every client login page invited strangers to create an
account on a private company ERP. Neither the demo tenant nor
`provision_client.sh` set it; both do now, reading the parameter key off Odoo's
own field rather than typing `auth_signup_uninvited` (which is the field name;
the key is `auth_signup.invitation_scope`).

**Support contact.** sapian_theme has had a configurable support line, and a
test asserting it renders, since the theme shipped. No build ever configured
it, so it rendered nothing — a feature indistinguishable from one nobody wrote.
The demo tenant configures it now.

**The button's other states.** The brand fix covered the resting state.
`--btn-disabled-bg` and `--btn-focus-shadow-rgb` were unset and fell through to
Odoo purple, and the disabled one is not an edge case: `login.js` adds
`disabled` on submit, so the button turned purple at 65% opacity for the
duration of every login. All five states are now derived from the palette.

**A backend footer**, matching what a competitor puts on every screen:
`© <year> <Company>. All Rights Reserved. For Support: …`, driven by the same
support parameter as the login page. Same shape as the app rail — a component
in `main_components`, `position: fixed`, one `padding-bottom` rule, hidden
below md and during fullscreen actions.

**And the check that was missing.** `build_demo.sh` now renders `/web/login`
through Odoo's own WSGI application as an anonymous visitor and asserts on the
returned HTML: 200, a size floor (so absence can only be measured on a page
that rendered), no Odoo attribution, our attribution present, no signup link,
the configured support contact actually visible, and the button branded in
every state. Proven to discriminate by restoring the shipped state on a built
demo: `login_odoo_refs=2`, `login_signup=1`, `login_support_rendered=0`,
`login_signup_scope=b2c` — while `login_primary` stayed green, which is exactly
how this survived.

### The Ethiopian calendar, and a date that had been wrong in plain sight (2026-08-14)
New module `l10n_et_calendar`, in two layers per CLAUDE.md rule 10: the
conversion is pure arithmetic, so it lives in `reference/et_calendar.py` with
125 goldens in `tests_fast/` that need no Odoo, and the ORM layer only calls it.

**The arithmetic.** Leap iff `year % 4 == 3`, no century exception, taken from
the calendar's definition rather than inferred from examples; epoch Meskerem 1,
1 EC = JDN 1,724,221; Julian Day Number as the pivot. Validated against three
authorities that are not this code's own output: the project's proclamation
anchors, an independent integer Julian implementation, and a recorded one-off
cross-check against the `ethiopian-date` package. Both traps in the brief are
tested rather than assumed — Hamle 1 is **not** always 8 July (it steps to the
7th for part of each cycle, and an earlier claim in this repo that it never does
was wrong), and the Gregorian-year offset flips between +7 and +8 at the
Ethiopian new year.

**A date nobody had questioned.** Asked what 1 August 2025 converts to, the
answer was Hamle 25, 2017 EC — mid-Ethiopian-month, where every effective date
this project has verified against a proclamation lands on day 1. That is a
checkable property, so it is now checked: `tests_fast/` enumerates every
statutory effective date we ship and asserts each lands on day 1. It found a
**second** one that had never been flagged anywhere — the cash cap seed,
`date(2025, 7, 1)` = Sene 24, 2017 EC, from the same proclamation whose PAYE
bands commence on Hamle 1. Both are marked `xfail(strict=True)` with dated
reasons pointing at the unresolved gazette question: visible in every run, and
loud if somebody corrects a seed without removing the marker. **No seed was
changed** — a calendar agreeing with a knowledge base is corroboration, not a
primary source.

**The mirror.** `l10n.et.date.mixin` gives any model a stored, indexed,
searchable Ethiopian twin of a Gregorian date, read-only, with two per-company
settings (display format, and which calendar prints on documents). What is
stored is canonical — `2017-11-01`, not "Hamle 1, 2017" — so the format setting
cannot invalidate a million rows, the column sorts correctly, and one Ethiopian
month is one prefix filter. Measured, not guessed: a mirrored date costs ~22 MB
per million rows, two cost ~36 MB, and the index turns a 30 ms sequential scan
into 7.9 ms. Module README carries the numbers and the collation caveat.

**On documents.** Two auto-installing bridges — `l10n_et_calendar_account`
(invoice date, due date) and `l10n_et_calendar_purchase` (order deadline,
expected arrival) — put the dates on the form, in the list and on the printed
PDF, with the company setting deciding which calendar prints. Each bridge is
two field declarations and two view inheritances and **no logic at all**: a
rule implemented twice in two bridges is a rule that will diverge, and these
would diverge on a date.

The purchase side forced the mixin to grow one thing. `date_order` and
`date_planned` are **Datetimes**, Odoo stores those as naive UTC, and Ethiopia
is UTC+3 — so an order placed at 01:00 in Addis (22:00 UTC the day before)
would have been filed a day early. The conversion through Ethiopian local time
lives in the mixin, keyed off the source field's own type, with both sides of
the midnight boundary tested; setting the timezone to UTC turns four tests red.

CI gains a `calendar-standalone` job, because the module's central claim is that
it stands alone and the integration job installs it beside everything else we
ship: it installs the calendar on a database with nothing else of ours,
asserts that from `ir_module_module`, uninstalls it, asserts the columns went
with it, and reinstalls. A second step in that job walks the three states an
auto-install bridge has to get right — Accounting alone (no bridge), plus the
calendar (the invoice bridge appears by itself, the purchase one does not),
plus Purchase (the second appears) — and then uninstalls both and asserts the
columns went with them.

### The demo you rehearse on is now the demo you show (2026-08-14)
Two flagged-but-unfixed items, and a third gap found while answering the
question about them.

**The demo was Odoo purple with no app rail.** `build_demo.sh` installed the
demo module and not `sapian_theme`, so the tenant a prospect sees contradicted
the white-labelling pitch in the same session. Now installed — and, because a
config line saying `-i sapian_theme` is exactly what a purple demo would also
have, step [5/5] READS THE COMPILED STYLESHEET: `--primary`, the navbar
background, the login button and the app rail's padding rule must all come back
branded, or the build exits non-zero instead of failing on camera. Run against
a build without the theme, all five checks go red.

Recorded because the ask cannot be met as literally worded: **`#714B67` is NOT
the purple on screen.** The backend's unthemed primary is `#71639e`, and
`#714B67` still appears ~13 times in a *correctly* themed bundle (html_editor
palettes and friends), so "must not contain #714B67" would fail a good build.
The checks assert the positive — the rules a prospect actually sees carry
`#14454F` — which is both stronger and true. The frontend bundle's `:root
--primary` is still `#714B67`; that is the separately-queued finding from
PR #23, now PRINTED as a NOTE on every build rather than filed away.

**Every order showed the build timestamp.** Established before changing
anything: this is **Odoo's own default**, not ours. `sale.view_quotation_tree`
(`sale/views/sale_order_views.xml:216`) explicitly replaces `date_order` with
`create_date`, and this repo ships no `sale.order` view. Fixed in the demo's own
view, which never reaches a client database, so Odoo's behaviour is untouched
for everyone else. A second cause needed fixing too: Odoo rewrites `date_order`
to `now()` on confirmation (`_prepare_confirmation_values`), so even orders
created with a July date came out stamped today. All seven now read Jul 6–30.

**And the dress rehearsal had not run since PR #24.** Asked whether the two
provisioning paths diverge, the answer turned out to be worse than divergence:
`scripts/dress_rehearsal.sh` died on

    UserError: Odoo is currently processing a scheduled action.

`_onboard_company` handed the wizard `Command.set(catalog.ids)` — the WHOLE
catalog. That was a no-op only while the catalog held 15 curated entries;
seeding all 38 turned it into **28 uninstalled modules** (crm, mrp,
point_of_sale, website, …) that the wizard tried to install mid-provision.
`sapian_demo_trader` was fixed for exactly this in PR #24 and the rehearsal was
not.

**Nothing caught it because the guard could not fire.** The wizard SKIPS module
installation in test mode, so every test of that module ran in the one mode
where the failure is impossible — green tests, dead script. The pick now goes
through one shared `sapian.module.catalog._filter_safe_to_pick`, used by both
tenant builders, and `test_catalog_pick.py` asserts the mode-independent fact
instead: every entry handed to the wizard is already installed.

Deliberate divergence, kept and documented: different month, volume and payroll
roster (the rehearsal's five employees exercise the transport-allowance cap and
a pension-exempt foreigner, and its exam recomputes each of their payslips), and
no client logo on a tenant nobody is shown. Everything else — theme, salesperson,
catalog pick — was an accident and is now closed.


### The demo tenant is a demo again — `sapian_demo_trader` (2026-08-14)
Three gaps found while writing the user guide, each of which forced an apology
mid-demo.

**An empty Sales pipeline.** The Sales app opened on nothing, so there was no
quotation to walk from quote to invoice — the most ordinary thing an ERP is
bought to do. Now three drafts, one sent, and one confirmed and delivered but
deliberately **not invoiced**, so there is a real order to press *Create
Invoice* on live. Three new Ethiopian customers (Rift Valley Contractors,
Hawassa Homes, Tsehay Hardware), all with TINs, at the catalogue's own sourced
prices. **Nothing in the pipeline posts to the ledger**, so every VAT, WHT and
payroll golden is untouched by construction rather than by luck.

**And the reason the pipeline looked empty was worse than empty.** Odoo's Sales
app opens on `sale.action_quotations_with_onboarding`, context
`{'search_default_my_quotation': 1}` — a default filter of `user_id = uid`.
Provisioning runs through `odoo shell` as OdooBot, so every order was stamped
with OdooBot as salesperson and the demo login opened Sales on zero rows — at
which point **Odoo renders its onboarding SAMPLE DATA over the list**: ghosted
quotations for Henry Campbell and Thomas Passot, priced in dollars, under a
"Beat competitors with stunning quotations!" video. American names and USD in
software sold as Ethiopian, and it survived because "there are orders in the
database" was true. Screenshotted on a built demo before the fix. The
salesperson is now set explicitly on every order, and the test asserts it
through the same filter the app applies.

**A payroll run that showed a flat progressive tax.** A run and three payslips
did exist — the gap was narrower than reported but real: they occupied only 3 of
the 6 PAYE bands in Proclamation 1395/2025 and never reached the top one, so the
progressive table could not be pointed at. The roster is now six employees with
job titles, one per band: Cleaner 1,800 (0%) · Office Assistant 3,500 (15%) ·
Storekeeper 6,000 (20%) · Sales Officer 10,000 (25%) · Driver & Loader
10,000 + 2,000 overtime (30%) · General Manager 25,000 (35%). Two people on the
same 10,000 basic landing in different bands is the demonstration that an input
line moves the tax while the pension base does not follow it. Totals move to
gross 58,300, PAYE 11,525, pension 3,941/6,193, net 42,834, journal 64,493 —
**hand-computed in the test docstring, not read out of a run**, and produced by
the real engine from wages, never written as literal amounts.

**Odoo's default logo.** `uses_default_logo` was True, so every demo invoice
carried the Odoo wordmark while the branding claim was being made in the same
session. The tenant now carries its own generated geometric mark
(`static/img/selam_logo.png`) — **deliberately not the Sapian logo**: Selam
General Trading is the demo CLIENT, and printing the vendor's brand on the
client's letterhead teaches a prospect the opposite of white-labelling. The
guard asserts `uses_default_logo is False`, not that `logo` is non-empty —
`res.company.logo` has `default=_get_logo` so it is *always* non-empty, and a
"non-empty" check passes on exactly the broken state.

Guards added as invariants rather than counts: every band in the company's own
effective-dated PAYE table must be occupied by a payslip (a future proclamation
adding a band makes this fail, which is correct); the pipeline must hold drafts,
a sent quotation and a confirmed order, with no invoice on the uninvoiced ones.

The module README described a **different tenant entirely** — Fasika
Supermarket, teff, Awash Agro, a VAT credit of −2,850, none of it in the code —
and has been rewritten against what the module actually creates. It is what a
salesperson reads the night before a demo.

### The app rail — `sapian_theme` (2026-08-14)
**Odoo 19's desktop apps menu draws no icons.** `web.NavBar.AppsMenu` has two
branches: the small-screen one renders `<img t-attf-src="{{app.webIconData}}"/>`,
the desktop one is a plain `DropdownItem` with `t-esc="app.name"`
(`web/static/src/webclient/navbar/navbar.xml`). So the ten icons drawn for
`brand/icons/` were invisible on the only screen a user works in. The rail is
what makes them exist: a persistent icon launcher down the left edge, one tile
per root app.

**A component in `main_components`, nothing patched, nothing inherited.**
Measured on this tree: 20 registration call sites into that registry across 7
shipped modules; 1 module patches `NavBar.prototype` (website); 0 inherit the
`web.WebClient` template. *(The count recorded earlier as 21 re-measures as 20;
the number is corrected in `addons/sapian_theme/README.md` rather than
repeated.)* Five dependencies, none internal to the navbar: the registry, the
`menu` service, `MENUS:APP-CHANGED`, `ACTION_MANAGER:UI-UPDATED`, and the
`/odoo/<action-path>` URL shape.

**36 apps, ~900 pixels: the rail scrolls, and nothing is hidden.** At a 48px
pitch, 36 apps is 1,728px against a 900px viewport — measured `scrollHeight`
1728 / `clientHeight` 900, with 18 tiles visible without scrolling. Every
alternative costs more than a scroll gesture: a "more" affordance hides apps
outright, a pinned subset needs per-user state plus a scrolling overflow list
anyway, grouping doubles the clicks, and smaller tiles make the icons illegible
— which is the only reason the rail exists. The scrollbar is deliberately left
visible as the "there is more below" affordance, and the current app is scrolled
into view on every switch.

**Order comes from menu sequence, NOT the catalogue tier.** Using `tier` would
mean `sapian_theme` depending on `sapian_core` — the exact dependency removed
from `l10n_et_payroll` in PR #21, on the principle that a manifest describes
what code NEEDS. Sequence already orders Odoo's own apps dropdown and drawer, is
editable per client with no code (Settings ▸ Technical ▸ Menu Items), and
already lands the three SapianERP apps at positions 1, 10 and 12 of 36.

**Guarded in a real browser, because a source assertion would have passed
through the login defect too.** `tests/test_app_rail.py` drives headless Chrome,
logs in, loads `/odoo` and asserts one tile per app with a decoded icon —
expectation read per run from `/web/webclient/load_menus`, never a fixed 36.
Measured: `apps=36 tiles=36 loaded=36 visibleWithoutScrolling=18
lastReachableByScrolling=true`; at 375x667 `display=none padding-left=0`. The
same check is run against a deliberately broken DOM (rail removed, tile removed,
icon removed) and asserted to complain about each, then to recover.
`browser_js` *skips* when Chrome is missing, so the new `rail-render` CI job
installs one (`scripts/install_test_browser.sh`) and requires the browser's own
`SAPIAN-RAIL …` log lines — which a skipped run cannot produce.

### SapianERP house identity — `sapian_theme` (2026-08-10)
First UI work in the repo. One brand colour (`#C416D3`, provisional) driving the
backend, the login page and printed documents, from a single file:
`addons/sapian_theme/static/src/scss/sapian_variables.scss`.

**One edit, proven.** Changing `$sapian-brand` once and rebuilding moved
`web.assets_backend` (160 occurrences), `web.assets_frontend` (12) and
`web.report_assets_common` (81) together, plus the colour handed to new
companies. The hook is the SCSS variable chain — `$o-brand-primary` →
`$primary` → Bootstrap `$theme-colors` — prepended into
`web._assets_primary_variables`. **Odoo 19 has no CSS-custom-property input for
backend colour**: `var(--primary)` appears in 0 files under `web/static/src`;
the `--primary` properties that exist are Bootstrap's generated *outputs*.
Everything else derives with `shade-color()` / `tint-color()`; a test fails the
build if a colour literal appears anywhere else in the module.

**Two colour systems reach a PDF, and a re-brand can leave them disagreeing.**
Assets come from the SCSS; the document itself comes from
`res.company.primary_color` as data. Python reads the SCSS so the *default*
cannot drift — but a company row stores a copy, and the rule that protects a
white-label client's colour also protects a stale house colour. Verified: after
a re-brand the report CSS still carried the old value in `.o_company_1_layout`.
**OPEN DECISION**: record which colour we set, so a later re-brand can tell
"ours, stale" from "theirs, chosen". Until then, existing companies need an
explicit pass after a re-brand.

**Also found:** Odoo's default report layout ignores the colour completely —
`web.external_layout` falls back to `external_layout_standard`
(`report_templates.xml:830`), which never reads `primary_color`. Only Wave,
Bubble, Bold, Boxed and Striped use it. A client on the default gets a
monochrome document whatever colour is set.

**Dark mode: none shipped, deliberately.** Odoo 19 Community hardcodes
`color_scheme() -> "light"` (`web/models/ir_http.py:72`) with no override
anywhere and no `web_enterprise`, so the dark bundle compiles and is never
served. The brand fails WCAG AA as ink on every plausible dark surface
(3.23:1 on `$gray-900`, 2.41:1 on `$gray-800`) — but white on a brand *fill* is
4.77:1 either way, so it is brand-as-ink that would break, not buttons. The
assumption is encoded in `test_color_scheme_is_light_on_this_stack`, not left as
prose: when dark becomes reachable the test fails and points at the README
recipe (`color.scale($sapian-brand, $lightness: 30%)`).

**Accessibility:** brand-on-tint measures 4.08:1 and FAILS AA for normal text,
so badge ink uses the derived shade (5.30:1) and never the raw brand.

Verified: installs and uninstalls cleanly on a database carrying no other sapian
module (0 leftover views); 11 module tests; a company with a pre-set colour was
untouched (`#1a7f5a` before and after, hook reported "0 companies") while a new
company got the brand; two real invoice PDFs rendered and inspected.

**Re-brand drift, option (c).** A company row stores a *copy* of the colour, so
after a re-brand an old house colour and a client's deliberate choice look
identical. `res.company.sapian_brand_applied` holds the exact pair we last
wrote, so the two can be told apart. **Detection never writes**: on module
update the theme logs a warning naming the drifted companies and changes
nothing — rewriting client-facing document colours as a side effect of an
upgrade is the same class of fault as a migration that silently skips a
company. Applying is explicit and dry-run by default
(`_sapian_apply_brand()` reports; `_sapian_apply_brand(dry_run=False)`
applies), and both halves of the pair move together or neither does. A
half-edited pair is left alone entirely. Accepted edge case, documented in the
README: a client who picks a colour identical to ours is indistinguishable from
an untouched default.

**Only two of Odoo's seven report layouts use the colour at all** — measured by
grepping every `external_layout_*` template and by rendering the same invoice
through each. standard (the default), boxed, bold, striped and folder reference
it **zero** times and produced byte-identical 40,048-byte PDFs; only wave
(40,571) and bubble (40,519) differ, and there the colour is purely decorative —
two SVG shapes at `fill-opacity=".1"`, ~20% and ~16% of the page. No coloured
rules, headings or totals in any layout. Choosing a default layout is still
open, and the MoR-required invoice elements outrank the aesthetics.

### List-view sums and status badges ✅ (2026-08-10)
Eight `sum=` totals added, all `fields.Monetary`, all in the owning module:
payroll run's payslip list (basic salary, gross, PAYE, pension EE/ER, other
deductions, net — the batch totals checked before filing), payslip input lines
(`amount`), the VAT declaration list (output/input/net) and the WHT summary
(`total_wht`).

Rejected, deliberately: PAYE band `rate`, pension `employee_rate`/
`employer_rate` and the three WHT config rates (percentages — summing tax rates
is meaningless and they already render as `percentage`); cash-cap and allowance
`cap_amount` (effective-dated configuration thresholds — a column of caps summed
would not merely be meaningless, it would read like a policy figure and someone
would eventually quote it); payslip input `taxable` (Boolean); pharma quantities
(mixed units — the quintal/bag work exists because they do not add up).

Verified in our own install rather than inferred: core already sums
`account.move`, `purchase.order` **and all three `sale.order` list views**
(`view_order_tree`, `view_quotation_tree`, `view_quotation_tree_with_onboarding`
— `amount_untaxed`, `amount_tax`, `amount_total`), so no core inheritance is
needed. Badge decorations were also already in place on all four status columns
including `stock.lot.pharma_state` (success/warning/danger, monotonic); the one
real gap was the import dossier's status badge on the **form**, which was
undecorated while the list version was colour-coded.

### Brand colour: deep teal, and a guard for report verification ✅ (2026-08-11)
**Primary is now `#14454F`**, from the logo. `#C416D3` was a placeholder chosen
before the logo existed and appears nowhere in the brand. Not a hex swap: the
hover/tint recipe was derived for a mid-tone colour and `shade-color(15%)` on a
dark primary moves HSL lightness by only −2.9pp — a hover that reads as
*disabled*. The derivation is now luminance-aware (`$sapian-brand-is-dark`):
dark brands lighten, light brands darken. It is a general rule, not a teal
special case — for the old magenta it reproduces exactly the previously
approved `#A713B3`, which a test pins. White on the new primary is 10.53:1
against the old 4.77:1. Full palette, contrast table and the amber
(`#E39A42`) fill-only rule now live in `brand/README.md`, together with the
four-petal pinwheel motif and the rule that module icons reuse the same blade
in a different palette colour.

**`report_render.py` — the harness hole becomes a guard.** wkhtmltopdf fetches
the report stylesheet over HTTP from `web.base.url`; when it cannot, it renders
the document unstyled and says nothing — valid PDF, exit 0, and every layout
identical. `render_pdf_checked()` GETs the exact stylesheet URL the document
links and raises `ReportAssetsUnreachable`, naming the cause and the fix, rather
than returning a document that merely looks right. Proved to discriminate: it
passes against a live server, fails against a dead port, and it caught a real
404 during this very change — a palette upgrade invalidates the compiled
bundles and an already-running server keeps serving the old asset hash, so the
re-brand procedure now includes a server restart.

### Default report layout: Boxed, for new companies only ✅ (2026-08-10)
`web.external_layout_boxed` is set on companies at creation, through the same
marker machinery as the colour (`sapian_layout_applied`): a company that chose
its own layout is never touched, and nothing back-fills a layout onto an
existing company. Temporary by intent — Boxed uses no brand colour, and the
MoR-required invoice elements task will likely produce a custom layout.

**Correction to the previous entry.** It reported that Boxed, Bold, Striped and
Standard produced byte-identical PDFs and inferred a partial render failure.
That was wrong, and wrong in a way worth recording: the comparison used
`len(pdf)`, and three genuinely different documents share a byte length of
40,048. Hashing them gives three distinct SHA-256 values; reading
`external_report_layout_id` back at render time confirms each layout was in
effect; the HTML differs for all five (lengths 27,915–29,206);
`attachment_use=False` with zero stored PDFs rules out caching. The layouts are
real and structurally distinct — only their *colour* usage is nil for five of
seven. Comparing sizes instead of contents is the same weak-check pattern this
repo keeps having to remove.

### Demo: the units are now visible, and the build asserts it ✅ (2026-08-10)
The quintal/bag pair was created correctly — 30 quintals in, 60 bags on hand,
verified on a fresh build — and shown to nobody. Odoo gates every UoM field on
`uom.group_uom` ("Units of Measure & Packagings"), the provisioner never
enabled it, so on a freshly built demo database the product form showed no unit
and the purchase order had no unit column. The demo's headline moment was data
with no way to see it: the same fault class as seeding a catalog nothing calls.

- `_enable_multi_uom()` links `uom.group_uom` into `base.group_user` — exactly
  what `res.config.settings` does for a `group_` field, done directly because
  `execute()` also installs/uninstalls modules from its `module_` fields, which
  must never happen mid-provision. Called before the idempotency early-return,
  so demo databases built before this pick it up on their next run.
- `test_multi_uom_setting_is_enabled` asserts it the way the settings screen
  asks it (`res.config.settings.default_get`), not by re-stating the write.
- **`build_demo.sh` gained a verification phase** that asserts rather than
  suggests. The one-company check used to be a printed hint at the end; it is
  now `CHECK companies=1`, `CHECK charts=et` and `CHECK group_uom=True`, each
  with an explanation of what breaks, and the build exits non-zero if any
  fails. Both of these properties have regressed silently before — a demo that
  fails now fails on the command line instead of on camera.

### Demo installs only what it demonstrates ✅ (2026-08-10)
`sapian_demo_trader` depended on `crm`, `mrp`, `project`, `mass_mailing`,
`fleet`, `repair`, `maintenance` and `website_sale`, and **none of them was
touched by the demo data** — the transitive closure of the seven real
dependencies is 35 modules and contains none of the eight. They were listed
only because `_onboard_company` handed the wizard the entire 15-entry
`STANDARD_CATALOG` and the wizard's install step has to be a no-op
mid-provision. The cost was the **main menu bar** of a tenant built for a 2–5
person hardware shop, which is in every frame of a screen recording.

**This is two changes, and either alone does nothing** — picking fewer catalog
entries only unblocks the removal; the manifest is what installs a module.

1. `_onboard_company` hands the wizard `DEMO_CATALOG_TIERS` (core + common).
2. The eight are gone from the manifest.
3. `test_catalog_dependencies` relaxed to "picked entries ⊆ deps", **plus its
   converse**: `test_unpicked_catalog_apps_are_not_dependencies` fails if an
   optional app creeps back into the dependency list. That is the regression
   that would otherwise be silent — it reappears in the menu bar while every
   other test still passes. Proved to discriminate: run against a database
   built with the old manifest it reports all eight as leaked.

Menu bar, from `load_menus()` (what the web client renders, not a record
search), on databases built from nothing with `build_demo.sh`:

```
BEFORE  SapianERP | Discuss | Calendar | To-do | Contacts | CRM | Sales |
        Dashboards | Invoicing | Project | Website | Email Marketing | Purchase |
        Inventory | Manufacturing | Maintenance | Repairs | Employees | Fleet |
        Apps | Settings
AFTER   SapianERP | Discuss | Sales | Dashboards | Invoicing | Purchase |
        Inventory | Employees | Apps | Settings
```

21 → 10. Calendar, To-do and Contacts went too — they rode in on `crm`/`project`.

The eight are **not hidden**: all 15 catalog entries are still seeded, so the
catalog reads 7 enabled / 8 available. "Here is what you are buying, here is
what is there when you want it" is a better answer to "so it does
manufacturing?" than pretending the apps do not exist.

The `env.get("website")` reassignment in `_configure_demo_login` went with
`website_sale`: it existed only because installing that module creates a website
owned by the base company (`website/data/website_data.xml`, module data — so it
applied even with Odoo demo data off), which then blocks archiving it. Residual
case, accepted: installing `website` separately and *then* this module would
make that archive raise. Unsupported (`check_no_demo_modules.sh` keeps demo
modules off client databases) and exercised by nothing.

### Demo tenant: building materials, one company, built like a client ✅ (2026-08-09)
The sales demo is a revenue asset, not a test fixture. Two changes, both in the
module so every future demo database is correct by construction — no database
is ever hand-edited.

**1. The tenant builds with Odoo demo data OFF.** `sapian_demo_trader` shipped
its content in `demo/`, so it only loaded when Odoo demo data was enabled —
which also loaded Odoo's fixtures: `My Company (San Francisco)`, `My US
Company`, `My Company (Chicago)`, plus a website bound to the wrong company (the
crossover failures and the un-loginable database we hit on the last upgrade). A
prospect must never see a US company list in software sold as Ethiopian.

- Provisioning is no longer triggered by installation at all. `demo/` was
  wrong (it loads only with Odoo demo data on, which drags in the US
  placeholder companies); `data/` turned out to be worse — module data loads
  MID-install, so the wizard charted the company and `account`'s end-of-load
  `_auto_install_template` hook then re-loaded the chart (`Account codes must
  be unique … 230100`), which CI caught and a local run had not. It is now a
  plain model method that `build_demo.sh` calls once the install has finished.
  Everything still lives in the module.
- `_provision_demo_tenant(..., adopt_existing=False)` gained an **explicit
  flag**, never a heuristic: `data/` calls `_provision_demo_tenant_on_install`,
  which passes `adopt_existing=True` out loud; the tests pass nothing and get
  the create path. Adoption is only taken when the candidate company has no
  foreign chart — Odoo cannot switch charts afterwards, and a demo silently on
  `generic_coa` is wrong in a way that stays invisible until an accountant
  looks. Where adoption cannot be honoured (a database built WITH Odoo demo
  data, e.g. the CI job) it logs a WARNING and creates a separate company
  instead of failing the install.
- **`scripts/build_demo.sh <db> [demo_module]`** is the single documented
  command. Three phases — base-only DB, set country Ethiopia, install the demo
  module with `--without-demo=all` — because with demo off the base company is
  created on `generic_coa` with country US, and the chart cannot be changed
  later. That is the same dance `provision_client.sh` does for a real client,
  so **recording the demo is a rehearsal of the actual deployment**. The demo
  module is an argument, so a pharma pitch is one flag away.
- **The guard we gave up is replaced, not dropped**: `demo/` was what stopped
  this module fabricating a company on a client's books.
  **`scripts/check_no_demo_modules.sh <db>`** fails, naming offenders, if any
  demo module is installed; `provision_client.sh` now runs it as an acceptance
  assertion. NOTE: the rest of the provisioning acceptance check (chart is
  'et', ETB, TIN set, backups scheduled, admin_passwd set) is **outstanding**.

**2. The catalogue is building materials, in the units of the trade.** Ten
products: three cements (bag), three rebars + binding wire (kg), corrugated
sheet and HCB (piece), sand (m³), plus two services for the withholding paths.
Customers are contractors and hardware retailers; suppliers keep the three
compliance profiles, including the **no-TIN supplier** the 30% demonstration
needs.

- **The unit pair**: cement is bought by the **quintal** and sold by the
  **bag**, 1 quintal = 2 bags of 50 kg. Odoo 19 removed UoM *categories* and
  `uom_po_id` — units now form a tree via `relative_uom_id`/`relative_factor`
  and a product offers extra units through `uom_ids` — so that is how it is
  built. Proven: the July purchase of **30 quintals shows 60 bags on hand**.
  Cement has no opening stock, so that 60 is the conversion and nothing else.
- Every price is in ONE marked block,
  `addons/sapian_demo_trader/models/demo_catalogue.py`, tagged `[RANGE]`,
  `[DERIVED]` or **`[UNVERIFIED]`**. The unverified ones are placeholders
  nobody has checked — set them before recording.
- The month's numbers are unchanged, because the demo's value is that it is a
  real month: VAT 56,000/8,400, WHT 1,560 + 4,500 + 1,200 = 7,260, payroll
  23,800/3,900/18,374. Opening stock was added for the sold lines so nothing
  shows negative on camera.
- Tests updated for the intended renames (`Awash` → `Derba Midroc Cement
  Depot`, `Habesha` → `Yonas Transport`) plus a new UoM-conversion test.
  Trader coverage 12 → 16 tests; suite 166 → 167, 0 failed.
- `docs/11-demo-video-kit.md` is new (no video kit existed); README's demo
  section now documents the one command.

**`sapian_demo_pharma` has the same `demo/` pattern and is deliberately
deferred** — out of scope this session. It is not converted, so
`build_demo.sh demo_pharma sapian_demo_pharma` will not yet produce a
one-company pharma tenant.

### Windows ops toolchain unblocked; post-condition ordering ✅ (2026-08-09)

**1. `MSYS2_ARG_CONV_EXCL='*'` blocked every compose call on Windows
(REGRESSION — backups were down).** The blanket exclusion was added (2026-07-07)
so CONTAINER paths like `/var/lib/odoo/filestore` reached docker unconverted.
It also stopped the HOST path passed to `docker compose -f` from being
converted, so Git Bash handed docker `/c/Users/...`, which docker resolved
against the current drive as `C:\c\Users\...` → "The system cannot find the
path specified". `backup.sh`, `restore.sh` and `dress_rehearsal.sh` all
carried it; `provision_client.sh` did not, which is why provisioning still
worked and is the clearest evidence that the exclusion — not the absolute
`-f` — was the fault.

- The exclusion is now **scoped** to `/var/lib/odoo`, and `MSYS_NO_PATHCONV=1`
  (also blanket) is gone. Container paths stay unconverted; host paths convert.
- The `-f` host path additionally goes through **`compose_cmd`** (new, in
  `scripts/lib/preflight.sh`), which runs `cygpath -m` when available so the
  path does not depend on MSYS heuristics — those differ between
  Git-for-Windows releases, and this one argument takes the whole toolchain
  down when it is wrong. No-op off Windows. Absolute `-f` is kept, so the
  scripts stay runnable from any cwd (cron/Task Scheduler).
- Applied to all four scripts. `check_backup_freshness.sh` never invokes
  docker, so it was unaffected.

**The error was also being hidden.** `require_docker_stack` ran the service
probe with `2>/dev/null`, so a compose failure surfaced as the misleading
"Compose service 'db' is not running" while the real message was discarded.
Both probes now REPORT their stderr and name the command that failed; the
daemon probe uses `docker info --format '{{.ServerVersion}}'` with a
stderr-only capture, because plain `docker info` prints pages of client output
even when the daemon is down. Suppressing the stream that carries the reason is
the same disease as the silent backups.

**On why the scheduled backups succeeded 7/27–8/9 with this construction:** the
absolute `-f` landed 2026-07-26 (`2caa40b`), *before* every one of those
successful runs, and the blanket exclusion predates it (2026-07-07) — so the
code was identical during the successes and during the failure. Nothing in
compose treats `-f` differently per subcommand, so this is not `ps` vs `exec`.
That leaves an environment change (a Docker Desktop / compose update altering
path handling) or a deployed copy that lagged the repo. **This session could not
settle which** — see the platform-verification note below.

**2. Post-condition logging order.** The migration always ran
bands → pension → post-condition, but the band summary line was emitted at the
end of `migrate()`, so the log read as though the assertion ran before the
correction it asserts on. Each step now logs its own summary and the
post-condition is called — and logged — last. A test spies the call order and
asserts the final log record is the post-condition.

**3. Process rule added to CLAUDE.md:** a fix for a platform-specific failure is
not verified until it is verified on that platform; if the platform is not
available in the session, the item is reported **UNVERIFIED** rather than
backed by Linux evidence. Written because item 2 of the previous session was a
Windows-only failure verified entirely on Linux, and shipped broken.

### Two silent failures, both made loud ✅ (2026-08-09)
Both found on a live machine, not by reading code. Same disease: a failure that
produced no signal.

**1. The PAYE migration could not see archived companies.** `19.0.4.0.0`
iterated `res.company.search([("active", "=", True)])`, so an archived company
was never examined — not corrected, and, because the skip-and-warn branch lived
inside that loop, not warned about either. On `scratch_final` the placeholder
company archived during demo provisioning kept bands dated 2024-07-01 while the
migration logged success and said nothing. Reproduced on a scratch database:
an archived company with legacy rows was left untouched with **zero** log
output, while an otherwise identical active company was corrected.

- **`19.0.5.0.0`** re-audits from the ROWS, not from a filtered company list,
  so a misdated row is found regardless of the company's active flag — and an
  exactly-shipped row set is **corrected** whether its company is archived or
  not (it is equally safe either way). Skip-and-warn now means only "these
  bands are customised and I will not touch them", never "I could not see this
  company". Shipped as a new version so databases already upgraded to
  `19.0.4.0.0` get re-checked.
- **Post-condition**: after correcting, the migration asserts that no band or
  pension row *anywhere* still carries the superseded date, and lists whatever
  does (company, count, date) at WARNING level. It reports rather than raises —
  a customised row is a legitimate leftover for a human to decide about, and
  failing the upgrade would strand the database — but it is never silent.
- **The seeder keeps its active-only scope, and stops lying about it**:
  `_l10n_et_seed_all_companies` → `_l10n_et_seed_active_companies` (PAYE bands,
  pension config, allowance types) with docstrings explaining why. Archived
  companies run no payroll, and if one is unarchived the missing configuration
  RAISES (A1) rather than falling back to constants. That covers "rows exist";
  "rows that exist are right" is the separate invariant the post-condition
  enforces across every company. This also explains the observed asymmetry —
  a company archived *after* install has bands, one archived *before* has none.

**2. `scripts/backup.sh` produced seven 0-byte backups over two weeks.** Docker
Desktop was not running; the dump failed, but `>` had already created the
destination file, and the cleanup that would have removed it never ran. The
guard itself is correct — verified on Linux, with the daemon unreachable and
with the `db` service stopped it exits 1, prints `!!` and leaves nothing. Docker
writes its connect error to **stderr**, the same stream as `!!`, so its absence
from the operator's log means the echo never executed rather than being
filtered; the log's `dofork: child -1 … 0xC000026B` (MSYS2 fork failure) is the
probable trigger. Killing the script mid-run reproduces the exact artefact:
valid-looking timestamped files, no error line. The lesson is structural —
cleanup-after-failure cannot be relied on, because cleanup is precisely what
does not happen when a process dies.

- **A file bearing a backup's real name now only comes into existence after
  the backup is complete and verified**: work goes to `<name>.tmp`, is size- and
  `pg_restore --list`-checked (and the filestore `tar tzf`-checked), then `mv`d
  into place. An `EXIT` trap removes temp files; even a killed shell leaves only
  `.tmp`.
- **Preconditions** (new `scripts/lib/preflight.sh`): the Docker daemon must
  answer and the `db` service must be running before any artefact is created.
  Used by `backup.sh` and by **`restore.sh`**, where it matters more — a restore
  happens under pressure, and discovering the daemon is down *after* odoo is
  stopped and the database dropped is the worst possible moment.
- **`<backup_dir>/LAST_BACKUP_STATUS`** records timestamp, database, outcome and
  the failure reason on every run; the script exits non-zero, so Task
  Scheduler's "Last Run Result" is a usable alarm.
- **`scripts/check_backup_freshness.sh <db> <dir> [hours]`** (default 48) exits
  non-zero when the newest verified backup is too old, missing, empty, or the
  last run reported FAILED.
- **Every log line is timestamped** — diagnosing the original fortnight of
  failures needed guesswork against file mtimes.
- Runbook section added to `docker/README.md`. `shellcheck -x` clean across
  `scripts/`; the one suppression (SC2016 in restore.sh) is justified inline.

**TODO, not this session**: `scripts/provision_client.sh` appends `admin_passwd`
with `>>`, so re-running it would leave two `admin_passwd` lines in the runtime
conf. Not dangerous (Odoo takes one), but it should write idempotently.

### PAYE bands: right dates, both generations ✅ (2026-08-09)
A tax-computation defect, not a UI issue. **No band value changed** — what was
wrong is the date the values were said to take effect, and the absence of the
regime that preceded them.

The bands we ship (0/15/20/25/30/35%, exempt to 2,000, top above 14,000) are
those of **Income Tax (Amendment) Proclamation No. 1395/2025, in force 8 July
2025**. They were seeded as effective **2024-07-01** — twelve months before the
proclamation existed. Consequences:

1. every payslip dated 2024-07-01 → 2025-07-07 computed PAYE on bands more
   generous than the law of the day, so tax was **UNDERSTATED** — the
   employer's liability at assessment. Worked example, hand-checked: gross
   6,000 → under 979/2016 it sits in 5,251–7,800 (25%, deduction 565) = **935**;
   under 1395/2025 it sits in 4,001–7,000 (20%, deduction 500) = **700**. A
   June-2025 payslip on a real database stored 700.
2. the preceding regime, **Proclamation No. 979/2016**, had no records at all,
   leaving the table unable to answer "what was the tax in May 2025?" — one
   rate set with a date column, not an effective-dated table.

Both are live concerns: migrating a year of historical payroll, a back-pay
correction and reissuing last year's payslip are all first-month tasks.

- **Reference calculator** carries both generations — `PAYE_BANDS_979_2016`,
  `PAYE_BANDS_1395_2025`, `PAYE_BAND_GENERATIONS` (commencement + citation per
  schedule) and `get_paye_bands(on_date)`, commencement inclusive. Still pure
  Python, no Odoo import. `DEFAULT_PAYE_BANDS` still means "in force now".
- **Seeder** writes every generation per company, each closed the day before
  the next commences.
- **Pension commencement corrected too**, and for a subtler reason than PAYE.
  The rates (7%/11%) are unchanged across the transition so nothing computes
  differently — but Proc 715/2011 **art. 57 phases** contributions from
  commencement on 8 July 2011 (employee 5/6/7%, employer 7/8/9/11%), so 7% and
  11% first coincide in **year four, 8 July 2014**. Seeding 2011-07-01 asserted
  a rate that did not apply for three years and predated commencement by a
  week; the seed is now `2014-07-08`. The 2011–2014 transitional generations
  are deliberately NOT modelled — they fall outside the supported range, and
  half-modelling them would assert rate history we have not verified.
- **Citations** beside each constant, with `TODO: confirm against gazette` on
  the 979/2016 commencement (secondary sources only: EY/Chambers/KPMG on
  1395/2025, the standard published 979/2016 schedule). The boundary that
  matters and is well-supported is 8 July 2025.
- `data/paye_band_data.xml` said "the 2024/25 reform". It is the **2025**
  reform; corrected so the next reader does not inherit the wrong model.
- **Migration `19.0.4.0.0`** for databases already in use. It corrects
  `effective_from` **only** where the company's bands are its entire set, match
  the shipped 1395/2025 signature exactly and carry no closing date; seeds the
  979/2016 generation for those; and applies the same discipline to the pension
  row (so upgraded databases cannot silently keep 2024-07-01 while fresh
  installs get the new date — that divergence is how this defect survived).
  Customised configuration is skipped whole and **named in a warning**.
  It **reports** every pre-boundary payslip whose PAYE would now differ
  (employee, period, old, new, delta) and **changes none of them** — posted
  payroll is not something a migration rewrites on its own authority. The
  report is persisted to `<data_dir>/l10n_et_payroll/` **and** as an
  `ir.attachment`, with both locations logged, because a log line scrolls past
  and is gone. The file name is scoped to the **database and the run time**
  (`paye_band_correction_<dbname>_<YYYYMMDDHHMMSS>.txt`): only `filestore/` is
  per-database — the rest of `data_dir` is shared by every database on the
  instance — so a name without the dbname meant upgrading the second tenant
  silently destroyed the first tenant's report, and a name built from the
  boundary constant collided with repeated runs on one database. Same-second
  runs get a numeric suffix; the attachment carries the name the file got.

Verified on a database seeded the old way, carrying one exactly-shipped company
and one with a deliberately customised deduction: matched company corrected to
2025-07-08 + 979 generation seeded (7 rows, closed 2025-07-07); customised
company untouched at 2024-07-01, deduction still 555, **no** 979 rows, named in
the warning; both pension rows corrected to 2014-07-08; payslips still 700.00,
unrewritten; report attachment persisted. Second forced run: identical row
counts, no duplicates. Goldens written FIRST and watched fail — 17 fast tests
plus 6 Odoo tests covering June-2025 → 979, August-2025 → 1395, and both sides
of the 8 July 2025 boundary.

### Ethiopian tax engines fail LOUD, not open ✅ (2026-07-26)
The WHT and cash-cap configurations were seeded **only** when chart 'et'
loaded (`template_et._post_load_data`), and both engines read "no
configuration" as "do nothing". A group's second company, or a tenant
provisioned any other way, therefore posted vendor bills with **no
withholding** and cash payments with **no cap check** — no error, no warning.
Structurally the same defect as audit finding A1 (payroll), but failing open
instead of loud. Same treatment applied:

- **Seeded per company on `res.company.create`** (`l10n_et_base/models/
  res_company.py`), plus a data-file `<function>` on install/upgrade and a
  `19.0.1.2.0` post-migration for databases that already exist. Every company
  now owns real, effective-dated records.
- **Scope is explicit**: new `res.company.l10n_et_tax_engine_active`, defaulted
  from the company country (ET) and editable. It is *computed* rather than a
  create-time default because provisioning creates the company first and sets
  the country afterwards (the onboarding wizard, `provision_client.sh`) — a
  plain default would leave every wizard-provisioned tenant out of scope. One
  flag governs **both** engines so they cannot drift apart.
- **Three outcomes replace the silent empty recordset** (`_l10n_et_resolve_config`
  on both config models):
  - out of scope → inert, silently and correctly (a foreign subsidiary sharing
    the database keeps posting bills and payments normally);
  - in scope, no configuration at all → **raises**, naming the company and
    where to configure it. That is the compliance hole;
  - in scope, but the document predates the earliest configuration → the
    withholding/cap check is **skipped with a chatter note** naming the
    earliest configured date. Deliberately not an error: importing historical
    vendor bills whose withholding was computed and remitted years before this
    engine existed is normal delivery work, and a hard block would make data
    migration impossible for every client with pre-Aug-2025 history. The skip
    is auditable in the same channel as the WHT audit trail.
- The "no Ethiopian withholding tax record found" error now offers the third
  exit as well — turn the engine off for a company with no Ethiopian fiscal
  setup — alongside setting the tax or reloading the chart.
- **Tena Pharma** (`sapian_demo_pharma`) ships with the flag **off**: it is
  provisioned without a chart of accounts, so the engine would have no ET taxes
  to resolve and would raise on the first vendor bill posted during a pitch.
  That is a statement about missing fiscal setup, not about Tena's tax
  obligations. **Follow-up (not built here):** give Tena the 'et' chart — it is
  an importer whose pitch includes a 2,511,500 ETB landed-cost dossier, so a
  prospect asking "where does that hit my books?" currently has nowhere to look.
- Regression suite `l10n_et_base/tests/test_tax_engine_scope.py` (12 tests):
  second-company withholding (golden 1,500 on 50,000), second-company cash cap,
  non-Ethiopian company stays inert, both raise branches, both backdated
  branches, country-set-after-creation, and the upgrade seeding path. **8 of 10
  discriminating tests fail on the pre-fix code**; two (`withholds_on_goods_bill`,
  `enforces_cash_cap`) pass before and after because loading chart 'et' already
  seeded configs on the old path — they pin the end state rather than the bug.

### Catalog/dependency invariant machine-checked ✅ (2026-07-26)
`sapian_demo_trader`'s manifest comment ("every catalog app must also be a
dependency") is now a test: `test_catalog_dependencies` asserts the
STANDARD_CATALOG module names are a subset of the module's transitive manifest
dependencies. That is the real recurrence guard for the demo-provisioning
break; the `_install_modules` warning only makes a violation graceful.
`test_company_onboarded_via_wizard` no longer asserts `enabled == catalog`
(true by construction): it compares the enabled entries against the modules
genuinely installed, so it can again catch "the wizard failed to enable a pick".

### PAYE bands + pension configuration reachable in the UI ✅ (2026-07-26, B7)
`l10n.et.paye.band` and `l10n.et.pension.config` had ACLs, record rules and
seeders but no menu, action or views — and the payslip error message pointed at
"Payroll › Configuration › PAYE Bands", which did not exist. When a rate changed
at a client, nobody could edit it. Added list+form views and actions for both,
an action+menu for `l10n.et.payslip` (views existed, unreachable), and a
Configuration submenu under Ethiopian Payroll (allowance types moved there too).
ACLs unchanged; the error messages now name the menus that exist.

### Deployment postgres pinned by digest ✅ (2026-07-26)
`docker/docker-compose.yml` pinned `postgres:16` to the same digest `ci.yml`
uses — the deployment stack was the one still drifting.

### Demo provisioning fixed + images pinned by digest ✅ (2026-07-26)
`-i sapian_demo_trader --with-demo` on a fresh database — the documented
rebuild one-liner — had started failing, and the trader suite was silently
running 2 of its 12 tests in CI (the e2e goldens never ran, because their
demo tenant never loaded).

**Root cause — two ingredients, neither sufficient alone.** The catalog
expansion in `66c21cc` (7 → 15 apps) opened a dormant code path: the demo
hands the onboarding wizard the FULL catalog, and with eight of those apps
absent from `sapian_demo_trader`'s manifest the wizard's `_install_modules`
found pending modules and called `button_immediate_install` — during demo
data loading. That path was harmless on the `odoo:19.0` image of 9 July (CI
was green on this exact addons code). A later upstream rebuild of the same
unpinned `19.0` tag tightened the guards in
`ir_module._button_immediate_function`, and the previously dormant call
became fatal: `RuntimeError: Module operations inside tests are not
transactional and thus forbidden` under `--test-enable` in CI, and
`UserError: ... cannot be called on init or non loaded registries` on a
plain install. So: dormant path opened by `66c21cc`, armed by an
`odoo:19.0` rebuild.

- **Fixed at the demo end** (real onboarding is unchanged — a client
  onboarding SHOULD install modules): the eight standard Community apps the
  catalog offers (`crm`, `mrp`, `project`, `mass_mailing`, `fleet`, `repair`,
  `maintenance`, `website_sale`) are now `sapian_demo_trader` dependencies,
  so they are installed before demo data runs and the wizard's install step
  is a no-op. The demo's pick list is unchanged — Selam still shows all 15
  catalog entries.
- **Recurrence made impossible:** `sapian_core`'s `_install_modules` now
  skips the install with a logged warning naming the skipped modules when
  the registry cannot support a module operation (not ready, still
  initialising, or in test mode — the same conditions core checks). Neither
  holds during real onboarding, so runtime behaviour is identical; a future
  catalog addition that forgets the manifest degrades with a clear warning
  instead of an opaque core error.
- **Collateral, also fixed:** with `website_sale` installed, archiving the
  Odoo placeholder company is refused while it owns the demo website, so
  `_configure_demo_login` reassigns any placeholder-owned website to the demo
  company first.
- **Images pinned by digest (R7):** `ci.yml` (odoo + postgres) and
  `docker/Dockerfile` pin the digests currently published for `odoo:19.0`
  and `postgres:16` — verified against Docker Hub's registry API — instead of
  floating tags. This is what let the fleet drift silently; upgrading an
  image is now a deliberate, tested change (bump the digest in its own PR).
- Verified: the README one-liner completes on a genuinely fresh database in
  a single pass (no pre-install workaround) with demo data loaded — Selam
  provisioned with logo, 6 posted moves, 3 payslips, 15 catalog entries,
  placeholders archived, and zero install-skip warnings (the deps cover
  every pick). Fast goldens 90/90; ruff/black clean.
- Existing `sapian_core` onboarding tests do NOT exercise `_install_modules`
  with modules actually pending — they assert catalog pre-selection and
  profile/branding only, which is why this path was never covered. Noted,
  not built this session.

### Ops hardening — backup/restore drilled end-to-end ✅ (2026-07-26)
Ops-layer-only session (no addons changes): the backup/restore path is now
drilled, not just written. All seven fixes verified by a real restore drill.
- `restore.sh`: the filestore phase used to `compose exec` into the odoo
  container the script had just STOPPED — impossible, and with `set -e` the
  abort landed after the DB was dropped/restored but before odoo restarted
  (tenant DB-only, filestore missing, Odoo down). Filestore now restores via
  throwaway `compose run --rm --no-deps` containers on the same `odoo-data`
  volume; all input validation happens before anything destructive; on any
  failure odoo deliberately stays STOPPED with an explicit known-state
  message (a half-restored tenant must never serve traffic). Also: the
  archive's top-level dir is renamed on extraction (`tar --transform`) so
  restoring under a different db name still gets its filestore.
- `provision_client.sh`: the generated `admin_passwd` was appended to the
  git-tracked `config/odoo.conf` (one `git add -A` away from committing a
  tenant master password, and compose mounted the same tracked file). Secrets
  now go to gitignored `config/odoo.runtime.conf` — created from the template
  if missing — which is what `docker-compose.yml` mounts; the tracked
  template stays clean (`git status` verified clean across a provision run).
  Deploy step documented in `docker/README.md`.
- `backup.sh`: `pg_dump` gets the same fail-guard + partial-file cleanup the
  filestore path already had (A9); every dump is verified restorable with
  `pg_restore --list` before success is reported; retention pruning matches
  the exact database (`NAME_[0-9]*`), so backing up `sapian` can no longer
  delete `sapian_prod_*` archives (regression-tested with aged files).
- `.env` location fixed everywhere: compose's project directory is `docker/`
  (it is invoked `-f docker/docker-compose.yml`), so the documented repo-root
  `.env` was never read and `${DB_PASSWORD:?}` aborted all scripts. The file
  now lives at `docker/.env`; CLAUDE.md, README.md and docker/README.md
  corrected.
- `dress_rehearsal.sh`: drops its target DB only after a typed-name
  confirmation (same guard as restore.sh), and exits non-zero when the
  reconciliation exam fails (`EXAM_VERDICT` sentinel — odoo shell always
  exits 0), so it can gate a release unattended.
- All four scripts resolve the repo root from their own location
  (`BASH_SOURCE`), so cron/Task Scheduler invocations work from any cwd, and
  all are executable (mode 100755) on a fresh clone.
- Restore drill (this session, containerized Odoo 19): `backup.sh` on the
  Selam demo tenant (dump passed `pg_restore --list`, filestore 2,372 files)
  → `restore.sh` onto `scratch_restore_drill` → on the restored DB all
  July-2026 goldens hold (VAT base 56,000 / output VAT 8,400; WHT 7,260;
  payroll gross 23,800 / PAYE 3,900 / net 18,374), the company logo reads
  back from the restored filestore and a payslip PDF renders. Fast goldens
  90/90 before and after.
- Review follow-ups (same session, second pass): `backup.sh`'s filestore leg
  now uses the same throwaway-container pattern as restore.sh, so a backup
  succeeds with the odoo service stopped or crashed (drilled: full backup
  taken with odoo down, dump `pg_restore --list`-verified, archive file count
  == live filestore). `restore.sh` validates the filestore archive with a
  full `tar tzf` listing in pre-flight and extracts into a temp dir, swapping
  it in only after a fully successful extraction — a truncated archive is
  rejected before anything is dropped (drilled: truncated .tgz rejected with
  the target filestore and DB intact, then a clean end-to-end restore). All
  four scripts pre-flight `config/odoo.runtime.conf`: created from the
  template when missing, clear abort when docker has created the path as a
  directory on a fresh clone.
- Demo-provisioning break found while drilling — root-caused and fixed in the
  next entry below. (An earlier draft of this entry blamed `66c21cc` alone;
  that attribution was wrong — see below.)

### Onboarding catalog — offer the standard Odoo Community apps ✅ (2026-07-09)
`sapian.module.catalog` STANDARD_CATALOG grows from 7 to 15 entries. Added the
stock Odoo 19 Community apps that had no Ethiopian layer and were previously
reachable only via the raw Apps menu, as `optional`-tier entries: CRM (`crm`),
Manufacturing (`mrp`), Project (`project`), Email Marketing (`mass_mailing`),
Fleet (`fleet`), Repair (`repair`), Maintenance (`maintenance`), and
Website & eCommerce (`website_sale`). Tier drives pre-selection, so the
onboarding wizard still pre-ticks only the `core` tier — the optional apps are
offered but never auto-installed. No new Ethiopian customization for these yet.
Catalog-count tests updated 7 → 15.

### Ops scripts — Windows-safe backup, restore, et-chart provisioning ✅ (2026-07-07)
Two commits (`51f3456`, `85d5f05`) hardening the operations layer:
- `backup.sh`: disable Git Bash MSYS path conversion (it mangled the
  container-absolute filestore path on Windows and aborted the backup; no-op on
  Linux/CI). New optional `[offsite_dir]` + `[retention_days]` args: after a
  successful DB+filestore backup, both archives are copied to a synced folder
  (e.g. OneDrive) for an off-site copy, with retention pruning in both
  locations; off-site failure aborts loudly (A9). Machine-specific paths stay
  out of the repo (local Task Scheduler `.cmd` wrapper).
- `restore.sh`: new companion script — drops/recreates the DB from a `pg_dump`
  and restores the filestore, with a typed confirmation guard.
- `provision_client.sh`: two-phase provisioning (base → set company country →
  install modules) so new tenants land on the Ethiopian 'et' chart instead of
  `generic_coa`, which Odoo won't let you switch afterwards.
- `backups/.gitignore`: never commit tenant data dumps.

### Dress rehearsal — full-month simulation + independent exam ✅ (2026-07-07)
New `sapian_dress_rehearsal` module: a rerunnable pre-release ritual that
provisions a fresh tenant through the onboarding wizard, drives one realistic
month (August 2026) of business through the REAL flows, then proves the books
with an exam that recomputes every figure by a path independent of what it
checks.
- The month: 25 sales orders (3 partial deliveries → backorders, 1 return +
  credit note; invoiced on ordered qty so VAT is decoupled from delivery),
  12 purchases (10 goods POs feeding stock, mix above/below the 20,000 WHT
  threshold; 2 direct service bills — no-TIN domestic 30%, foreign digital
  15%), a 5-employee payroll run (incl. a transport allowance capped at 25%
  of 6,000 = 1,500 and a pension-exempt foreigner), several bank payments +
  one vendor CASH payment near the 50,000 cap, and one inventory adjustment.
- The exam (all green): trial balance (48 balanced moves, debits==credits
  2,814,155), VAT (15% × 397,000 base = output 59,550; input 186,090; ties to
  GL), WHT (per-bill recompute 34,950 @3% + 3,000 @15% + 12,000 @30% = 49,950;
  ties to WHT-payable GL), payroll (5 payslips recomputed from CONFIG-sourced
  bands/rates — PAYE 11,650, pension EE 2,905), stock (on-hand per product =
  received − delivered ± adjustment vs quant, incl. the −5 Teff shrinkage).
- 3 role walkthroughs over HTTP (HttpCase): warehouse receive, accountant
  bill-with-WHT (3% auto-applied), HR payroll confirm.
- `scripts/dress_rehearsal.sh` rebuilds `scratch_rehearsal` from empty, runs
  the month and prints the reconciliation table; the tenant is kept for
  manual click-through. 6 Odoo tests (TransactionCase + HttpCase); lint 10.00.

### Defensive-audit fixes — A1–A10 (2026-07-06)
Second, independent defensive audit (single-context, evidence-per-finding) over all six
modules + docker/config/scripts/CI. All confirmed findings fixed with regression tests;
A8 deferred to the deployment runbook. Findings table in HANDOFF.md.

- **A1 (high) — per-company PAYE/pension config.** PAYE bands + pension config used to be
  seeded (via XML `<record>`s) only for the company active at module install; every other
  company (a group's 2nd company, the demo tenants, a SaaS tenant) silently fell back to
  hard-coded rate constants in the compute helper. Now seeded PER COMPANY from the reference
  calculator — install `<function>`, `res.company.create` hook, and a pre-migration that
  detaches the legacy xmlid records so existing DBs keep them while every other company is
  filled in. The silent `DEFAULT_PAYE_BANDS`/`0.07`/`0.11` fallback is REMOVED: a company
  with no applicable config now raises a clear `UserError` naming the company and date.
  Regression tests prove new companies are seeded, missing config raises, and the 10,000
  golden (1,650/700/7,650) comes from the records (editing a band moves PAYE).
- **A2+A5 (medium) — pharma expiry digest.** The single `pharma_alerted` boolean meant a
  batch was digested once ever (no re-alert when it crossed nearing→expired) and shared,
  company-less lots were de-duplicated across all companies. Replaced with a
  `pharma.expiry.alert` model keyed (lot, company, state): re-alerts on state transition,
  per company. Digest takes an injectable `today` for testing. Test: a batch alerted while
  nearing gets a second digest entry when it later expires.
- **A3 — CI runs the Odoo integration suite.** New GitHub Actions job (odoo:19.0 container +
  postgres service) installs the demo tenants with demo data and runs the full
  `--test-enable` suite; CI is red on any test failure.
- **A4 (low) — VAT declaration no longer raises on read.** An off-chart company made the
  non-stored totals compute raise `UserError`, breaking list/form views. It now returns zero
  totals with an `off_chart` warning state surfaced as a form banner.
- **A6 (low) — cash-cap concurrency.** The daily-cap check was a TOCTOU fail-open under
  concurrent posts. Added a transaction advisory lock keyed on (company, party, day) so
  concurrent posts to the same party serialize; documented in the model.
- **A7 (low) — import-dossier least privilege.** Landed-cost financials were writable by any
  warehouse user. Warehouse users are now read-only; write/create is limited to purchase
  managers, full access to account managers (vertical_pharma now depends on purchase+account).
- **A9 (low) — backup.sh** exits non-zero and removes the partial archive if the filestore
  backup fails (no more silent "Backup written" on partial success).
- **A10 (low) — provision_client.sh** generates a strong per-tenant `admin_passwd`, writes it
  into the runtime `odoo.conf`, and prints it once for the vault (idempotent).
- **A8 (low, deferred)** — `proxy_mode=True` with the dev compose publishing 8069 directly and
  no TLS. Documented in `docker/README.md` as a go-live runbook step (nginx/TLS reverse proxy);
  no code change.

### Pre-release hardening — accountant corrections + adversarial review ✅ (2026-07-06)
Two phases; the exception to the no-multi-agent rule (final pre-release pass).

**Phase 1 — accountant-verified config corrections (Jul 2026 review):**
- Cash cap 30,000 → **50,000 ETB** (Art. 81, Proc 1395/2025, cross-verified vs KPMG's
  proclamation copy). Semantics: single transaction OR same-day aggregate per party,
  whichever hits first — the aggregate check covers the single-transaction case. Goldens
  updated; an upgrade hook corrects DBs still on the old 30k default (customized caps
  untouched); warning text reworded.
- **Allowance exemption engine** (`l10n.et.allowance.type`, seeded per company with source
  notes): transport exempt up to the LOWER of 2,200/month or 25% of basic (excess taxable,
  computed — golden salary 10,000 + transport 3,000 → exempt 2,200, taxable 800, PAYE 1,890);
  hardship + actual-cost medical exempt; housing + position taxable. Payslip input lines link
  to a type; the rule computes the split. Per-diem documented as an evidence-based input line.
- **Pension nationality rules**: mandatory for Ethiopian nationals, voluntary for foreign
  nationals of Ethiopian origin (opt-in flag on the employee), excluded for other foreigners.
- WHT defaults confirmed (either TIN or licence missing → 30%; thresholds gate all WHT);
  anti-avoidance note added to the reports README. Docs (plan-2026/07, CLAUDE.md tax-facts,
  HANDOFF) updated with VAT carry-forward default, Reg 570/2025 EFD+QR mandate, filing
  channels and MoR beneficiary accounts.

**Phase 2 — 3-reviewer adversarial pass (R1 calc, R2 security, R3 state-machine) over all
five modules; every finding confirmed by executed input or refuted; 18 fixed with regression
tests, 1 deferred (fail-safe). Full findings table in HANDOFF.md.** Highlights:
- critical: allowance-ceiling edit rewrote confirmed payslips (now frozen); each transport
  line got its own monthly ceiling → double exemption (now summed per type); confirmed
  run/payslip deletable → orphaned journal (ondelete guards).
- major: cash cap blind to same-batch siblings; HR Officer read wages/bank/TIN via the payslip
  (ACLs restricted to HR manager); no PAYE-band/pension overlap guard; un-flagging is_pharma or
  clearing a lot's expiry escaped the expiry gates (constraints added).
- minor: allowance half-cent rounding; payroll rounder aligned to Decimal half-up; pharma
  expiry UTC/local off-by-one; multi-company rules on paye.band/pension.config/module.catalog;
  CSV formula-injection neutralizer on all exports; digest re-arm on expiry relabel; bank file
  cleared on reset; reset blocked on a reconciled move; `list_db=False` default.
- deferred (fail-safe): recall report doesn't net customer returns (over-reports; a recall must
  contact everyone) — pharma session 2.
- Demo-data bugs fixed: sales invoices now ETB (were USD default pricelist); invoice due date
  no longer precedes the issue date; physical demo goods are storable. Asserted in e2e tests.
- Result: 90 fast goldens + 133 Odoo tests green; install/uninstall clean; lint 10.00; the
  live demo DB (`scratch_final`) upgraded in place (cash cap corrected, allowance types seeded).

### Pharma vertical, session 1 — vertical_pharma + sapian_demo_pharma ✅ (2026-07-05)
The DAT International pitch module (docs/plan-2026/07 §8, 05; behavior per the
client's own requirements in docs/01-proposal-extraction.md §8.1).
- **vertical_pharma** (13 Odoo tests incl. an HttpCase web-dispatch test; 12 new
  fast goldens → 79 total):
  - Batch discipline: `is_pharma` flag forces lot tracking + expiry + the FEFO
    "Pharmaceuticals" category (constraint-guarded); receipts without an
    expiration date on a pharma batch cannot validate.
  - Expiry engine (`reference/pharma_calc.py`): fresh → nearing expiry →
    expired against a per-company horizon (default 90 days; golden: expiry
    2026-09-25 alerts FROM 2026-06-27, not before; expiry date = last usable
    day). Daily cron posts ONE digest activity per company (anchored on the
    most urgent batch, assigned to a stock manager), each batch reported once.
  - Expired-lot delivery policy per company: block (default, UserError with
    batch details — verified through web RPC dispatch) or warn + audit note.
  - GS1 DataMatrix capture on receipt lines: AIs 01/17/10/21, day-00 = month
    end, serials parsed not persisted (v1); mis-scans warn and fill nothing.
  - Import shipment dossiers (`IMP/...` sequence): supplier, ETA, status,
    clearance notes + chatter docs, landed-cost fields with computed total;
    linked to receipts, batches derived; menu under Inventory; multi-company
    record rule + stock-group ACLs.
  - Batch recall report (button on the lot, `web.external_layout`): every done
    customer delivery of the batch with date, quantity and the customer's
    PHONE + CITY (a recall means calling people); import-dossier traceability
    printed; golden: B-123 → exactly two customers with different dates/
    quantities, third customer excluded (received B-124 only).
  - EFDA traceability export: deliberately a stub pending official specs.
- **sapian_demo_pharma** (7 Odoo tests): "Tena Pharma Import PLC" — six
  medicines (Amharic+English, realistic 730-day shelf lives so a live pitch
  receive can't create an instantly-expired lot), batches at all three expiry
  stages, digest PRE-FIRED (the pitch shows the alert, not a description),
  dossier IMP/2026/0001 landed-cost golden 2,511,500 ETB, and the recall-ready
  flow (Hiwot 120 + Kadisco 80 exhaust B-123 so Bethel's 60 FEFO-reserves
  B-124). Installed on `scratch_final` alongside Selam.
- Odoo 19 gotchas learned (tests now encode them): product_expiry AUTO-FILLS
  missing expiry from `product.expiration_time`; expired quants are
  unreservable (forcing a lot on a manual move line is the only path our
  delivery gate must catch); receipt-created lots carry NO company_id unless
  the product does; `res.groups.users` → `all_user_ids`; stock.warehouse has
  no activity mixin; HttpCase needs `--workers=0` (odoo.conf ships workers=2);
  Git Bash mangles `--test-tags /module` (use MSYS_NO_PATHCONV=1).

### Project skill — Fable 5 prompting guide ✅ (2026-07-04)
`.claude/skills/fable5-prompting/SKILL.md` (`ad9cf37`): a project skill for
drafting/reviewing kickoff prompts, system prompts and agent instructions
tuned to Claude Fable 5 — token-conscious session design for this repo's
Claude Code workflow. Tooling only; no product code.

### Cleanup — demo polish, catalog truth, CI, samples ✅ (2026-07-04)
- Demo login: provisioning archives ALL Odoo placeholder companies (incl. the
  original main company) and points admin (and every stranded user) at the real
  companies — a fresh login on the demo DB lands in Selam with a clean company
  switcher. Wizard shows a prominent "You are onboarding: <company>" banner
  (users had onboarded a placeholder by accident).
- Module catalog: Enabled is now explicitly a STATUS mirror of the installed
  modules — re-synced by a data <function> on every sapian_core upgrade and on
  demand via a list-header button; the misleading enable/disable toggle is
  gone (module installation happens via the onboarding wizard; managed
  per-company uninstall stays deferred). Sync counts 'to upgrade'/'to install'
  as installed — the upgrade-graph race was exactly the reported drift. List
  defaults to the current company; search/group-by added.
- CI: GitHub Actions workflow (lint: ruff/black/pylint-odoo; fast reference
  goldens; XML/CSV/manifest validation). The Odoo integration suite stays
  local per CLAUDE.md (documented in the workflow).
- samples/: seven accountant-review PDFs rendered from the live Selam tenant
  (payslip, PAYE declaration, pension schedule with the MISSING-POESSA banner,
  customer VAT invoice, WHT certificate, VAT declaration, WHT summary). Docker
  image now bundles the Abyssinica SIL font so Amharic renders in PDFs
  (bilingual names printed as boxes before).
- Housekeeping: disposable scratch DBs dropped; `scratch_final` documented as
  THE demo DB (README: login flow, rebuild command).

### Bug fix — onboarding wizard web path ✅ (2026-07-04)
Found by manual browser testing (container tests never exercised web dispatch);
reproduced and verified over XML-RPC against a live server.
- Root cause #1: applying to a company with existing accounting crashed on the
  ETB currency write ("cannot change the currency … journal items exist") and
  rolled the whole onboarding back → "lost" name/TIN/logo/color. Currency and
  chart-'et' loading are now guarded (skip + warning on the company partner's
  chatter); chart 'et' is only loaded on companies WITHOUT a chart.
- Root cause #2: the wizard dialog stayed the web client's restorable URL
  action → reopened on refresh/company switch, blank screen on close. Apply and
  Cancel now both redirect to the apps home (`/odoo`), which also reloads the
  new company identity (name/logo/color) immediately.
- Post-install writes are committed explicitly after the mid-install registry
  swap (module installation already committed once; a later failure can no
  longer take the post-install writes down).
- `res.company.sapian_onboarding_done` completion flag; the onboarding menu is
  now a router: wizard while not onboarded, module catalog afterwards (admin-
  only menu). Reopening prefills all values from the company — re-applying can
  never silently erase branding.
- Logo validated at the wizard with Odoo's own image pipeline (exactly what
  `res.company.logo` accepts) — bad files fail early with a clear message.
- Demo cleanliness: provisioning archives the core demo companies ("My US
  Company", "My Company (Chicago)"); the switcher shows only real companies.
- 4 new HttpCase browser-path tests (apply persistence + redirect, prefill,
  cancel, menu router); full suite now 90 integration + 67 fast.

### Epic C — onboarding wizard + demo trader tenant ✅ (2026-07-04) — BUILD PHASE COMPLETE
- `sapian_core` v2: `sapian.onboarding.wizard` — company profile (name, TIN,
  address, fiscal year calendar/Ethiopian, ETB), light branding (logo + one
  primary color; external-layout reports and login pick them up natively),
  module picks from a self-seeding standard catalog (7 sellable entries),
  installs the picked modules and applies Ethiopian defaults via the existing
  loaders. Proven unattended on a fresh sapian_core-only DB; idempotent re-run.
  Registry-replacement mid-install handled explicitly (capture → install →
  fresh env).
- `sapian_demo_trader` (new, demo-only): "Selam General Trading PLC" provisioned
  THROUGH the wizard, one July-2026 month of transactions via the real flows —
  quotation → delivery → 15% VAT invoices (56,000 base / 8,400 VAT); PO →
  receipt → bill with 3% WHT (52,000 → 1,560); punitive 30% no-TIN bill
  (4,500, red MISSING row) and 15% foreign digital bill (1,200, "N/A (foreign)");
  posted payroll (23,800 gross / 3,900 PAYE / 18,374 net, one employee missing
  a POESSA ID for the banner) + bank file; July VAT declaration (net −2,850
  credit) and WHT summary (7,260) pre-created, all GL tie-outs green.
- 14 new integration tests: the golden E2E re-runs the exact provisioning code
  and pins every hand-computed number. Fixed en route: stock only auto-creates
  warehouses for new companies in test mode — provisioning creates it
  explicitly.
- **The sellable Payroll+HR wedge and the Essential/Business ERP now exist,
  demo-able end to end. Next: sales, not code.**

### Epic B — `l10n_et_reports` statutory reports slice ✅ (2026-07-04)
- New addon (depends `l10n_et_base`; core l10n_et tax codes + WHT kind markers
  reused, nothing duplicated): monthly VAT declaration (output 15%/zero-rated/
  exempt, input VAT, net payable or credit carried forward) and WHT summary
  (per-bill rows with supplier TIN, totals by rate, grand total).
- Reports are LIVE period windows over posted journal items (reprint after a
  correction → current numbers; refunds net out). Both carry GL tie-out rows
  against the accounts the taxes post to (300700/221200/300600); a manual
  posting that bypasses the tax engine renders a visible MISMATCH warning —
  tested with a rogue-entry regression test.
- Branded PDFs via web.external_layout + CSV exports for both; MISSING-TIN
  markers and fix-before-filing banners (Epic A pattern); 30-day remittance
  note; foreign digital providers excluded from the missing-TIN warning with
  an on-report note ("foreign providers: no local TIN required").
- Golden-verified against the Epic 3 demo docs: output 1,500 / input 10,950 /
  net −9,450 credit; WHT {3%: 1,500, 30%: 4,500, 15%: 1,200} = 7,200, all
  tie-outs green. 18 integration tests; install/uninstall/reinstall verified.
- Layout caveat: computations exact; verify row layout against the current MoR
  forms before filing (README).

### Epic A — `l10n_et_payroll` payroll workflow completion ✅ (2026-07-02)
- Monthly payroll runs on core `hr` (Odoo 19 has no hr_contract/hr_payroll:
  own light models; wages from `hr.version`): payslip generation, manual input
  lines (taxable/exempt earnings, post-tax deductions), freeze-on-confirm.
- Aggregated payroll journal posting to an auto-created `PAY` journal with
  per-company account config auto-resolved from the Ethiopian chart (golden:
  10,000 basic → expenses 11,100; payables 1,650 PAYE + 1,800 pension + 7,650
  net; balanced). Idempotent confirm/reset with chatter audit trail.
- Employee statutory identifiers: TIN (validated via the l10n_et_base reference
  calculator) + POESSA pension ID; statutory reports warn on missing ones.
- Generic bank salary transfer CSV (name/bank/account/net + totals row).
- QWeb reports (EN, `web.external_layout`): payslip PDF, PAYE monthly
  declaration (TIN per row), pension remittance schedule (POESSA ID per row).
- Fixed en route: pension config now effective-date filtered in the compute
  helper (was latest-record); Odoo 19 `_sql_constraints` → `models.Constraint`
  (payroll + sapian_core); sapian_core deprecated `name_get` removed; manifests
  cleaned. 21 integration tests; demo payroll (3 employees, one missing pension
  ID for the warning path) on the ET demo company; install/uninstall/reinstall
  verified.

### Epic 3 — `l10n_et_base` Ethiopian accounting localization ✅ (2026-07-02)
- Reference calculators (`addons/l10n_et_base/reference/et_tax_calc.py`, pure Python,
  no Odoo): WHT applicability + amount (3% goods > 20k / services > 10k, punitive 30%,
  foreign digital 15%, `punitive_respects_thresholds` config flag), Proc 1395/2025
  daily cash-payment cap check, Ethiopian TIN format validation. 45 golden tests in
  `tests_fast/`, adversarially verified (mutation-tested coverage).
- Odoo module extending the core `l10n_et` chart template `'et'`:
  - CoA additions (PAYE Payable 300900, Customs Duty Clearing 230200) and
    account-type fixes for the mistyped core VAT/WHT accounts (3006/3007/3008 →
    liabilities, 2212/2213/2214 → assets) — core files untouched.
  - Automatic WHT lines on vendor bills at post time, driven by the effective-dated
    `l10n.et.wht.config` (rates/thresholds/punitive-gating flag, source notes) and
    the reference calculator; idempotent on re-post; chatter audit trail.
  - Zero-rated + VAT-exempt fiscal positions mapped onto the core 15% VAT taxes.
  - `l10n.et.cash.cap.config` (warn/block/off) enforcing the ETB 30,000/party/day
    cash cap on outbound cash payments.
  - Partner compliance fields (TIN validated + normalized via the reference calc,
    VAT reg. no., business licence no./expiry, foreign-digital flag, Amharic name);
    commercial-field propagation; finance-only partner tab.
  - Printable WHT certificate and Ethiopian VAT invoice (QWeb, EN).
  - Security: access rules + multi-company record rules for both config models.
  - Demo data: 3 partners + posted documents exercising every tax path.
  - 33 Odoo integration tests (golden postings, effective dating, cash cap,
    reports); verified install → uninstall → reinstall on a scratch DB with demo;
    trial balance clean.
- Tooling: `ruff.toml`, `pyproject.toml` (black, line-length 96), `.pylintrc`
  (pylint-odoo 10/10); fixed `config/odoo.conf` inline comments that broke the
  Odoo 19 config parser; payroll import-order lint fixes.

### Revised build order (July 2026, token-conscious — supersedes docs epic order)
Next: Epic A payroll workflow completion → Epic B statutory reports slice →
Epic C thin onboarding + demo tenant. Verticals, payments/SMS, e-invoice,
Ethiopian calendar, full theme, BI deferred until a client signs.

## Baseline (Epics 0–2, ported from the starter repo)

- Repo skeleton: `docker/`, `config/`, `scripts/`, `data-templates/`, `docs/`
  (incl. the July-2026 `docs/plan-2026/` master-planning package).
- `sapian_core`: module catalog model + company defaults (S0-4/S1-1/S1-2).
- `l10n_et_payroll`: PAYE (Proc 1395/2025) + pension (Proc 1268/2022) engine with
  effective-dated rate models and a pure-Python reference calculator — 22 golden
  tests (basic 10,000 → PAYE 1,650 / pension 700 / net 7,650).
