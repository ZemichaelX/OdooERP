# -*- coding: utf-8 -*-
"""The tax identifier must reach the document the customer actually receives.

Ethiopian law identifies a taxpayer by TIN, and this module stores it in
``l10n_et_tin`` because Ethiopia has a TIN *and* a separate VAT registration
number, which one core ``vat`` field cannot hold. The cost of that decision, until
now, was that the framework printed neither: every core template guards its tax-ID
line with ``t-if="company.vat"`` or ``t-if="partner_id.vat"`` — the shared external
layout does it in 17 places, and so do the invoice, the quotation and the POS
receipt. With ``vat`` empty, none of them printed anything.

So the fix is the FIELD, not one report: ``vat`` is populated from
``l10n_et_tin``. See ``docs/design-tin-identifier.md``.

WHY THIS GUARD READS THE SENT PDF'S BYTES
-----------------------------------------
Asserting on the template proves the markup exists; asserting on the field proves
a value was stored. Neither proves the customer received it. This guard sends the
invoice through the wizard a user actually clicks, captures the message at the
SMTP boundary, and extracts the text of the attached PDF.

AND WHY IT ASSERTS THE RENDERER FIRST
-------------------------------------
Odoo splits a report into ``bodies, res_ids, header, footer, ...`` and hands the
header to wkhtmltopdf as ``--header-html``. An UNPATCHED-Qt wkhtmltopdf ignores
it, so the whole letterhead — where the seller's identifier lives — is silently
absent from the PDF. A guard run on such a build asserts on bytes that cannot
contain the answer: it cannot fail, which makes it decoration rather than a guard.
That is defect register rule 2, and it is recorded there as a worked example
because it already fooled one careful measurement.

So this test FAILS LOUDLY on an unpatched renderer. It does not skip: a skip is
silent, and silence is the thing the rule is about.
"""

import io
from unittest.mock import patch

from odoo.addons.base.models.ir_actions_report import _wkhtml
from odoo.addons.base.models.ir_mail_server import IrMail_Server
from odoo.tests import tagged
from odoo.tools.pdf import PdfReader

from .common import L10nEtBaseCommon

COMPANY_TIN = "0088776655"
CUSTOMER_TIN = "0022334455"


@tagged("post_install", "-at_install")
class TestTinOnDocuments(L10nEtBaseCommon):
    """The TIN must be in the bytes the customer receives."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.partner_id.l10n_et_tin = COMPANY_TIN
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Mebrat Construction PLC",
                "is_company": True,
                "l10n_et_tin": CUSTOMER_TIN,
                "email": "ap@mebrat-construction.example.et",
            }
        )

    # ---- the guard -----------------------------------------------------

    def _assert_renderer_can_render_headers(self):
        """Refuse to report success on a renderer that cannot draw the header."""
        wkhtml = _wkhtml()
        self.assertTrue(
            wkhtml.is_patched_qt,
            "wkhtmltopdf %r is not a patched-Qt build, so it silently DROPS the "
            "report header from every PDF — including the letterhead carrying the "
            "seller's TIN. This guard would pass on the half it cannot see, which "
            "is defect register rule 2. Install wkhtmltox 0.12.6.1-3 (the build "
            "the odoo:19.0 image ships) and re-run." % (wkhtml.version,),
        )

    def _send_and_capture_pdf_text(self, invoice):
        """Send the invoice the way a user does; return the attached PDF's text.

        Captured at the SMTP boundary rather than read off the record, so what is
        asserted is what left the system.
        """
        captured = []

        class _FakeSMTP:
            def quit(self):
                pass

            def close(self):
                pass

        def _fake_connect(self, *args, **kwargs):
            return _FakeSMTP()

        def _fake_send(self, message, *args, **kwargs):
            captured.append(message)
            return "<captured@sapian.test>"

        invoice.partner_id.email = invoice.partner_id.email or "ap@example.et"
        # Point wkhtmltopdf's asset fetches at a closed port. It renders the same
        # text either way, and the alternative is a real HTTP round-trip served by
        # the very process that is holding this test's transaction — which
        # deadlocked until the run was killed at 15 minutes. Styling is irrelevant
        # to a text assertion; the identifier is in the markup, not the CSS.
        self.env["ir.config_parameter"].sudo().set_param("report.url", "http://127.0.0.1:1")
        self.addCleanup(self.env["ir.config_parameter"].sudo().set_param, "report.url", False)
        # `IrMail_Server._disable_send()` returns True whenever a test is running,
        # so `mail.mail._send` returns before building a single message. Without
        # lifting it this guard captures nothing and reports the TIN missing when
        # in truth nothing was sent — which is exactly what happened on the first
        # red run, and is why the message COUNT is asserted below rather than
        # assumed.
        with (
            patch.object(IrMail_Server, "_disable_send", classmethod(lambda cls: False)),
            patch.object(IrMail_Server, "send_email", _fake_send),
            patch.object(IrMail_Server, "_connect__", _fake_connect),
        ):
            # `force_report_rendering` is load-bearing: without it
            # `_render_qweb_pdf` returns HTML during tests
            # (ir_actions_report.py:1027), so the attachment named `.pdf` is an
            # HTML document. It still CONTAINS both TINs, so every assertion
            # below would pass while proving nothing about a PDF — rule 2 again,
            # caught only by asserting the %PDF- magic bytes.
            wizard = (
                self.env["account.move.send.wizard"]
                .with_context(
                    active_model="account.move",
                    active_ids=invoice.ids,
                    force_report_rendering=True,
                )
                .create({"move_id": invoice.id})
            )
            wizard.action_send_and_print()
            self.env["mail.mail"].sudo().search([]).send()

        self.assertEqual(
            len(captured),
            1,
            "Expected exactly one message at the SMTP boundary; got %d. Nothing "
            "was sent, so nothing can be asserted." % len(captured),
        )
        pdfs = []
        for part in captured[0].walk():
            filename = part.get_filename()
            if filename and filename.lower().endswith(".pdf"):
                pdfs.append(part.get_payload(decode=True) or b"")
        self.assertEqual(
            len(pdfs), 1, "Expected one PDF attachment on the sent mail, got %d." % len(pdfs)
        )
        self.assertTrue(
            pdfs[0].startswith(b"%PDF-"),
            "The attachment named .pdf is not a PDF: %d bytes starting %r. A "
            "placeholder or an error page here would make every assertion below "
            "meaningless." % (len(pdfs[0]), pdfs[0][:32]),
        )
        text = "".join(
            page.extract_text() or "" for page in PdfReader(io.BytesIO(pdfs[0])).pages
        )
        return " ".join(text.split()), len(pdfs[0])

    def _post_invoice(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_date": "2026-08-05",
                "company_id": self.company.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_goods.id,
                            "quantity": 1,
                            "price_unit": 1000.0,
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def test_sent_invoice_pdf_carries_both_tins(self):
        """THE guard: both identifiers must be in the bytes that were sent."""
        self._assert_renderer_can_render_headers()
        invoice = self._post_invoice()
        text, size = self._send_and_capture_pdf_text(invoice)
        self.assertIn(
            COMPANY_TIN,
            text,
            "The SELLER's TIN %s is not in the %d-byte PDF the customer received. "
            "An invoice without the supplier's tax identifier is not a valid "
            "Ethiopian VAT invoice." % (COMPANY_TIN, size),
        )
        self.assertIn(
            CUSTOMER_TIN,
            text,
            "The BUYER's TIN %s is not in the %d-byte PDF the customer received."
            % (CUSTOMER_TIN, size),
        )

    # ---- the mechanism behind it ---------------------------------------

    def test_tin_populates_core_vat(self):
        """`vat` is what every core template reads, so the TIN must reach it."""
        partner = self.env["res.partner"].create(
            {"name": "Fresh Supplier PLC", "is_company": True, "l10n_et_tin": "0011223344"}
        )
        self.assertEqual(partner.vat, "0011223344")

    def test_tin_written_later_still_populates_vat(self):
        """A TIN typed after the partner exists must sync too."""
        partner = self.env["res.partner"].create({"name": "Later TIN PLC", "is_company": True})
        self.assertFalse(partner.vat)
        partner.l10n_et_tin = "0055667788"
        self.assertEqual(partner.vat, "0055667788")

    def test_an_existing_vat_is_never_overwritten(self):
        """This populates an empty field; it does not overrule the client."""
        partner = self.env["res.partner"].create(
            {"name": "Has Own VAT PLC", "is_company": True, "vat": "CLIENT-CHOSEN-1"}
        )
        partner.l10n_et_tin = "0099887766"
        self.assertEqual(
            partner.vat,
            "CLIENT-CHOSEN-1",
            "The sync overwrote an identifier somebody had typed deliberately.",
        )

    def test_backfill_moves_only_empty_vat_and_is_idempotent(self):
        """Existing tenants: a template change never reaches them on upgrade."""
        blank = self.env["res.partner"].create({"name": "Backfill Me PLC", "is_company": True})
        self.env.cr.execute(
            "UPDATE res_partner SET l10n_et_tin = %s, vat = NULL WHERE id = %s",
            ("0012345678", blank.id),
        )
        blank.invalidate_recordset()
        self.assertFalse(blank.vat, "Fixture guard: vat must start empty.")

        moved = self.env["res.partner"]._l10n_et_backfill_vat_from_tin()
        self.assertIn(blank, moved, "The backfill reported no work on a partner needing it.")
        blank.invalidate_recordset()
        self.assertEqual(blank.vat, "0012345678")

        again = self.env["res.partner"]._l10n_et_backfill_vat_from_tin()
        self.assertNotIn(blank, again, "The backfill is not idempotent.")

    def test_ethiopia_labels_the_identifier_tin_not_vat(self):
        """Otherwise every document says VAT where Ethiopia says TIN."""
        self.assertEqual(self.env.ref("base.et").vat_label, "TIN")
