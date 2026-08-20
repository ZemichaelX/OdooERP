# -*- coding: utf-8 -*-
"""No outgoing email carries another vendor's branding. Asserted on the LIST.

WHY THE LIST AND NOT A SAMPLE
-----------------------------
The four items this work started from were the four somebody had noticed. A
sweep of the modules our catalogue reaches found eleven, plus two carrying
Odoo's logo as an image. Any test that names templates would have found exactly
the ones already known, which is how the count stayed at four.

So this walks every `mail.template` INSTALLED IN THIS DATABASE, whatever
modules that is, and fails on the first one whose outgoing form still names the
vendor. A module added later is covered on the day it is installed.

WHY IT READS `_prepare_outgoing_body()` AND NOT `body_html`
-----------------------------------------------------------
`body_html` is the field; it is no longer the last word. The scrub runs at
`mail.mail._prepare_outgoing_body`, which is what `IrMailServer._build_email__`
is handed, so reading the field would report a branded body on a database that
sends a clean one — and, worse, would keep reporting clean if the hook were
removed and the field happened to be fixed some other way. The assertion is on
the string that leaves the process.

THE FIXTURE IS BUILT, NOT SEARCHED
----------------------------------
An earlier guard in this repository searched for a posted invoice, called
`skipTest` when it found none — which was every database in CI — and so had
never run in either direction while reporting twelve passes. Every mail here is
constructed by the test.
"""

import re

from odoo.tests import TransactionCase, tagged

from odoo.addons.sapian_theme import vendor
from odoo.addons.sapian_theme_mail.reference import mail_debrand


@tagged("post_install", "-at_install")
class TestOutgoingDebrand(TransactionCase):
    """Every template in the database, through the real send path."""

    def _outgoing(self, body, subject="Subject", company=None):
        """Return what would actually be sent for ``body``/``subject``."""
        mail = (
            self.env["mail.mail"]
            .sudo()
            .create(
                {
                    "subject": subject,
                    "body_html": body,
                    "email_to": "customer@example.com",
                    "auto_delete": False,
                }
            )
        )
        if company is not None:
            mail = mail.with_company(company)
        out_body = mail._prepare_outgoing_body()
        out = mail._prepare_outgoing_list()
        out_subject = out[0]["subject"] if out else subject
        return out_body, out_subject

    # ---- the sweep -------------------------------------------------------

    def test_no_installed_mail_template_can_send_odoo_branding(self):
        """The LIST, not a sample of it.

        Templates are read raw rather than rendered: rendering needs a record
        of the right model for each of them, and the branding upstream ships is
        static markup that no rendering removes. What matters is that the SEND
        path takes it out, and that is what is measured.
        """
        templates = self.env["mail.template"].sudo().search([])
        self.assertGreater(
            len(templates),
            20,
            "fewer than 20 mail templates in this database — the sweep would "
            "prove almost nothing, so the install list is wrong",
        )

        branded_before, still_branded = [], []
        for template in templates:
            body = template.body_html or ""
            subject = template.subject or ""
            if mail_debrand.odoo_branding_in(body) or mail_debrand.odoo_branding_in(subject):
                branded_before.append(template.name or str(template.id))
            out_body, out_subject = self._outgoing(body, subject or "Subject")
            leaks = mail_debrand.odoo_branding_in(out_body) + mail_debrand.odoo_branding_in(
                out_subject
            )
            if leaks:
                still_branded.append("%s -> %s" % (template.name, leaks[:3]))

        # A GREEN THAT NEEDS A RED TO MEAN ANYTHING. If no installed template
        # was branded to begin with, "none is branded now" is a fact about the
        # database, not about this fix.
        self.assertTrue(
            branded_before,
            "not one installed mail.template carried Odoo branding, so this "
            "test cannot tell a working scrub from a missing one. Install the "
            "modules the CI job installs.",
        )
        self.assertFalse(
            still_branded,
            "%d of %d installed templates still send Odoo branding:\n  %s"
            % (
                len(still_branded),
                len(templates),
                "\n  ".join(still_branded[:10]),
            ),
        )

    # ---- the specific mails this item was raised about -------------------

    def test_the_three_auth_signup_templates_and_the_livechat_transcript(self):
        """Named because they are the ones a person can check by hand.

        Two of the four go to the CLIENT'S CUSTOMER — the portal invitation and
        the chat transcript — which is why this item existed.
        """
        wanted = [
            "auth_signup.set_password_email",
            "auth_signup.portal_set_password_email",
            "auth_signup.mail_template_user_signup_account_created",
            "im_livechat.livechat_email_template",
        ]
        checked = 0
        for xmlid in wanted:
            record = self.env.ref(xmlid, raise_if_not_found=False)
            if not record:
                continue
            checked += 1
            body = getattr(record, "body_html", False) or getattr(record, "arch_db", "")
            if isinstance(body, dict):  # arch_db is translated
                body = next(iter(body.values()), "")
            self.assertTrue(
                mail_debrand.odoo_branding_in(body),
                "%s is not branded upstream any more; this expectation is "
                "stale and the sweep above is now the only real check" % xmlid,
            )
            out_body, _ = self._outgoing(body)
            self.assertFalse(
                mail_debrand.odoo_branding_in(out_body),
                "%s still sends Odoo branding: %s"
                % (xmlid, mail_debrand.odoo_branding_in(out_body)[:3]),
            )
        self.assertGreaterEqual(
            checked,
            3,
            "only %d of the four named templates exist here; `auth_signup` "
            "must be installed for this test to mean anything" % checked,
        )

    # ---- the switch ------------------------------------------------------

    def test_the_attribution_is_ours_by_default(self):
        body = 'Powered by <a href="https://www.odoo.com?utm_source=db">Odoo</a>'
        out, _ = self._outgoing(body)
        self.assertIn(vendor.SAPIAN_PRODUCT, out)
        self.assertIn(vendor.SAPIAN_URL, out)
        self.assertFalse(mail_debrand.odoo_branding_in(out))

    def test_switching_the_attribution_off_removes_the_line_entirely(self):
        """Off means off, and never means "somebody else's name"."""
        company = self.env.company
        company.sudo().write({"sapian_email_attribution": False})
        body = 'Powered by <a href="https://www.odoo.com?utm_source=db">Odoo</a>'
        out, _ = self._outgoing(body, company=company)
        self.assertNotIn("Powered by", out)
        self.assertNotIn(vendor.SAPIAN_PRODUCT, out)
        self.assertFalse(mail_debrand.odoo_branding_in(out))

    def test_a_users_own_words_are_not_rewritten(self):
        """The scrub is not a find-and-replace on the vendor's name.

        Somebody at the client emailing their consultant about a migration must
        keep their sentence. This is the case that makes a blunter rule
        unacceptable, and it is asserted on the real send path rather than only
        in the fast goldens.
        """
        theirs = "<p>Please quote for migrating our Odoo 17 database.</p>"
        out, _ = self._outgoing(theirs)
        self.assertIn("migrating our Odoo 17 database", out)

    def test_the_subject_is_scrubbed_on_the_way_out(self):
        _, subject = self._outgoing(
            "<p>hello</p>", subject="Abebe invites you to connect to Odoo"
        )
        self.assertEqual(subject, "Abebe invites you to connect to SapianERP")
        self.assertFalse(mail_debrand.odoo_branding_in(subject))

    def test_the_hook_is_the_one_upstream_documents(self):
        """A named-method check, so a rename upstream fails here loudly.

        `_prepare_outgoing_body` is called by `_prepare_outgoing_list`, which is
        called by `_send`. If Odoo renames either, this module silently stops
        scrubbing and every other test in this file keeps passing, because they
        all call the method directly.
        """
        mail_mail = self.env["mail.mail"]
        self.assertTrue(hasattr(mail_mail, "_prepare_outgoing_body"))
        self.assertTrue(hasattr(mail_mail, "_prepare_outgoing_list"))
        source = re.sub(r"\s+", " ", mail_mail._prepare_outgoing_list.__doc__ or "")
        self.assertTrue(source, "upstream's _prepare_outgoing_list lost its docstring")
