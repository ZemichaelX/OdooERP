# -*- coding: utf-8 -*-
"""One test that produces an actual PDF file, not a rendered HTML string.

WHY THIS IS SEPARATE, AND WHY IT IS AN HttpCase
-----------------------------------------------
Under `--test-enable` Odoo short-circuits `_render_qweb_pdf` to
`_render_qweb_html` (ir_actions_report.py:1027) so that suites do not need
wkhtmltopdf. Two consequences, both found the hard way:

  * asserting `%PDF` on the result of the ordinary call asserts the magic bytes
    of the FALLBACK, and fails on a perfectly good PDF pipeline;
  * passing `force_report_rendering` inside a plain TransactionCase makes
    wkhtmltopdf fetch the report's assets over HTTP from a server that is not
    running, and the test HANGS rather than failing. It ran for ten minutes
    before it was killed.

So the real render lives here, in an `HttpCase`, which has a live server for
wkhtmltopdf to fetch from, with `web.base.url` pointed at it.

Everything about the CONTENT of the report — both calendars, the setting that
flips them, the display format — is asserted against rendered HTML in
`test_invoice_dates.py`, which is fast. This file asserts one thing the HTML
cannot: that the document actually prints.
"""

from datetime import date

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestL10nEtInvoicePdf(HttpCase):
    def test_the_invoice_prints_and_the_pdf_is_real(self):
        self.env["ir.config_parameter"].sudo().set_param("web.base.url", self.base_url())
        company = self.env.company
        company.l10n_et_report_calendar = "both"
        company.l10n_et_date_format = "latin"

        partner = self.env["res.partner"].create({"name": "Selam Wholesale PLC"})
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "invoice_date": date(2025, 7, 8),
                "invoice_line_ids": [
                    (0, 0, {"name": "Consultancy", "quantity": 1, "price_unit": 1000.0})
                ],
            }
        )
        move.invoice_date_due = date(2025, 8, 7)
        move.action_post()
        self.assertEqual(move.l10n_et_invoice_date, "2017-11-01")

        pdf, report_type = (
            self.env["ir.actions.report"]
            .with_context(force_report_rendering=True)
            ._render_qweb_pdf("account.report_invoice", move.ids)
        )
        self.assertEqual(report_type, "pdf", "Odoo fell back to HTML")
        self.assertTrue(pdf.startswith(b"%PDF"), "not a PDF")
        # A wkhtmltopdf that failed early still emits a valid, nearly empty
        # document, so assert a size a real invoice cannot be under.
        self.assertGreater(len(pdf), 5000, "a PDF this small printed nothing")
