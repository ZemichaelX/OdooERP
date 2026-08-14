# -*- coding: utf-8 -*-
"""The invoice bridge: on screen, in the database, and on the rendered PDF.

The mixin's own behaviour is tested in l10n_et_calendar. What is tested here is
what the bridge adds: that the two dates on a real customer invoice mirror
correctly, that the fields actually appear in the form the user opens, and that
the company setting really changes what comes out of the printer — asserted
against rendered HTML, not against the template source, because a template that
inherits nothing still looks correct in a diff.
"""

from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestL10nEtCalendarInvoice(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.l10n_et_date_format = "latin"
        cls.company.l10n_et_report_calendar = "both"
        cls.partner = cls.env["res.partner"].create({"name": "Selam Wholesale PLC"})

    def _invoice(self, invoice_date=date(2025, 7, 8), due=date(2025, 8, 7)):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": invoice_date,
                "invoice_date_due": due,
                "invoice_line_ids": [
                    (0, 0, {"name": "Consultancy", "quantity": 1, "price_unit": 1000.0})
                ],
            }
        )
        # the due date is computed from payment terms unless it is written back
        move.invoice_date_due = due
        return move

    # ---- the mirror on a real invoice ---------------------------------------

    def test_both_dates_mirror(self):
        move = self._invoice()
        self.assertEqual(move.l10n_et_invoice_date, "2017-11-01", "Hamle 1, 2017")
        self.assertEqual(move.l10n_et_invoice_date_due, "2017-12-01", "Nehase 1, 2017")

    def test_moving_the_due_date_leaves_the_invoice_date_alone(self):
        move = self._invoice()
        move.invoice_date_due = date(2025, 9, 11)
        self.assertEqual(move.l10n_et_invoice_date_due, "2018-01-01", "Meskerem 1, 2018")
        self.assertEqual(move.l10n_et_invoice_date, "2017-11-01")

    def test_the_values_are_in_the_columns(self):
        move = self._invoice()
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT l10n_et_invoice_date, l10n_et_invoice_date_due "
            "FROM account_move WHERE id = %s",
            (move.id,),
        )
        self.assertEqual(self.env.cr.fetchone(), ("2017-11-01", "2017-12-01"))

    def test_a_month_of_invoices_can_be_filtered_in_one_domain(self):
        """Hamle 2017 is 8 July – 6 August 2025. It is not a Gregorian month
        and cannot be expressed as one, which is the whole point of storing
        the Ethiopian date rather than computing it on the way out."""
        inside = self._invoice(date(2025, 7, 8)) | self._invoice(date(2025, 8, 6))
        outside = self._invoice(date(2025, 7, 7)) | self._invoice(date(2025, 8, 7))
        found = self.env["account.move"].search(
            [
                ("id", "in", (inside | outside).ids),
                ("l10n_et_invoice_date", ">=", "2017-11-01"),
                ("l10n_et_invoice_date", "<=", "2017-11-30"),
            ]
        )
        self.assertEqual(found, inside)

    # ---- on screen ----------------------------------------------------------

    def test_the_fields_are_in_the_form_the_user_opens(self):
        """`get_view` returns the arch after inheritance is applied, so this
        fails if the xpath silently stopped matching — which is what happens
        when Odoo moves an element in a version upgrade."""
        arch = self.env["account.move"].get_view(
            self.env.ref("account.view_move_form").id, "form"
        )["arch"]
        self.assertIn("l10n_et_invoice_date", arch)
        self.assertIn("l10n_et_invoice_date_due", arch)

    # ---- on the rendered PDF ------------------------------------------------

    def _render(self, move):
        html = self.env["ir.actions.report"]._render_qweb_html(
            "account.report_invoice", move.ids
        )[0]
        return html.decode() if isinstance(html, bytes) else html

    def test_the_pdf_carries_both_calendars_by_default(self):
        move = self._invoice()
        move.action_post()
        html = self._render(move)
        self.assertIn("Hamle 1, 2017", html, "the Ethiopian invoice date")
        self.assertIn("Nehase 1, 2017", html, "the Ethiopian due date")
        self.assertIn("07/08/2025", html, "and the Gregorian one it came from")

    def test_the_setting_flips_which_calendar_prints(self):
        """The gate, both ways. A setting that only ever ADDS a line is not a
        choice of calendar, so the Gregorian date must really disappear."""
        move = self._invoice()
        move.action_post()

        self.company.l10n_et_report_calendar = "ethiopian"
        html = self._render(move)
        self.assertIn("Hamle 1, 2017", html)
        self.assertNotIn("07/08/2025", html, "Gregorian must be gone")

        self.company.l10n_et_report_calendar = "gregorian"
        html = self._render(move)
        self.assertIn("07/08/2025", html)
        self.assertNotIn("Hamle 1, 2017", html, "Ethiopian must be gone")

    def test_the_pdf_honours_the_display_format(self):
        move = self._invoice()
        move.action_post()
        self.company.l10n_et_date_format = "amharic"
        self.assertIn("ሐምሌ 1 ቀን 2017 ዓ.ም.", self._render(move))
        self.company.l10n_et_date_format = "numeric"
        self.assertIn("01/11/2017", self._render(move))

    # ---- the module itself --------------------------------------------------

    def test_the_dependency_closure_carries_nothing_unexpected(self):
        """The used-but-undeclared failure has bitten this project three times.
        Assert the whole closure, not just the direct list."""
        Module = self.env["ir.module.module"]
        seen, frontier = set(), {"l10n_et_calendar_account"}
        while frontier:
            found = Module.search([("name", "in", list(frontier))])
            seen |= frontier
            frontier = set(found.dependencies_id.mapped("name")) - seen
        ours = {n for n in seen if n.startswith(("sapian_", "l10n_et_"))}
        self.assertEqual(
            ours,
            {"l10n_et_calendar_account", "l10n_et_calendar"},
            "a bridge must bridge exactly two things",
        )
        self.assertIn("account", seen)
        self.assertNotIn("purchase", seen, "the invoice bridge must not need purchase")

    def test_it_is_an_auto_install_bridge(self):
        module = self.env["ir.module.module"].search(
            [("name", "=", "l10n_et_calendar_account")], limit=1
        )
        self.assertTrue(module.auto_install, "it must appear on its own")
        self.assertEqual(
            set(module.dependencies_id.mapped("name")), {"l10n_et_calendar", "account"}
        )
