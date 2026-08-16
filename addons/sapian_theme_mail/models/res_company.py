# -*- coding: utf-8 -*-
"""The EMAIL colour pair, and whether outgoing mail carries our name.

WHY THIS IS A SECOND SET OF FIELDS
----------------------------------
`sapian_theme` already seeds `primary_color`/`secondary_color`, which is what
printed documents read. Those are `base`'s fields. The colour of the
call-to-action button in an EMAIL is a different pair entirely, added by `mail`
(mail/models/res_company.py:28-33), and nothing was setting it. That is how a
tenant shipped with a teal backend, teal documents, and a purple "View Invoice"
button in its customers' inboxes.

Measured on the demo tenant before this module:

    email_primary_color   '#FFFFFF'
    email_secondary_color '#875A7B'      <- Odoo purple, the column default

THE NAMES ARE THE WRONG WAY ROUND, which is worth knowing before editing:
`email_primary_color` is the button's TEXT and `email_secondary_color` is its
BACKGROUND ("Email Button Text" / "Email Button Color"). Reading them the
obvious way puts white text on a white button.

ONE FIELD, EVERY TEMPLATE
-------------------------
This is the reason the fix is data and not a pile of template overrides. Every
mail template in Odoo that draws a button writes it the same way:

    background-color: {{... .email_secondary_color or '#875A7B'}};
    color: {{... .email_primary_color or '#FFFFFF'}};

— account, sale, portal's invitation, auth_signup's password reset, hr,
gamification, website_sale, and the rest. Setting the company field once turns
all of them, including templates this repo never touches.
"""

import logging

from odoo import api, fields, models

from odoo.addons.sapian_theme import brand

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    # Odoo's own defaults for the two fields (mail/models/res_company.py:28-33).
    # These are the values that mean "this company has expressed no preference".
    #
    # NOTE the difference from `primary_color`, and it matters: that field
    # defaults to False, so an untouched company has an EMPTY field. These two
    # carry a column default, so an untouched company is one still wearing
    # Odoo's exact value — there is no empty state to test for, and
    # `if not company.email_secondary_color` would find nothing on any database.
    ODOO_EMAIL_TEXT = "#FFFFFF"
    ODOO_EMAIL_BUTTON = "#875A7B"

    sapian_email_applied = fields.Char(
        string="SapianERP Email Colours Applied",
        copy=False,
        help="The email button pair SapianERP last wrote to this company, as "
        "'text|background'. Same purpose and same rule as "
        "sapian_brand_applied: it is how a stale house colour is told apart "
        "from a colour the client chose, which are otherwise identical. A "
        "separate marker because the EMAIL colours and the DOCUMENT colours "
        "move independently — which is exactly how a teal backend shipped "
        "alongside a purple invoice email.",
    )

    sapian_email_attribution = fields.Boolean(
        string="Sign outgoing email 'Powered by SapianERP'",
        default=True,
        help="Adds a small 'Powered by SapianERP' line to the footer of "
        "notification emails. Unlike the backend footer, this rides on YOUR "
        "correspondence to YOUR customers, so it is yours to switch off. "
        "Turning it off removes the line entirely — it never falls back to "
        "another vendor's name.",
    )

    @api.model
    def _sapian_email_pair(self):
        """The house pair for email buttons, as (text, background).

        The background is the brand. The text stays white — which is Odoo's
        default too, and is the readable choice on our teal (README.md,
        "Contrast — measured, not assumed").
        """
        return (self.ODOO_EMAIL_TEXT, brand.brand_primary())

    @api.model_create_multi
    def create(self, vals_list):
        """A new company mails in the house colour.

        `setdefault`, never an assignment, and the marker only when BOTH values
        were ours to supply — the same contract `sapian_theme` already applies
        to the document colours. A caller that passes its own email colour
        keeps it and gets no marker, so it is never rewritten later.
        """
        text, button = self._sapian_email_pair()
        for vals in vals_list:
            ours = "email_primary_color" not in vals and "email_secondary_color" not in vals
            vals.setdefault("email_primary_color", text)
            vals.setdefault("email_secondary_color", button)
            if ours:
                vals.setdefault("sapian_email_applied", "%s|%s" % (text, button))
        return super().create(vals_list)

    @api.model
    def _sapian_apply_email_defaults(self):
        """Backfill existing companies. Idempotent, and never overwrites.

        `create` only helps a company that does not exist yet. Every tenant
        already running — including the demo — was created before this module
        and keeps mailing purple until this runs, which is why it is a
        post-install hook rather than a migration: it is provisioning, and it
        is safe to run again.

        "Untouched" is `== Odoo's default`, for the reason in ODOO_EMAIL_BUTTON
        above. Too loose and a client's chosen colour is overwritten; too
        strict and every existing tenant keeps the purple. Both directions are
        real failures, so the test asserts both.

        Returns the companies actually changed, so the caller logs a number
        rather than assuming the work happened.
        """
        text, button = self._sapian_email_pair()
        changed = self.browse()
        # `search([])` with no limit is deliberate and pylint's no-search-all
        # is silenced for it: this must visit EVERY company, including archived
        # ones, or a multi-company tenant gets a branded email from one company
        # and a purple one from the next. The set is bounded by the number of
        # companies on a tenant, which is single digits.
        all_companies = self.sudo().with_context(active_test=False)
        for company in all_companies.search([]):  # pylint: disable=no-search-all
            vals = {}
            if company.email_secondary_color in (False, "", self.ODOO_EMAIL_BUTTON):
                vals["email_secondary_color"] = button
            if company.email_primary_color in (False, ""):
                vals["email_primary_color"] = text
            if not vals:
                continue
            if "email_secondary_color" in vals:
                vals["sapian_email_applied"] = "%s|%s" % (
                    vals.get("email_primary_color", company.email_primary_color),
                    button,
                )
            company.write(vals)
            changed |= company
        return changed
