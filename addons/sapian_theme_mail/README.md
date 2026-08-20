# sapian_theme_mail — the email a client's customer actually receives

The most externally visible surface in the product, and nothing had looked at
it. A customer invoice emailed from a SapianERP tenant arrived carrying:

```
Powered by <a href="https://www.odoo.com?utm_source=db&utm_medium=email"
              style="color: #875A7B;">Odoo</a>
```

and a "View Invoice" button painted `#875A7B` — Odoo purple — on a tenant whose
backend, login page and printed documents were all brand teal.

This does not reach the client's staff, who know what software they bought. It
reaches **their customers**, over the client's name, attached to a document
about money they owe. It outranks the login page for visibility.

## Why it is a bridge and not part of `sapian_theme`

`sapian_theme` depends on `base` + `web` only, and its manifest says why: *"This
module must install on a database that carries no other sapian module, and must
not drag product modules in behind it."* A CI job asserts it installs and passes
entirely alone.

Everything here needs `mail`:

- `email_primary_color` / `email_secondary_color` are fields **`mail`** adds to
  `res.company` (`mail/models/res_company.py:28-33`). Referencing them from
  `sapian_theme` is a `NameError` on a database without mail.
- `mail.mail_notification_layout` and `mail.mail_notification_light` are
  `mail`'s templates. Inheriting a view that does not exist aborts the install.

So the choice was between widening `sapian_theme`'s dependency — breaking the
one property its own manifest promises — and a bridge. Same shape as
`sapian_theme_website` and the `l10n_et_calendar_*` bridges. `auto_install`
because `mail` is a dependency of almost everything, so this appears on every
real tenant automatically; branding outgoing email must not be a tick-box a
deployment can forget.

## Two halves, two mechanisms

### The button colour: one field, every template

`sapian_theme` already seeds `primary_color`/`secondary_color`. Those are
**`base`**'s fields and they drive printed documents. The email button is a
**different pair**, and nothing was setting it — which is precisely how a teal
backend shipped alongside a purple invoice email.

> **The names are the wrong way round.** `email_primary_color` is the button's
> **text** and `email_secondary_color` is its **background** ("Email Button
> Text" / "Email Button Color"). Reading them the obvious way puts white text on
> a white button.

The fix is data, not template overrides, because every mail template in Odoo
draws its button the same way:

```
background-color: {{... .email_secondary_color or '#875A7B'}};
color:            {{... .email_primary_color   or '#FFFFFF'}};
```

account, sale, portal's invitation, auth_signup's password reset, hr,
gamification, website_sale — all of them. Setting the company field once turns
every one, **including templates this repo never touches**.

#### "Untouched" means something different here

`primary_color` defaults to `False`, so a company that never chose one has an
**empty** field. These two carry a **column default**, so there is no empty
state: an untouched company is one still wearing Odoo's exact `#875A7B`.

```python
if company.email_secondary_color in (False, "", ODOO_EMAIL_BUTTON):
```

Too loose and a white-label client's chosen colour gets overwritten; too strict
and every existing tenant keeps mailing purple. Both directions are real
failures, so both are asserted —
`test_a_company_that_chose_its_own_colour_is_never_touched` and
`test_the_backfill_moves_a_company_still_on_odoo_purple`.

The backfill is a **post-install hook**, not a migration: it is provisioning,
and it is idempotent.

### The attribution: ours by default, theirs to switch off

**This is deliberately not the same answer as the backend footer**, and the
difference is who the surface belongs to.

| | backend footer | outgoing email |
|---|---|---|
| Who sees it | the client's own staff | **the client's customers** |
| Whose surface | our product, which they licence | their commercial correspondence |
| Who may change it | **nobody** — constants in `vendor.py` | **the client** — `res.company.sapian_email_attribution` |

"Powered by Odoo" goes unconditionally: it attributes the client's business
software to a vendor that is not us and links their own customer into a
competitor's funnel (`utm_source=db&utm_medium=email`). No licence requires it
— see `sapian_theme/README.md`, "Odoo attribution".

"Powered by SapianERP" replaces it, **on by default**, because this is the
highest-reach surface we have and a white-label ERP vendor is normally
discovered exactly here. It is **switchable** because it rides on the client's
letterhead: a trading company emailing a formal invoice has a legitimate say in
what that document advertises, in a way it does not have over the chrome of
software it licences from us. Recommending "ours, always" would be taking a
decision that is not ours to take.

**Off means off.** The line disappears; it never falls back to Odoo. Asserted by
`test_switching_it_off_removes_the_line_and_does_not_restore_odoo`, which also
checks that no dangling "Powered by" is left behind — the words sit *outside*
the anchor in upstream's markup, so replacing the anchor alone would strand
them.

## The guard renders; it never reads the template

A template-source assertion would have been worthless, and that is not a
stylistic claim — it is what happened. The attribution and the button both sit
behind conditions only the notification pipeline evaluates:

```
show_header = email_notification_force_header or (
    email_notification_allow_header and has_button_access)
show_footer = email_notification_force_footer or (
    email_notification_allow_footer and show_header
    and author_user and author_user._is_internal())
```

`has_button_access` is per recipient; `email_notification_allow_footer` is
passed by the sender — `account.move.send` at
`account/models/account_move_send.py:558`, `sale` at `sale_order.py:1077`.

Two earlier attempts at reproducing this reported a **clean** email on a
database that was demonstrably mailing "Powered by Odoo":

| attempt | result | why it was wrong |
|---|---|---|
| `_render_encapsulate(layout, body)` | `poweredBy=0` | no `show_footer` in context |
| `template.send_mail(...)` | `poweredBy=0` | layout not applied by that path |
| `message_post(...)` + `allow_footer=True` | **`poweredBy=1`** | what the product actually does |

So every test posts a message the way the product posts it and reads
`mail.mail.body_html` — the exact string the customer receives — and
`test_the_footer_really_rendered_or_this_file_proves_nothing` asserts the footer
is present before anything asserts what is *not* in it.

## The switch is in Settings, because otherwise it is not a switch

The decision above says the line is the client's to remove. That was true of
the *field* and false of the *product*: `sapian_email_attribution` lived only on
`res.company`, which a client reaches through Settings > Technical > Companies —
developer mode. A permission that needs developer mode is a sentence in a
README, not a permission.

It now sits in **Settings > General Settings**, inside `mail`'s own **Email
Templates** block (`mail_templates_setting`), directly under **Button Text** and
**Button Color** — the two fields this module seeds. One place for "what our
outgoing mail looks like", rather than a Sapian section nobody would open. It
inherits that block's `groups="mail.group_mail_template_editor,
base.group_system"`, so it is an administrator's setting.

The tests assert the whole path a client takes — open Settings, untick, save —
and then assert the **rendered email**, because asserting the field would be
asserting the part we built again. `test_the_switch_is_on_the_settings_form`
reads the combined arch from `get_view()`, so it fails if the xpath stops
matching or the view stops loading.

### Both red proofs, with the expected counts stated first

| break | expected | got |
|---|---|---|
| settings view withheld | 2 (the two arch tests) | **2** — the four model-path tests still passed, which is the point |
| attribution made unconditional | 2 (both switch-off tests) | **2** |

The second one is worth recording because the **first attempt returned 0**. The
patch script asserted it would find 2 occurrences of
`t-if="company.sapian_email_attribution"` and there are 4 — the two separator
tags start with the same string — so the assertion raised, the file was never
modified, and the run tested unbroken code. Nothing about the output said so
except the number.

That is the CLAUDE.md rule "a red proof is only evidence if the failure COUNT is
what you expected", applied to itself within the hour it was written. The break
is now verified in the file (`grep -c` must print 0) *before* the run is
launched.

## Which customer-facing mail is affected

| Mail | Attribution | Purple button | Covered by |
|---|---|---|---|
| **Invoice sent** | yes — `mail_notification_layout` | yes | both halves |
| **Quotation sent** | yes — same layout, `sale_order.py:1077` | yes | both halves |
| **Payment receipt** | yes — `mail_notification_light` | yes | both halves |
| **Portal invitation** | **no** — `portal.portal_share_template` carries no attribution | yes | the colour field |
| Password reset | yes — `auth_signup.reset_password_email`, its own template | yes | the colour field only |

`mail.mail_notification_layout_with_responsible_signature` — the layout invoices
actually use (`_get_mail_layout`, `account_move_send.py:583`) — is a **primary
inheritance** of `mail_notification_layout` and picks the change up for free.

**The rest of the estate — measured, then closed by a third mechanism.** The two
layouts above cover the mails a *document* produces. They do not cover a mail
that carries its own body, and nobody had counted those. A sweep of the 83
modules reachable from `sapian.module.catalog.STANDARD_CATALOG`, reading all
1,362 data files each of them loads, found **fourteen more templates**, and the guard then found a fifteenth the
sweep could not reach — `auth_totp_mail` is `auto_install`, and a walk that
follows `depends` never arrives at a module that attaches itself. Fifteen
templates, fourteen emails (the digest is two templates, one mail):

| Surface | Who receives it | What it carried |
|---|---|---|
| `auth_signup.set_password_email` | the client's own staff | **8 mentions** — subject line, "Welcome to Odoo", "Your Odoo domain is", a tour link, and a paragraph of competitor marketing |
| `auth_signup.portal_set_password_email` | **the client's customer** | Powered by Odoo |
| `auth_signup.mail_template_user_signup_account_created` | **the client's customer** | Powered by Odoo |
| `im_livechat.livechat_email_template` | **the client's customer** | Powered by Odoo |
| `website_slides.mail_notification_channel_invite` | a course attendee | Powered by Odoo |
| `website_profile.validation_email` | a website visitor | Powered by Odoo |
| `lunch.lunch_order_mail_supplier` | **the client's supplier** | Powered by Odoo |
| `gamification.email_template_badge_received` | the client's own staff | Powered by Odoo |
| `hr_expense.hr_expense_template_submitted_expenses` | a manager | Powered by Odoo |
| `hr_expense.hr_expense_template_register_no_user` | whoever mailed a receipt | Powered by Odoo |
| `digest.digest_mail_main` | the client's managers | "Powered by Odoo" **and** "Sent by Odoo" |
| `digest.digest_section_mobile` | the client's managers | an advert for the vendor's **phone app** — a screenshot on odoo.com, "Run your business from anywhere with Odoo Mobile", two app-store badges |
| `account.mail_template_einvoice_notification` | **the client's customer** | Odoo's **logo image** |
| `account.mail_template_invoice_subscriber` | a journal subscriber | Odoo's **logo image** |
| `auth_totp_mail.mail_template_totp_invite` | the client's own staff | the SUBJECT: "...on your Odoo account" |

`auth_signup.reset_password_email` was the fourteenth and is fixed by xpath in
`sapian_theme_auth_signup`, because it is a QWeb template.

Ten of the thirteen are `mail.template` RECORDS, which cannot be
xpath-inherited: overriding one means copying upstream's entire `body_html` into
this repository, per template, in a bridge per upstream module, and every copy
rots at the next Odoo release. The set is not closed either — an optional module
nobody enumerated, a future version, or a client duplicating an Odoo template
all put it back.

So the third mechanism is a **send-time scrub** at
`mail.mail._prepare_outgoing_body`, upstream's own documented extension point
and the last thing that touches a body before `IrMailServer._build_email__`,
plus `_prepare_outgoing_list` for the subject. Whatever produced the mail, it
comes through there. The rules are plain string work and live in
`reference/mail_debrand.py` with goldens in `tests_fast/test_mail_debrand.py`
that quote upstream's markup verbatim.

**It is not a find-and-replace on the word.** Somebody at the client emailing
their consultant about an Odoo migration keeps their sentence; what is removed
is the branding Odoo injects into mail sent over the client's name — the
attribution, odoo.com links, the logo image, and a short explicit list of
phrases each commented with the template it came from. That last list is the
part that can rot, which is why the guard asserts the POSITIVE: zero branding in
the outgoing form of **every** `mail.template` installed in the database. A
reworded upstream sentence then fails a test instead of shipping.

**Red proof, on one database.** The CI job installs the ten branded modules
WITHOUT this one and shows the probe leaking, then installs this one into that
same database and shows the same probe at zero. A green second phase on its own
could not tell a working scrub from a database that was never branded. First
run: `leaks=3`, `branded_templates=14 of 31`.

**Two things the guard caught in the scrub itself,** which is the argument for
writing it before believing the fix:

* **`/odoo/...` is not branding.** It is Odoo 19's own backend route, and
  `account.mail_template_einvoice_notification` links into it for the "View your
  invoice" button the mail exists for. `\bOdoo\b` matches inside it, so the
  detector flagged two clean templates. Rewriting that URL would have broken the
  button.
* **The vendor's app advert is mostly not the word.** A Play Store link and a
  CDN image carry it; only one of the three markers is "Odoo". A word-level
  scrub would have left the advert standing with our name on it, which is worse
  than leaving it alone.

Two of the fourteen are removed rather than rebranded, and the difference is
deliberate: the "Never heard of Odoo? ... 12+ million users" paragraph and the
phone-app promo are advertising, and there is no version of them that belongs in
a client's mail under anybody's name.

---

# SapianBot — the system's own name in the chatter

`base.partner_root` authors every message no person wrote: "Product created",
stage changes, tracked-field updates, activity reminders. `base` calls it
"System"; `mail` renames it to **OdooBot** and gives it Odoo's face. Measured on
the all-apps demo tenant:

```
res.partner(2)  name  'OdooBot'
                email 'odoobot@example.com'
                image mail/static/src/img/odoobot.png   (0% transparent)
```

and, concretely, *"OdooBot — Product created"* in the chatter of
`product.template` 7 (Binding Wire 1.5 mm).

It is now **SapianBot**, from `sapian_theme/vendor.py`. Not the vendor speaking
and not the client speaking — the system speaking, which is why Odoo names it
after itself; our system is SapianERP. A constant rather than an
`ir.config_parameter` for the reason that file already gives: a system parameter
is writable by `base.group_system`, which on a client's database is the client.

**On the record, because it is a decision and not an oversight:** this partner
authors tracking messages in chatter, and a portal user sees the chatter on
their own documents. So the name reaches the client's customers on a portal
invoice.

## Why this is Python and not a data record

The obvious fix — `<record id="base.partner_root">` in our own data file — does
not work, and it fails in the silent direction. `orm/models.py:5165`:

```python
if not (update and d_noupdate):
    to_update.append(data)
```

`update` is True when a module is being **upgraded** rather than installed, and
`d_noupdate` is the flag **stored on the existing `ir_model_data` row** — not
the flag on our own XML block. `base` creates that row inside
`<data noupdate="True">`, and `_build_update_xmlids_query`'s `ON CONFLICT DO
UPDATE` sets only `(model, res_id, write_date)`, so no later module can clear
it by declaring its own block updateable. Verified on a live database:
`select noupdate from ir_model_data where module='base' and name='partner_root'`
→ `t`.

The consequence is not "it reverts". It is that the rename would reach **new
databases only** — which is every database CI builds and no database a client
runs — while every check stayed green.

So the identity is a `write()`, from `res.partner._sapian_apply_bot_identity()`,
called from two places:

| Caller | Reaches |
|---|---|
| `post_init_hook` | a database installing the module now |
| `migrations/19.0.1.3.0/end-bot_identity.py` | a database that already has it |

The manifest version is load-bearing: the migration runs only when the installed
version is below `19.0.1.3.0`.

**Why it survives `-u mail`:** the same rule pointed the other way — mail's own
record is blocked by the identical check, so nothing in Odoo rewrites this
partner after the database is first built. That is an argument, and an argument
is not a proof, so the `SapianBot survives an upgrade` CI job runs the whole
sequence: install → `-u mail` → `-u sapian_theme_mail` → **break it on purpose
and require the identity tests to fail** → rewind the version and require the
migration to repair it.

## The avatar

`brand/icons/deliver/sapian_core__icon.png`, copied into this module because an
addon must be self-contained, and byte-compared against the brand original by
`test_the_avatar_we_ship_is_the_brand_asset` — brand/README.md forbids a redraw
in those words, and a copy is exactly the thing that drifts into one.

**One file serves both the avatar and the tray icon, and that is a measurement
rather than a shortcut.** Odoo needs two images because `odoobot.png` is a
filled purple tile (0% transparent) and only `odoobot_transparent.png` is safe
over an unknown OS-tray background. Ours is already transparent-backed: 45.5% of
its pixels are fully transparent and all four corners are alpha 0.
`test_the_avatar_is_transparent_backed` is that measurement kept as a guard, and
`test_the_size_the_chatter_renders_is_ours_and_still_transparent` re-checks the
resized `avatar_128` variant separately, because a resize is where an alpha
channel gets flattened onto white.

## The four JS strings

| Leak | Where | Fix |
|---|---|---|
| "Install Odoo" | `mail/core/web/messaging_menu_patch.js` | patched getter |
| "Turn on notifications" icon | same file | **no code** — its only leak was the bot avatar |
| "Odoo will (not) send notifications on this device" | `notification_permission_service.js` | patched service |
| `odoobot_transparent.png` on desktop push | `out_of_focus_service.js` | intercepted in `sendNotification` |

The product name comes from `session_info`, not a JS literal, so a re-brand is
one edit in `vendor.py`.

**What a guard can and cannot say here.** A `patch()` adds code to the bundle;
it never removes the code it patches. `"Install Odoo"` is therefore still a
string inside the served `web.assets_backend` while the menu renders "Install
SapianERP", and no assertion of the form "Odoo's string is gone from the bundle"
can ever pass. So the tests assert what is true instead: ours is *in* the served
bundle (the failure that actually happens — a module installed but absent from
the serving process's addons_path delivers zero JS in silence), and the strings
and paths we intercept are still the ones upstream ships, so a rename turns a
test red rather than turning an interception into a no-op.

## The sweep

`TestNoNewOdooIdentityAppears` is the same shape as the purple-template sweep
above, scoped to **two surfaces only** — the bot partner record and the
messaging menu — and it goes red when the set of Odoo-identity strings **grows**.
It slices the served bundle by Odoo's own `odoo.define("@mail/core/...")`
wrappers, so it reads what the browser got rather than what is on disk. It is
deliberately not "no 'Odoo' anywhere in the bundle": that returns hundreds of
module paths and framework identifiers, and a guard that cries every week is a
guard somebody deletes.

## Odoo's own tests that this rename would break

Reported rather than discovered later. **Our CI does not run any of them** — every
job selects with `/module` tags scoped to our own addons — but a bare
`--test-enable` would hit these:

| Module | Assertions | Installed on a client tenant? |
|---|---|---|
| `im_livechat` | `test_get_discuss_channel.py` ×3 (`"name": "OdooBot"`), `test_chatbot_internals.py` ×2 (a channel named "OdooBot Ernest Employee") | **yes**, if live chat is sold |
| `test_mail`, `test_mail_full`, `test_discuss_full`, `test_mass_mailing` | ×10, including `email_from '"OdooBot" <odoobot@example.com>'` — so the email change breaks these too | no — Odoo's test-only modules |
| `mail` JS suites | 8 files under `mail/static/tests/` | no — run only when mail's own tests are selected |

`web`'s `mock_server/mock_models/res_partner.js` defines its own OdooBot and is
unaffected: it is a mock, not the database.

## What proves the JS patches actually RUN

Named rather than left as accidental protection, because CLAUDE.md is explicit
that a green figure only means something when you say what it proves.

The bundle assertions above prove our file is *served*. They do not execute it —
if `super.start(...)` in the notification-permission patch threw, the bundle
would still contain the string. What executes it is `sapian_theme`'s existing
`browser_js` suite: those tests load `/odoo` in headless Chrome and fail on any
console error, so a patch that broke service start-up takes them down with it.
Measured on a database carrying all three theme modules: **134 tests, 0 failed,
0 skipped**, Chrome reporting.

That coverage is real but indirect. It says "the webclient still boots"; it does
not say "the menu item now reads Install SapianERP". The rendered label needs a
PWA install prompt, which headless Chrome does not raise, so no test here claims
it — the two inputs are asserted separately and the composition is stated.
