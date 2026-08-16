# -*- coding: utf-8 -*-
"""The password-reset email, asserted on what the SMTP layer was handed.

WHY NOT `mail.mail.body_html`
-----------------------------
The pattern from `sapian_theme_mail` — post, then read the mail.mail row —
cannot work here, and the reason is worth stating because it looks like it
should. `res.users.action_reset_password` wraps the whole send in

    with contextlib.closing(self.env.cr.savepoint()):

and `contextlib.closing` on a Savepoint rolls it back UNCONDITIONALLY (see the
class docstring in odoo/sql_db.py: "The savepoint object can be wrapped in
``contextlib.closing`` to unconditionally roll it back"). The mail is physically
sent inside that block and the database row is then discarded, so after the call
there is no record to read. Measured: `mail.mail` count before and after the
call is identical, on a database that had just sent the mail.

So these tests capture the message where it is real and where a rollback cannot
reach it — at the SMTP boundary, through `mail_mail_gateway`'s patch of
`IrMailServer._build_email__`. `self._mails[0]['body']` is the exact string
handed to the mail server, which is the exact string the recipient opens.

NO TEST HERE CAN SKIP. There is no `skipTest`, no "if the module is installed",
and no searching for a fixture: every test creates its own user and sends its
own mail. The one time this file's sibling searched for a fixture instead, eight
tests skipped silently in both directions and a red proof came back 3 of 15.

WHAT WAS MEASURED BEFORE THE FIX, rendering through the product's own call on a
database with `sapian_theme_mail` already installed:

    Powered by <a href="https://www.odoo.com?utm_source=db&utm_medium=auth"
                  style="color: #14454F;">Odoo</a>
    Thanks,<br/><div>Public user</div>

The link is painted in OUR teal — `sapian_theme_mail` seeded the company's
`email_secondary_color` and this template reads it — so the house brand was
being used to advertise Odoo, in the client's mail, over the client's name.
"""

import re

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.sapian_theme import brand
from odoo.tests import tagged

# Odoo's two purples, asserted absent for the same reason as in
# sapian_theme_mail: swapping one for the other would be no fix at all.
ODOO_PURPLES = ("#875A7B", "#714B67")


class ResetMailCase(MailCommon):
    """Sends a real password-reset mail and hands back what SMTP received."""

    def _reset_mail_body(self, as_public=True):
        """Trigger the reset the way the login page does, return the body.

        `as_public=True` reproduces the path that matters: the reset form is
        served to somebody who is not logged in, so the controller runs as the
        PUBLIC user and calls `.sudo()` — which raises the privilege and leaves
        the identity alone. That distinction is the entire cause of the "Public
        user" signature, so a test that ran as admin would measure a different
        program.
        """
        user = self.env["res.users"].create(
            {
                "name": "Abebe Bekele",
                "login": "abebe.reset@example.com",
                "email": "abebe.reset@example.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        target = user
        if as_public:
            target = user.with_user(self.env.ref("base.public_user")).sudo()
        with self.mock_mail_gateway():
            target.action_reset_password()
            sent = list(self._mails)
        self.assertTrue(sent, "no password-reset mail was sent at all")
        body = sent[0].get("body") or ""
        # A body that came back nearly empty satisfies every "not in" below, so
        # the size is asserted before anything else is.
        self.assertGreater(len(body), 1500, "the reset mail is too short to be the real email")
        # And the parts that prove the template rendered rather than erroring
        # into something short: the recipient's name and the reset link.
        self.assertIn(user.name, body, "the reset mail does not name its recipient")
        self.assertIn("Change password", body, "the reset mail has no reset button in it")
        return body

    def brand_hex(self):
        """From the palette, never a literal — a re-brand must move this."""
        return brand.brand_primary().upper()


@tagged("post_install", "-at_install")
class TestResetMailAttribution(ResetMailCase):
    """ "Powered by Odoo" is gone, and ours is there instead."""

    def test_the_reset_mail_does_not_attribute_the_erp_to_odoo(self):
        body = self._reset_mail_body()
        self.assertNotIn(
            "Powered by Odoo",
            re.sub(r"\s+", " ", body),
            "the password-reset mail still attributes the client's ERP to Odoo",
        )
        self.assertNotIn(
            "odoo.com",
            body,
            "the password-reset mail still links a locked-out user into "
            "odoo.com's marketing funnel",
        )

    def test_the_reset_mail_carries_our_attribution(self):
        """The positive half. Absence of Odoo is not the deliverable.

        Without this, deleting the band outright would satisfy every
        assertion above.
        """
        body = self._reset_mail_body()
        self.assertIn(
            "Powered by",
            re.sub(r"\s+", " ", body),
            "the password-reset mail carries no attribution at all",
        )
        self.assertIn("SapianERP", body, "the attribution does not name us")
        self.assertIn(
            "https://sapiantech.com",
            body,
            "the attribution does not link to us",
        )

    def test_the_attribution_is_painted_in_the_brand(self):
        """The colour the defect wore.

        Before this module the SAME markup painted the word "Odoo" in this
        exact hex, because `sapian_theme_mail` seeds the company field the
        template reads. The colour was never the bug; whose name it painted
        was.
        """
        body = self._reset_mail_body()
        found = re.search(
            r'href="https://sapiantech\.com"[^>]*style="color:\s*(#[0-9A-Fa-f]{6})',
            body,
        )
        self.assertTrue(
            found, "the attribution link carries no colour of its own: %s" % body[-600:]
        )
        self.assertEqual(
            found.group(1).upper(),
            self.brand_hex(),
            "the attribution is not painted in the brand",
        )

    def test_no_odoo_purple_survives_in_the_reset_mail(self):
        body = self._reset_mail_body()
        for purple in ODOO_PURPLES:
            self.assertNotIn(
                purple.lower(),
                body.lower(),
                "the password-reset mail still paints %s" % purple,
            )

    def test_the_button_still_works_and_is_ours(self):
        """The reset link is the whole point of the mail; do not lose it.

        `sapian_theme_mail` is what makes this pass — the template reads
        `email_secondary_color` — and it is asserted HERE because this module
        is the one that rewrites the markup around it.
        """
        body = self._reset_mail_body()
        found = re.search(r"background-color:\s*(#[0-9A-Fa-f]{6})[^\"]*text-decoration", body)
        self.assertTrue(found, "there is no call-to-action button left in the mail")
        self.assertEqual(
            found.group(1).upper(),
            self.brand_hex(),
            "the 'Change password' button is not in the brand colour",
        )


@tagged("post_install", "-at_install")
class TestResetMailSignature(ResetMailCase):
    """It signs as the company, on every path, and never as 'Public user'."""

    def test_it_does_not_sign_itself_public_user(self):
        body = self._reset_mail_body()
        self.assertNotIn(
            "Public user",
            body,
            "the password-reset mail is still signed by Odoo's anonymous " "public account",
        )

    def test_it_signs_as_the_company(self):
        body = self._reset_mail_body()
        signature = self._signature_of(body)
        self.assertIn(
            self.env.company.name,
            signature,
            "the mail thanks the recipient and then names nobody: %r" % signature,
        )

    def test_it_signs_as_the_company_when_an_admin_triggers_it_too(self):
        """THE DISCRIMINATION PROOF for "always", in the other direction.

        Users > "Send password reset instructions" renders with `env.user` set
        to the ADMIN, whose signature is a real signature — so upstream's
        `t-if="user.signature"` branch is live on this path and dead on the
        other. If the fix had been "fall back to the company when there is no
        signature", this test would find the admin's name in a mail sent to a
        portal customer. It must find the company on both paths or the two
        paths do not agree.
        """
        admin = self.env.ref("base.user_admin")
        admin.signature = "<div>Mitchell Admin, Chief of Everything</div>"
        self.env.flush_all()
        body = self._reset_mail_body(as_public=False)
        signature = self._signature_of(body)
        self.assertIn(self.env.company.name, signature)
        self.assertNotIn(
            "Chief of Everything",
            body,
            "an internal user's personal signature block reached a portal "
            "user's password-reset mail",
        )

    def _signature_of(self, body):
        """What follows "Thanks," up to the end of that cell — not the body.

        Narrower than "the company name appears somewhere", and the narrowing
        is not theoretical: the company name is already in this mail's FOOTER
        (name, phone, email, website), so a whole-body assertion would pass on
        a mail signed "Public user" and prove nothing at all.

        Bounded by `</td>` rather than by a character count. A count would be a
        magic number sitting a few characters from the footer — the stock
        markup puts ~330 characters of `<hr>` between the signature and the
        company name, so `.{0,300}` would happen to work and would silently
        start including the footer the day that rule was restyled. The cell is
        the actual boundary: the signature is inside the CONTENT cell and the
        company name is in a different table.
        """
        found = re.search(r"Thanks,(.*?)</td>", body, re.S)
        self.assertTrue(found, "the mail no longer thanks the recipient")
        return found.group(1)


@tagged("post_install", "-at_install")
class TestResetMailAttributionIsTheClientsToSwitchOff(ResetMailCase):
    """The same switch as every other mail, and off means off."""

    def test_on_by_default(self):
        self.assertTrue(self.env.company.sapian_email_attribution)

    def test_switching_it_off_removes_the_line(self):
        self.env.company.sapian_email_attribution = False
        self.env.flush_all()
        body = self._reset_mail_body()
        self.assertNotIn("SapianERP", body, "the attribution did not switch off")
        self.assertNotIn(
            "Powered by",
            re.sub(r"\s+", " ", body),
            "switching the attribution off left a dangling 'Powered by'",
        )

    def test_switching_it_off_does_not_restore_odoo(self):
        """The promise made in the README, asserted where it can fail.

        Removing our name must not hand the space back to the vendor whose
        name we removed. Asserted separately from the line above so that a
        failure says which half broke.
        """
        self.env.company.sapian_email_attribution = False
        self.env.flush_all()
        body = self._reset_mail_body()
        self.assertNotIn("odoo.com", body, "switching ours off brought Odoo's back")
        self.assertNotIn("Odoo", body, "Odoo's name is back in the mail")

    def test_switching_it_off_keeps_the_rest_of_the_mail(self):
        """A switch, not a wrecking ball.

        Off removes one band. The recipient must still get their name, their
        reset button and the company's own contact block — otherwise "off"
        would be a way of breaking the mail, and every "not in" assertion above
        would pass on the wreckage.
        """
        self.env.company.sapian_email_attribution = False
        self.env.flush_all()
        body = self._reset_mail_body()
        self.assertIn("Change password", body)
        self.assertIn(self.env.company.name, body)

    def test_switching_it_back_on_restores_ours(self):
        """So "off" is a switch and not a one-way door."""
        self.env.company.sapian_email_attribution = False
        self.env.flush_all()
        self.env.company.sapian_email_attribution = True
        self.env.flush_all()
        body = self._reset_mail_body()
        self.assertIn("SapianERP", body, "the attribution did not come back")
        self.assertNotIn("odoo.com", body)


@tagged("post_install", "-at_install")
class TestTheCaptureCanActuallySeeAFailure(ResetMailCase):
    """THE DISCRIMINATION PROOF for the harness itself.

    Every assertion in this file is of the form "X is not in the body". All of
    them pass on an empty string, on a body that never rendered, and on a
    capture that silently recorded nothing — which is exactly the state
    `mail.mail.body_html` would have left them in, since the row is rolled back
    before any test could read it.

    So: put a known string into the mail and require the capture to find it. If
    this goes green while the others go green, the others mean something.
    """

    def test_the_body_we_capture_is_the_body_that_was_sent(self):
        self.env.company.write({"name": "Sapian Capture Probe PLC"})
        self.env.flush_all()
        body = self._reset_mail_body()
        self.assertIn(
            "Sapian Capture Probe PLC",
            body,
            "a string written into the company right before sending did not "
            "appear in the captured mail, so this file is reading something "
            "other than the mail that was sent",
        )
