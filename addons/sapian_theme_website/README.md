# sapian_theme_website — what `website` changes about a SapianERP tenant

Two things, and they share a shape: installing `website` silently rewrote how
the product presents itself to a stranger, and in both cases every check we had
kept passing.

1. **Public sign-up opened.** `website_sale`'s post-install hook sets every
   website to `b2c`, and the login controller stopped reading the parameter our
   guard was reading.
2. **The login page became a page of the marketing site.** `/web/login` was
   served inside Odoo's default website header and footer — see
   "The login page is not a website page" below.


A tenant of ours is a private company ERP. Nobody on the internet creates an
account on it. That was true, and then it quietly stopped being true.

## What went wrong

`website_sale` is in `sapian.module.catalog` — it is something we sell. Its
post-install hook opens public sign-up on every website of the tenant that
bought it:

```python
# website_sale/__init__.py:15
env['website'].search([]).auth_signup_uninvited = 'b2c'
# website_sale/models/website.py:88
auth_signup_uninvited = fields.Selection(default='b2c')
```

Measured on the 36-app database (`build_demo.sh … --all-apps`) before this
module existed:

| | |
|---|---|
| `ir.config_parameter auth_signup.invitation_scope` | `b2b` |
| `website 'My Website'.auth_signup_uninvited` | **`b2c`** |
| `GET /web/login` | **"Don't have an account?"** |
| `CHECK login_signup_scope` (the guard) | **`b2b` — green** |

## Why the guard was green

The login controller asks one method:

```
auth_signup/controllers/main.py:132
    'signup_enabled': ..._get_signup_invitation_scope() == 'b2c'
```

Two modules define it and **neither calls `super()`**:

```
auth_signup/models/res_users.py:88   -> the config parameter
website/models/res_users.py:66       -> the per-website column `or` the parameter
```

So the highest class in the MRO ends the chain. The parameter we set is read
only while `website` is absent. Our guard kept reading it.

That is the third time a check here was correct when written and wrong
afterwards because the system moved underneath it — `login_primary` was green
while the page said "Powered by Odoo"; `is_redirect_home` was `True` while
`action_id` decided the landing. `scripts/lib/check_login_page.py` now reports
`login_signup_effective`, taken from the method the controller calls.

## Why a bridge and not part of `sapian_theme`

The override was written in `sapian_theme` first. It was dead code in every
configuration, and the MRO says so:

```
MRO: [website.res_users, auth_signup.res_users, sapian_theme.res_users]
_get_signup_invitation_scope() -> 'b2c'
```

`sapian_theme` depends on `base` + `web` only — deliberately, so it installs on
a database carrying nothing else of ours — which loads it *before* both, and a
module can only win this by depending on `website`. Same reasoning that makes
`l10n_et_calendar_account` a bridge so `l10n_et_calendar` never has to depend on
`account`. `auto_install` means it appears exactly when both sides are present.

`TestPublicSignupScope.test_we_are_above_website_in_the_mro` asserts the order,
not just the result, so a future dependency change that demotes us fails with
the reason instead of silently reopening sign-up.

## One override, and no write — which was tried first

The first version also normalised the stored `website.auth_signup_uninvited`
rows in a `post_init_hook`, so Settings > Website would not read "Free sign up"
on a tenant where sign-up is closed. It was removed, because it cannot win:

| install order | who writes last |
|---|---|
| fresh build, everything in one run | `website_sale`'s hook, after ours |
| existing tenant buys `website_sale` | `website_sale`'s hook, a year after ours |
| bridge installed onto an existing `website_sale` | ours |

Two of three. This module's own test caught it on
`-i sapian_theme,website,website_sale`. A guarantee that holds only when modules
happen to install in the right order is the class of thing this module exists to
remove, so the write is gone and the override is the whole mechanism — it is
read on every request, so it holds regardless of what is installed, when.

**The consequence, stated rather than hidden:** Settings > Website can read
"Free sign up" while sign-up is invitation-only. That is a display
inconsistency, not a hole. `scripts/lib/check_login_page.py` prints the stored
rows (`login_signup_websites`) next to the effective value
(`login_signup_effective`) so the difference is visible to whoever looks.

## The escape hatch

```
ir.config_parameter  sapian_theme.allow_public_signup = 1
```

Set it and this module stops interfering: `_get_signup_invitation_scope` then
returns Odoo's own resolution untouched. Off by default, because a private
company ERP that anybody on the internet can open an account on is not a
misconfiguration, it is a breach.

Note what the opt-in does **not** do: it does not turn sign-up on. It stops us
forcing it off. A client running a real webshop sets the parameter *and* sets
Customer Account to "Free sign up" in Settings > Website — two deliberate acts,
which is the point.

Anything other than an explicit truthy value (`1`, `true`, `yes`, `on`) keeps
sign-up closed — a parameter left at `"0"` or `"false"` must never read as
permission, which `test_the_opt_in_is_off_by_default_and_strict` asserts.


## The login page is not a website page

### What was on screen

On a 36-app database with `website` installed — the configuration we ship —
`/web/login` rendered our branded card inside Odoo's default website chrome: a
"Your Logo" navbar with Shop / Events / Courses / Jobs / Contact us, and a
footer with "Useful Links", "We are a team of passionate people...",
`info@yourcompany.example.com` and `+1 555-555-5556`. That is the first screen a
prospect sees.

### Why every login check stayed green

They all measured the **card**, and the card was right:

```
login_powered_sapian=1  login_mark=1  login_signup=0  login_primary=#14454F
```

Four assertions, all true, all still true on the broken page. None of them
described the page we serve. It is the same mistake as reading
`auth_signup.invitation_scope` while the served page offered sign-up — assert
the part you built, never the thing the user is looking at.

### The cause: a view inheritance, not route dispatch

Nothing in website's `ir.http` or its controllers mentions `/web/login`. The
route is still auth_signup's and still renders `web.login`. What changes is the
layout — `website/views/website_templates.xml:1623`:

```xml
<template id="login_layout" inherit_id="web.login_layout"
          name="Website Login Layout" priority="20">
    <xpath expr="t[@t-call]" position="replace">
        <t t-call="website.layout">
            <div class="oe_website_login_container" t-out="0"/>
        </t>
    </xpath>
</template>
```

`web.login_layout` is a `t-call` to `web.frontend_layout` carrying four t-sets,
two of which are `no_header = True` and `no_footer = True`. `web.frontend_layout`
draws `<header t-if="not no_header">` and `<footer t-if="not no_footer">`, so
the stock login page has neither.

website replaces that entire `t-call` element, and **the replacement carries no
t-sets**. `website.layout` inherits `portal.frontend_layout` inherits
`web.frontend_layout`, and it edits the header and footer with
`position="attributes"` rather than replacing them — so both are still guarded
by exactly those two flags. The chrome is not *added* by website; it is
**unsuppressed**. That is why nothing looked wrong in any template we own.

### The fix, and the one that was rejected

`views/login_layout.xml` deactivates that inheritance. `web.login_layout` then
renders as it does with no website installed, so the login page is the *same
page* in both configurations rather than merely chrome-free in each.

Re-setting `no_header`/`no_footer` inside website's `t-call` would also hide the
chrome and was rejected twice over: it leaves the page rendering through
`website.layout`, so the card stays destroyed and the two configurations still
differ; and it depends on the exact markup of website's replacement, so an
upstream edit to that one xpath quietly changes what we are patching.

It survives `-u website` by the loader's own rule, not by hope:
`odoo/tools/convert.py:517-524` writes `active` only when the template tag
carries an `active` attribute and the record is new or the mode is not update.
website's `login_layout` declares no `active`.

### Measured

| route | chrome, `login_layout` active | deactivated |
|---|---|---|
| `/web/login` | 1 | 0 |
| `/web/signup` (sign-up open) | 1 | 0 |
| `/web/reset_password` | 1 | 0 |
| `/` — the marketing site | 1 | **1** |

`/web/login` went from 25,993 to 9,896 bytes. The last row is the point: the
website keeps its own chrome, so "no header on the login page" is a real
result and not a broken theme.

### What it covers, and what it deliberately does not

* **`/web/signup` and `/web/reset_password`** — covered by the same line,
  because they `t-call="web.login_layout"` too (`auth_signup_login_templates.xml`
  lines 36 and 72). Not separately handled.
* **The customer portal (`/my/...`)** — *not* affected, and should not be. It
  renders through `portal.frontend_layout` and `website.layout` and never
  touches `web.login_layout`. Verified by fetching `/my` authenticated: header
  and footer present before and after.
* **`website.protected_403`**, the password prompt for a protected website
  page, `t-call="website.login_layout"` — keeps working and loses the chrome
  too. Measured over HTTP, because a bare `_render` of it fails for want of a
  request in *either* state and settles nothing:

  ```
  login_layout=ACTIVE    http=403  prompt=1  chrome=1  bytes=24333
  login_layout=INACTIVE  http=403  prompt=1  chrome=0  bytes=6531
  ```

  That is a real consequence of touching a shared layout, and it is stated
  rather than buried. Scoping the change to the auth routes alone would need a
  flag passed from the controller.

### The consequence that a test caught

Removing the website footer removed `web.brand_promotion_message` from these
pages — which was the **only** attribution `/web/signup` and
`/web/reset_password` had. `test_the_other_auth_pages_keep_theirs` went red at
0, which is exactly what it was written for.

The attribution moved back into the login card's own footer in
`sapian_theme/views/login_templates.xml`, replacing "Powered by Odoo" in place.
It had been anchored on the login *form* because website destroyed the card —
a workaround that has now outlived its cause, and one that reached `/web/login`
alone. One line now serves all three auth pages, with or without `website`.
