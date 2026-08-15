# sapian_theme_website — the bridge that keeps sign-up closed

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
