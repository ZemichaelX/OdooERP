# -*- coding: utf-8 -*-
"""Outgoing email, asserted on the RENDERED BODY. Never on the template source.

WHY RENDERED
------------
A template-source assertion is worthless here and the reason is concrete: the
attribution and the button both sit behind conditions that only the notification
pipeline evaluates.

    show_header = email_notification_force_header or (
        email_notification_allow_header and has_button_access)
    show_footer = email_notification_force_footer or (
        email_notification_allow_footer and show_header
        and author_user and author_user._is_internal())

`has_button_access` is computed per recipient; `email_notification_allow_footer`
is passed by the sender — `account.move.send` sets it at
account/models/account_move_send.py:558, `sale` at sale_order.py:1077. Render
without those and the footer simply does not exist, so a test that "rendered the
template" would report a clean email and prove nothing. That happened twice
while finding this defect: `_render_encapsulate` and then `template.send_mail`
both came back with zero attributions on a database that was mailing "Powered
by Odoo" to customers.

So every test here posts a message the way the product posts it, and reads
`mail.mail.body_html` — the exact string the customer receives.

WHAT WAS MEASURED BEFORE THE FIX, on the demo tenant's own invoice:

    Powered by <a href="https://www.odoo.com?utm_source=db&utm_medium=email"
                  style="color: #875A7B;">Odoo</a>

    button: background-color: #875A7B
"""

import re

from odoo.tests import TransactionCase, tagged

from odoo.addons.sapian_theme import brand

# Odoo's two purples. #875A7B is the `email_secondary_color` column default and
# is what the invoice mail actually rendered; #714B67 is the other one Odoo
# uses (webmanifest, loading screen). Both are asserted absent — a fix that
# swapped one Odoo purple for the other would be no fix at all.
ODOO_PURPLES = ("#875A7B", "#714B67")


@tagged("post_install", "-at_install")
class MailBodyCase(TransactionCase):
    """Posts a real notification and hands back what the recipient receives."""

    def _customer_mail_for(self, record, partner, layout):
        """The body of the mail sent to `partner`, rendered by the pipeline.

        THE FOOTER IS FORCED, and that is a correction to an earlier version of
        this file. It passed `email_notification_allow_footer=True` — what
        `account.move.send` passes — and relied on `has_button_access` being
        true for the recipient. On a database without the demo tenant's data
        that chain silently produced no footer, and the "no Powered by Odoo"
        assertions passed on an email that had no footer to put it in.

        `email_notification_force_*` is upstream's own switch for exactly this
        (mail/tests/common.py:1347). What these tests are for is the CONTENT of
        the footer when it renders; that it renders in production is
        established by measurement, recorded in the module README. Forcing it
        makes the content assertions impossible to satisfy vacuously — and
        `_assert_footer_rendered` re-checks it on every single body anyway.
        """
        before = self.env["mail.mail"].search([]).ids
        record.with_context(
            mail_notify_force_send=False,
            email_notification_allow_footer=True,
            email_notification_force_header=True,
            email_notification_force_footer=True,
        ).message_post(
            body="<p>Test notification.</p>",
            subject="Test",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            partner_ids=partner.ids,
            email_layout_xmlid=layout,
        )
        mails = self.env["mail.mail"].search([("id", "not in", before)])
        self.assertTrue(mails, "no mail was generated at all")
        body = ""
        for mail in mails:
            if partner in mail.recipient_ids:
                body = mail.body_html or ""
                break
        self.assertTrue(body, "no mail was addressed to the customer")
        # A body that came back nearly empty satisfies every "not in" below.
        self.assertGreater(len(body), 500, "the rendered mail is too short to be a real email")
        # EVERY body, not just the one test that used to check it: the footer
        # must be present before anything asserts what is absent from it.
        self.assertIn(
            self.env.company.name,
            body,
            "the mail footer did not render, so any assertion about what is "
            "NOT in it proves nothing",
        )
        return body

    def _subject_record(self):
        """A record to notify about, CREATED here — never searched for.

        The earlier version searched for a posted customer invoice and called
        `skipTest` when it found none. On every database in CI it found none,
        so all eight rendered tests skipped — in the run with the fix and in
        the run without it. A skip is a success signal produced by doing
        nothing, and this file was producing eight of them.

        The attribution and the button live in the LAYOUT, not in the invoice,
        so any record that can be posted to exercises them. A real invoice is
        used when `account` is present because it is the closest thing to what
        the customer receives; a partner is the fallback, and it exercises the
        identical layout. Either way the test RUNS.
        """
        partner = self.env["res.partner"].create(
            {"name": "Guard Customer PLC", "email": "guard.customer@example.com"}
        )
        if "account.move" not in self.env:
            return partner, partner
        journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.env.company.id)], limit=1
        )
        if not journal:
            return partner, partner
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "journal_id": journal.id,
                "invoice_line_ids": [
                    (0, 0, {"name": "Guard line", "quantity": 1, "price_unit": 100.0}),
                ],
            }
        )
        return move, partner

    def brand_hex(self):
        """The brand from the palette, never a literal.

        A hardcoded teal here would keep passing after a re-brand while the
        emails went out in the old colour.
        """
        return brand.brand_primary().upper()


@tagged("post_install", "-at_install")
class TestInvoiceEmailIsBranded(MailBodyCase):
    """The invoice a customer receives carries our colours and not Odoo's."""

    def setUp(self):
        super().setUp()
        self.invoice, self.customer = self._subject_record()

    def test_the_rendered_invoice_mail_has_no_odoo_attribution(self):
        body = self._customer_mail_for(
            self.invoice,
            self.customer,
            "mail.mail_notification_layout_with_responsible_signature",
        )
        self.assertNotIn(
            "Powered by Odoo",
            body.replace("\n", " "),
            "the invoice email still attributes the client's software to Odoo",
        )
        self.assertNotIn(
            "odoo.com",
            body,
            "the invoice email still links the client's customer to odoo.com",
        )

    def test_the_rendered_invoice_mail_has_no_odoo_purple(self):
        body = self._customer_mail_for(
            self.invoice,
            self.customer,
            "mail.mail_notification_layout_with_responsible_signature",
        )
        for purple in ODOO_PURPLES:
            self.assertNotIn(
                purple.lower(),
                body.lower(),
                "the invoice email still paints %s — the call-to-action button "
                "is in Odoo's colour, not the brand" % purple,
            )

    def test_the_rendered_invoice_mail_carries_the_brand(self):
        """The positive half. Absence of purple is not the deliverable.

        Without this, deleting the button entirely would pass every assertion
        above — and the customer would lose the link to their invoice.
        """
        body = self._customer_mail_for(
            self.invoice,
            self.customer,
            "mail.mail_notification_layout_with_responsible_signature",
        )
        self.assertIn(
            self.brand_hex().lower(),
            body.lower(),
            "the brand colour is nowhere in the invoice email",
        )
        self.assertIn(
            "background-color",
            body,
            "there is no call-to-action button left in the invoice email",
        )
        self.assertIn("SapianERP", body, "the invoice email carries no attribution")

    def test_the_footer_really_rendered_or_this_file_proves_nothing(self):
        """THE PRECONDITION, and it is the whole reason these tests are real.

        Every "not in" assertion above passes on a mail whose footer never
        rendered — which is the state two earlier attempts at this test were
        in. So: assert the footer IS there, by finding the company block that
        only the footer emits.
        """
        body = self._customer_mail_for(
            self.invoice,
            self.customer,
            "mail.mail_notification_layout_with_responsible_signature",
        )
        self.assertIn(
            self.env.company.name,
            body,
            "the mail footer did not render at all, so the assertions about "
            "what is in it prove nothing",
        )


@tagged("post_install", "-at_install")
class TestEmailColourSeeding(TransactionCase):
    """The company field, which is what turns every mail template at once."""

    def test_the_company_mails_in_the_brand(self):
        company = self.env.company
        self.assertEqual(
            (company.email_secondary_color or "").upper(),
            brand.brand_primary().upper(),
            "the email button colour is not the brand",
        )

    def test_a_new_company_is_seeded_too(self):
        company = self.env["res.company"].create({"name": "Seeding Test PLC"})
        self.assertEqual(
            (company.email_secondary_color or "").upper(),
            brand.brand_primary().upper(),
        )
        self.assertTrue(company.sapian_email_applied)

    def test_a_company_that_chose_its_own_colour_is_never_touched(self):
        """THE DISCRIMINATION PROOF for the backfill, in the dangerous direction.

        A white-label client picking their own email colour must keep it. This
        is the assertion that fails if the backfill is ever loosened to "write
        it everywhere".
        """
        company = self.env["res.company"].create(
            {"name": "Golbon Trading PLC", "email_secondary_color": "#C0FFEE"}
        )
        self.assertFalse(
            company.sapian_email_applied,
            "we marked a colour we did not choose, so a later pass would treat "
            "the client's colour as ours to rewrite",
        )
        self.env["res.company"]._sapian_apply_email_defaults()
        self.assertEqual(
            company.email_secondary_color,
            "#C0FFEE",
            "the backfill overwrote a colour the client chose",
        )

    def test_the_backfill_moves_a_company_still_on_odoo_purple(self):
        """And the other direction: it must actually do something.

        An existing tenant sits on the column default. If the backfill skipped
        those too it would be safe and useless — the exact shape of a check
        that passes by doing nothing.
        """
        company = self.env["res.company"].create({"name": "Purple Trading PLC"})
        company.write(
            {
                "email_secondary_color": self.env["res.company"].ODOO_EMAIL_BUTTON,
                "sapian_email_applied": False,
            }
        )
        moved = self.env["res.company"]._sapian_apply_email_defaults()
        self.assertIn(company, moved, "the backfill left a purple company behind")
        self.assertEqual(
            (company.email_secondary_color or "").upper(),
            brand.brand_primary().upper(),
        )


@tagged("post_install", "-at_install")
class TestAttributionIsTheClientsToSwitchOff(MailBodyCase):
    """On by default, and off means off — never a fallback to Odoo."""

    def setUp(self):
        super().setUp()
        self.invoice, self.customer = self._subject_record()

    def test_on_by_default(self):
        self.assertTrue(self.env.company.sapian_email_attribution)

    def test_switching_it_off_removes_the_line_and_does_not_restore_odoo(self):
        self.env.company.sapian_email_attribution = False
        self.env.flush_all()
        body = self._customer_mail_for(
            self.invoice,
            self.customer,
            "mail.mail_notification_layout_with_responsible_signature",
        )
        self.assertNotIn("SapianERP", body, "the attribution did not switch off")
        self.assertNotIn(
            "Powered by",
            body.replace("\n", " "),
            "switching the attribution off left a dangling 'Powered by'",
        )
        self.assertNotIn("odoo.com", body, "switching ours off brought Odoo's back")
        # And the footer itself is still there — we removed a line, not the
        # block that carries the company's own contact details.
        self.assertIn(self.env.company.name, body)


@tagged("post_install", "-at_install")
class TestTheOtherCustomerFacingMail(MailBodyCase):
    """The mails the brief asked about by name, each rendered and reported."""

    def test_a_quotation_mail_is_branded(self):
        """`sale` uses the same layout and passes the same footer flag.

        A real sale.order when `sale` is installed, the shared layout on the
        fallback record otherwise — never a skip. `sale_order.py:1077` passes
        `mail.mail_notification_layout_with_responsible_signature` and
        `email_notification_allow_footer=True`: the same pair the invoice uses,
        so the quotation is branded by the same two changes rather than by
        anything of its own.
        """
        record, partner = self._subject_record()
        if "sale.order" in self.env:
            record = self.env["sale.order"].create({"partner_id": partner.id})
        body = self._customer_mail_for(
            record,
            partner,
            "mail.mail_notification_layout_with_responsible_signature",
        )
        self.assertNotIn("Powered by Odoo", body.replace("\n", " "))
        self.assertNotIn("odoo.com", body)
        for purple in ODOO_PURPLES:
            self.assertNotIn(purple.lower(), body.lower())

    def test_the_compact_layout_is_branded_too(self):
        """`mail.mail_notification_light` — the payment receipt's layout.

        Asserted through the layout rather than through a payment record,
        because a database without a posted payment would otherwise skip the
        only test covering this template. The layout is the thing that carries
        the attribution; the record only chooses it.
        """
        record, partner = self._subject_record()
        body = self._customer_mail_for(record, partner, "mail.mail_notification_light")
        self.assertNotIn("Powered by Odoo", body.replace("\n", " "))
        self.assertNotIn("odoo.com", body)
        for purple in ODOO_PURPLES:
            self.assertNotIn(purple.lower(), body.lower())


@tagged("post_install", "-at_install")
class TestNoOdooPurpleReachesAnyMailTemplate(TransactionCase):
    """The button colour across every shipped template that draws one.

    Not a substitute for the rendering tests above — it is the sweep that
    catches a template nobody has rendered. Most Odoo mail templates write the
    button as `email_secondary_color or '#875A7B'`, so with the company field
    set that fallback is unreachable and the sweep sees nothing. A template
    that HARDCODES the purple instead is a template our field cannot reach.

    IT FOUND FIVE, AND THEY ARE PINNED RATHER THAN HIDDEN. All five are
    internal or supplier-facing, so none is in this PR's scope — which is the
    mail a client's CUSTOMER receives — and none is fixed here:

        Journal Notification        account.mail_template_invoice_subscriber
                                    to journal followers (internal accountants);
                                    a #714B67 gradient header and button
        New eInvoices Notification  account.mail_template_einvoice_notification
        Purchase: Purchase Order    supplier-facing
        Purchase: Vendor Reminder   supplier-facing
        Settings: 2Fa New Login     to the internal user logging in

    The assertion is therefore "no NEW offender", not "no offender". Written
    that way on purpose: an exclusion list that simply subtracts today's
    failures is how a sweep stops meaning anything, so this one goes red if the
    set GROWS — a sixth template, or one of the customer-facing templates
    joining them — which is the regression worth catching.
    """

    # Pinned baseline, by template NAME because the xmlid is not on the record.
    KNOWN_INTERNAL_OFFENDERS = {
        "Journal Notification",
        "New eInvoices Notification",
        "Purchase: Purchase Order",
        "Purchase: Vendor Reminder",
        "Settings: 2Fa New Login",
    }

    # The mail this PR is about. None of these may EVER hardcode a purple.
    CUSTOMER_FACING = (
        "account.email_template_edi_invoice",
        "account.mail_template_data_payment_receipt",
        "sale.email_template_edi_sale",
    )

    def _offenders(self):
        templates = self.env["mail.template"].search([])
        self.assertGreater(
            len(templates), 5, "no mail templates found, so this sweep is vacuous"
        )
        found = {}
        for template in templates:
            # The `or '#875A7B'` fallback is fine — unreachable while the
            # company field is set. A bare literal is not.
            body = re.sub(
                r"or\s*['\"]#875A7B['\"]", "", str(template.body_html or ""), flags=re.I
            )
            for purple in ODOO_PURPLES:
                if purple.lower() in body.lower():
                    found[template.name] = purple
        return found

    def test_no_new_template_hardcodes_odoo_purple(self):
        found = self._offenders()
        new = set(found) - self.KNOWN_INTERNAL_OFFENDERS
        self.assertFalse(
            new,
            "these mail templates hardcode an Odoo purple and are not in the "
            "known internal set, so the company colour field cannot reach "
            "them: %s" % ", ".join("%s (%s)" % (n, found[n]) for n in sorted(new)),
        )

    def test_no_customer_facing_template_hardcodes_odoo_purple(self):
        """The half that matters for this PR, asserted by xmlid not by name."""
        found = self._offenders()
        for xmlid in self.CUSTOMER_FACING:
            template = self.env.ref(xmlid, raise_if_not_found=False)
            if not template:
                continue
            self.assertNotIn(
                template.name,
                found,
                "%s hardcodes an Odoo purple, so setting the company colour "
                "does not brand it" % xmlid,
            )

    def test_the_sweep_can_actually_see_a_purple(self):
        """THE DISCRIMINATION PROOF.

        Every assertion above passes if `_offenders` silently returns nothing —
        a wrong field name, a regex that never matches, a search that came back
        empty. So plant one and require the sweep to find it.
        """
        template = self.env["mail.template"].create(
            {
                "name": "Sapian Sweep Probe",
                "model_id": self.env.ref("base.model_res_partner").id,
                "body_html": "<p style='color: #875A7B;'>planted</p>",
            }
        )
        self.assertIn(
            template.name,
            self._offenders(),
            "the sweep did not notice a template that plainly hardcodes the "
            "purple, so its green result means nothing",
        )


@tagged("post_install", "-at_install")
class TestTheAttributionSwitchIsReachable(MailBodyCase):
    """The switch is in Settings, and using it from there really works.

    The decision in views/mail_attribution.xml is that the line is the CLIENT's
    to remove. That was true of the field and false of the product: it lived on
    res.company only, which means Settings > Technical > Companies, which means
    developer mode. A permission that needs developer mode is not a permission.

    These tests assert the whole path a client takes — open Settings, untick,
    save — and then assert the email that comes out. Asserting the field alone
    would be asserting the part we built again.
    """

    def _settings(self, **values):
        """Open Settings, set values, save — the client's actual path."""
        settings = self.env["res.config.settings"].create(values)
        settings.execute()
        return settings

    def test_the_switch_is_on_the_settings_form(self):
        """In the DOM of the form a client opens, not merely on the model.

        `fields_view_get` returns the combined arch, so this fails if the view
        does not apply — a wrong xpath, an anchor mail renamed, our module not
        loading its view at all.
        """
        arch = self.env["res.config.settings"].get_view()["arch"]
        self.assertIn(
            "sapian_email_attribution",
            arch,
            "the switch is not on the Settings form, so a client cannot reach "
            "it without developer mode",
        )

    def test_it_sits_in_mails_own_email_block(self):
        """Beside Button Text and Button Color, not in a section of our own."""
        arch = self.env["res.config.settings"].get_view()["arch"]
        before, _, after = arch.partition("sapian_email_attribution")
        # The colour fields are the block's other contents; ours must be inside
        # the same setting, which means one of them appears before it.
        self.assertIn(
            "email_secondary_color",
            before,
            "the switch is not inside mail's Email Templates block — a client "
            "looking at their email settings would not see it",
        )
        self.assertTrue(after, "the arch ended at our field, which cannot be right")

    def test_it_defaults_to_on_in_settings(self):
        settings = self.env["res.config.settings"].create({})
        self.assertTrue(
            settings.sapian_email_attribution,
            "the switch reads as off before anyone touches it",
        )

    def test_switching_it_off_from_settings_reaches_the_company(self):
        self._settings(sapian_email_attribution=False)
        self.assertFalse(
            self.env.company.sapian_email_attribution,
            "saving Settings did not write the company field",
        )

    def test_switching_it_off_from_settings_removes_the_line_from_the_email(self):
        """THE ONE THAT MATTERS. The client's path, then the rendered body.

        And the third assertion is the promise made in the module README:
        removing our name must not hand the space to Odoo.
        """
        self._settings(sapian_email_attribution=False)
        record, partner = self._subject_record()
        body = self._customer_mail_for(
            record,
            partner,
            "mail.mail_notification_layout_with_responsible_signature",
        )
        self.assertNotIn(
            "SapianERP",
            body,
            "unticking the setting did not remove our attribution from the mail",
        )
        self.assertNotIn(
            "Powered by",
            body.replace("\n", " "),
            "unticking the setting left a dangling 'Powered by'",
        )
        self.assertNotIn(
            "odoo.com",
            body,
            "removing our attribution restored Odoo's — off must stay off",
        )
        self.assertNotIn(
            "Odoo",
            body,
            "Odoo's name came back into the mail when ours was switched off",
        )

    def test_switching_it_back_on_restores_ours(self):
        """The other direction, so 'off' is a switch and not a one-way door."""
        self._settings(sapian_email_attribution=False)
        self._settings(sapian_email_attribution=True)
        record, partner = self._subject_record()
        body = self._customer_mail_for(
            record,
            partner,
            "mail.mail_notification_layout_with_responsible_signature",
        )
        self.assertIn("SapianERP", body, "the attribution did not come back")
        self.assertNotIn("odoo.com", body)
