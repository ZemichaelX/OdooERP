# SapianERP Theme — Password reset mail bridge

Two xpaths into one template: `auth_signup.reset_password_email`, the mail a
user gets when they click "Reset password" on the login page.

## What was wrong

Rendered through the product's own call, on a database that already had
`sapian_theme_mail` installed, as the user who really renders it:

```
Powered by <a href="https://www.odoo.com?utm_source=db&utm_medium=auth"
              style="color: #14454F;">Odoo</a>

Thanks,<br/><div>Public user</div>
```

Read the colour on that link. `#14454F` is the house teal — `sapian_theme_mail`
seeded `res.company.email_secondary_color` and this template paints the
attribution with it, so **the brand was being used to advertise Odoo**, in the
client's own mail, over the client's own name.

`sapian_theme_mail` could not have reached this. It overrides
`mail.mail_notification_layout` and `mail.mail_notification_light`; the reset
mail uses neither. It is a standalone `ir.ui.view` rendered directly by
`res.users.action_reset_password` (`auth_signup/models/res_users.py:206`).

## Why a third bridge

`auth_signup.reset_password_email` belongs to `auth_signup`, and inheriting a
view that does not exist aborts an install. Putting the override in
`sapian_theme_mail` would mean adding `auth_signup` to that module's `depends`
— and since it is `auto_install`, the **email colour fix would stop
auto-installing** on any database without signup. A bridge costs a manifest;
the alternative costs the colour fix its reach. `sapian_theme` is excluded for
the reason its own manifest gives: it must install on a database carrying
nothing else of ours, and a CI job asserts that.

`auth_signup` is itself `auto_install` (on `base_setup`, `mail`, `web`), so on
every real tenant this bridge appears with it.

## 1. The attribution

Same words, same link, same switch as the notification layouts, because a
client who unticks one box expects it to mean the same thing everywhere:

- "Powered by Odoo" goes unconditionally.
- "Powered by SapianERP" → <https://sapiantech.com> replaces it, **on by
  default**, and `res.company.sapian_email_attribution` (Settings → General
  Settings → Discuss → Email Templates) switches it off.
- **Off means off.** The whole grey band disappears — never a dangling
  "Powered by", never a fallback to Odoo. That is why the override replaces
  the entire `<tr>` rather than just the anchor.

Matched by HREF, not by position: the template is a stack of visually identical
`<td align="center" style="min-width: 590px;">` cells and the only thing that
tells this one apart is what is inside it.

## 2. The signature

Upstream signs with `user.signature`, where `user` is `self.env.user` at render
time (`mail_render_mixin.py:329`). On the path that matters that is the
**public user** — the reset form is served to somebody who is by definition not
logged in, and the controller's `.sudo()` raises the privilege while leaving
the identity alone. Hence "Thanks, Public user".

It now signs as **the company, always**:

- The message is not from a person. A machine sent it because somebody forgot
  a password; the honest sender is the company.
- Keeping `user.signature` "when there is one" would make the same mail say
  different things depending on who clicked — an admin using Users → *Send
  password reset instructions* would put their personal signature block in
  front of a portal customer who has no relationship with them. A small
  information disclosure, a large inconsistency, and untestable, since the
  content would depend on the session.
- Outward-facing correspondence carries the client's identity, and that is
  their company. The footer of this same mail already carries the company name,
  phone, email and website.

`object.company_id`, not `user.company_id`: `object` is the user being reset, so
on a multi-company tenant the mail is signed by *their* company. The public user
has no meaningful company at all.

## How the tests capture the mail

Not from `mail.mail.body_html` — there is no row to read.
`action_reset_password` wraps the send in
`with contextlib.closing(self.env.cr.savepoint()):`, and `contextlib.closing`
on a `Savepoint` **rolls it back unconditionally** (see the class docstring in
`odoo/sql_db.py`). The mail is physically sent inside that block and the
database row is then discarded. Measured: the `mail.mail` count is identical
before and after a successful send.

So the tests capture the message at the SMTP boundary, through
`mock_mail_gateway`'s patch of `IrMailServer._build_email__`.
`self._mails[0]['body']` is the exact string handed to the mail server, which is
the exact string the recipient opens. A rollback cannot reach a Python list.

**No test in this module can skip.** Every one creates its own user and sends
its own mail — no `skipTest`, no searching for a fixture. `sapian_theme_mail`'s
first version searched for a posted invoice and skipped eight tests silently in
*both* directions; a red proof came back 3 of 15 and the guard had never run.

`TestTheCaptureCanActuallySeeAFailure` is the discrimination proof for the
harness: every other assertion here is "X is not in the body", and all of them
pass on an empty string. It writes a known string into the company immediately
before sending and requires the capture to find it.

## Still carrying Odoo's name, and not in this module's scope

Found while measuring, reported rather than fixed here — they are
`mail.template` **data records**, not `ir.ui.view` templates, so they need a
different mechanism (a data override on `body_html`, not view inheritance):

| Template | xmlid | Who receives it |
|---|---|---|
| Account Created (internal) | `auth_signup.set_password_email` | a new employee |
| Portal Account Created | `auth_signup.portal_set_password_email` | **the client's customer** |
| Unregistered User Reminder | `auth_signup.mail_template_data_unregistered_users` | an invited user who never signed up |

The middle one is customer-facing and is the same defect as this module's.
