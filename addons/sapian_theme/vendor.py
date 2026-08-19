# -*- coding: utf-8 -*-
"""Who WE are — Sapian's own identity, as it appears on a client's screen.

This is the vendor's name and the vendor's support line, and it is deliberately
NOT the tenant's. The backend footer used to sign itself with
``res.company.name`` and the ``sapian_theme.support_contact`` parameter, so a
tenant installed for Golbon Trading told its users, at the bottom of every
page, that the software was Golbon's and that support was Golbon's number. That
is the same defect as the login page saying "Powered by Odoo", pointed the other
way: the product on screen is not the product being sold.

CONSTANTS, NOT SYSTEM PARAMETERS — the decision, and why
--------------------------------------------------------
`ir.config_parameter` was the obvious home, and it is the wrong one:

* **A tenant admin can edit it.** Technical > System Parameters is open to
  anyone with `base.group_system`, which on a client's own database is the
  client. So can `res.company`. A store the tenant can write is a store that
  says the value is theirs to set — and the brief is explicit that a client
  editing their own company must not be able to change our footer.
* **It is not configuration.** A parameter implies a deployment chooses it.
  Nothing chooses this: every SapianERP installation carries the same
  attribution, and one that carried a different one would be a defect.
* **A release is the delivery mechanism anyway.** Each client runs our image;
  changing our support number ships the way every other change ships. Storing
  it per-tenant would mean N places to update and no way to know they agreed.

Same shape as ``brand.py``: one file is the source, everything else reads it,
and nothing restates it.

WHERE IT REACHES THE SCREEN
---------------------------
The backend is a single-page OWL application, so the footer is handed these
through ``session_info`` (see models/ir_http.py) rather than reading a template
variable. `TestVendorFooterIsNotTheTenants` proves a tenant cannot move them:
it renames the company, sets the support parameter, and asserts the served
payload is unchanged.

WHAT IS DELIBERATELY LEFT ALONE
-------------------------------
The LOGIN page still shows the tenant's own ``sapian_theme.support_contact``
when one is configured. That page is where a client's staff go when they cannot
get in, and the number they need there is their own internal one — the brief
covered the backend footer, and widening it to the login page would be a
different decision, not an implementation detail of this one.
"""

# The legal name, as it should appear in a copyright line.
SAPIAN_COMPANY = "Sapian Technologies PLC"

# One string, rendered verbatim after "For Support:". Kept as a single value
# rather than a phone/email pair because the footer prints it as one line and a
# structure nobody iterates is a structure that goes stale.
SAPIAN_SUPPORT = "+251 11 668 1234 / support@sapiantech.com"

# Read by the backend footer, which links our name to us — see
# static/src/xml/backend_footer.xml.
#
# It is NOT what the login page and the portal attribution use: those are
# server-side QWeb (views/login_templates.xml, views/brand_promotion.xml) and
# carry the href literally, because a template rendered by the server cannot
# reach a Python constant without a model method whose only job would be to
# return it. Said plainly rather than left implied: this constant is one of
# three copies of the domain, not the single home for it, and the two templates
# are where the other two live.
SAPIAN_URL = "https://sapiantech.com"

# ---------------------------------------------------------------- the system

# The product name, as a user reads it. Distinct from SAPIAN_COMPANY above:
# that is the legal entity that signs a copyright line, this is the thing on
# the screen. Both appear, and confusing them is how a footer ends up saying
# "Powered by Sapian Technologies PLC".
SAPIAN_PRODUCT = "SapianERP"

# THE SYSTEM'S OWN NAME IN THE CHATTER.
#
# `base.partner_root` is the author of every message no person wrote: "Product
# created", stage changes, tracked-field updates, the scheduled-activity
# reminders. `base` calls it "System"; `mail` renames it to "OdooBot" and gives
# it Odoo's face (mail/data/res_partner_data.xml).
#
# It is NOT the vendor speaking and NOT the client speaking — it is the system
# speaking, which is exactly why Odoo names it after itself. Our system is
# SapianERP, so the name follows the product, and it lives here rather than in
# `ir.config_parameter` for the reason this file already gives: a system
# parameter is writable by `base.group_system`, which on a client's database is
# the client.
#
# ON THE RECORD, because it is a decision and not an oversight: this partner
# authors tracking messages in the chatter, and a portal user sees the chatter
# on their own documents. So this name reaches the CLIENT'S CUSTOMERS on a
# portal invoice. That is accepted — the system is ours in a way the invoice's
# letterhead is not.
SAPIAN_BOT = "SapianBot"

# `example.com` deliberately, and it is not laziness — it is RFC 2606's
# reserved domain, the same choice Odoo made with `odoobot@example.com`. The
# address must never resolve: it belongs to a record that cannot read replies,
# and pointing it at a real mailbox would invite mail nobody reads.
SAPIAN_BOT_EMAIL = "sapianbot@example.com"
