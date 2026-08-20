# -*- coding: utf-8 -*-
"""The last point every outgoing email passes through.

WHAT WAS WRONG, MEASURED RATHER THAN ASSUMED
--------------------------------------------
The two notification LAYOUTS were fixed by xpath (views/mail_attribution.xml),
and that fixed the invoice and the quotation — the mails the earlier work was
about. It did not fix the mails that carry their own body.

A sweep of the 83 modules reachable from `sapian.module.catalog.STANDARD_CATALOG`
— 1,362 data files read — found ELEVEN more surfaces still carrying another
vendor's branding, four of them addressed to someone outside the client's
company:

  auth_signup.set_password_email .................. the client's own staff
  auth_signup.portal_set_password_email ........... THE CLIENT'S CUSTOMER
  auth_signup.mail_template_user_signup_account_created  THE CLIENT'S CUSTOMER
  im_livechat.livechat_email_template ............. THE CLIENT'S CUSTOMER
  website_slides.mail_notification_channel_invite . a course attendee
  website_profile.validation_email ................ a website visitor
  lunch.lunch_order_mail_supplier ................. the client's SUPPLIER
  gamification.email_template_badge_received ...... the client's own staff
  hr_expense.hr_expense_template_submitted_expenses  a manager
  hr_expense.hr_expense_template_register_no_user .. whoever mailed a receipt
  digest.digest_mail_main ......................... the client's managers

and two more that are not words at all: `account.mail_template_einvoice_notification`
and `account.mail_template_invoice_subscriber` embed Odoo's own LOGO IMAGE at the
head of a finance email.

WHY A SEND-TIME SCRUB. Ten of those are `mail.template` RECORDS, which cannot be
xpath-inherited: overriding one means copying upstream's whole `body_html` into
this repository, per template, in a bridge module per upstream module, and every
copy rots at the next Odoo release. The set is not closed either — an optional
module nobody enumerated, a future version, or a client duplicating an Odoo
template all put it back.

`_prepare_outgoing_body` is upstream's own documented extension point ("to be
inherited to add custom content depending on some module") and the last thing
that touches a body before `IrMailServer._build_email__`. Whatever produced the
mail, it comes through here.

WHY NOT `body_html`. Scrubbing the stored field would look tidier and would show
in the record, but it is reachable by a dozen write paths and none of them is the
send. The existing tests read `mail.mail.body_html` precisely because that used
to be the last word; it no longer is, so `test_outgoing_debrand.py` reads what
this method returns — the exact string handed to the SMTP builder.

THE RULES THEMSELVES ARE NOT HERE. They are plain string work, so they live in
`reference/mail_debrand.py` with goldens in `tests_fast/` that quote upstream's
markup verbatim (CLAUDE.md rule 10).
"""

import logging

from odoo import models

from odoo.addons.sapian_theme import vendor

from ..reference import mail_debrand

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = "mail.mail"

    # ---- helpers ---------------------------------------------------------

    def _sapian_mail_company(self):
        """The company whose letterhead this mail rides on.

        The record's company first: a multi-company tenant sending an invoice
        from company B must honour B's attribution switch, not whichever
        company the cron user happens to be in. `env.company` is the fallback
        for a mail attached to no record at all — a password reset, say.
        """
        self.ensure_one()
        company = self.mail_message_id.sudo().record_company_id
        return company or self.env.company

    def _sapian_attribution_html(self):
        """Our line, or ``None`` to remove the run outright.

        ``None`` and not an empty string: the scrub distinguishes "replace it
        with this" from "there should be nothing here", and a company that
        switched the line off has asked for the second. It never falls back to
        another vendor's name.
        """
        company = self._sapian_mail_company()
        if not company.sapian_email_attribution:
            return None
        colour = company.email_secondary_color or "#14454F"
        return 'Powered by <a target="_blank" href="%s" style="color: %s;">%s</a>' % (
            vendor.SAPIAN_URL,
            colour,
            vendor.SAPIAN_PRODUCT,
        )

    # ---- the two overrides -----------------------------------------------

    def _prepare_outgoing_body(self):
        """Scrub the body upstream just finished assembling."""
        body = super()._prepare_outgoing_body()
        scrubbed = mail_debrand.debrand_html(
            body,
            vendor.SAPIAN_PRODUCT,
            attribution_html=self._sapian_attribution_html(),
        )
        if scrubbed != body:
            # WHAT CHANGED, not that something was attempted. A run that
            # scrubbed nothing is silent, so this line appearing at all is the
            # evidence the hook is wired up on a real send.
            _logger.info(
                "sapian_theme_mail: debranded outgoing mail %s (%d chars removed)",
                self.id,
                len(body) - len(scrubbed),
            )
        return scrubbed

    def _prepare_outgoing_list(self, mail_server=False, doc_to_followers=None):
        """And the subject, which travels beside the body rather than in it.

        `auth_signup.set_password_email` is the one that needs it: its subject
        reads "... invites you to connect to Odoo", so a body-only fix leaves
        the vendor's name in the line every recipient sees first, in their
        inbox list, before opening anything.
        """
        emails = super()._prepare_outgoing_list(
            mail_server=mail_server, doc_to_followers=doc_to_followers
        )
        for email in emails:
            if email.get("subject"):
                email["subject"] = mail_debrand.debrand_subject(
                    email["subject"], vendor.SAPIAN_PRODUCT
                )
        return emails
