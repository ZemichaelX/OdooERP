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

**Not fixed here, and stated rather than left to be discovered:**
`auth_signup.reset_password_email` still says "Powered by Odoo". It is a
template of its own rather than a layout, so the two overrides in this module do
not reach it, and its button *is* fixed by the colour field. It is a portal
password reset, not a commercial document, so it did not justify widening this
PR. It is the obvious next one.
