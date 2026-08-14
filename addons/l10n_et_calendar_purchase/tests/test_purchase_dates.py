# -*- coding: utf-8 -*-
"""The purchase bridge: two Datetime sources, on screen and on the PDF.

The difference from the invoice bridge is that both source fields are
Datetimes. Odoo stores those as naive UTC and Ethiopia is UTC+3, so a naive
conversion is wrong by a day for every order entered after 21:00 UTC. That is
tested here on a real purchase order as well as in the mixin's own suite,
because it is the failure mode a demo would actually show.
"""

from datetime import date, datetime

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestL10nEtCalendarPurchase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.l10n_et_date_format = "latin"
        cls.company.l10n_et_report_calendar = "both"
        cls.vendor = cls.env["res.partner"].create({"name": "Addis Supplies PLC"})
        cls.product = cls.env["product.product"].create(
            {"name": "Printer paper", "purchase_ok": True}
        )

    def _order(self, ordered=datetime(2025, 7, 8, 9, 0), planned=datetime(2025, 8, 7, 9, 0)):
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "date_order": ordered,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 10,
                            "price_unit": 100.0,
                            "date_planned": planned,
                        },
                    )
                ],
            }
        )
        order.date_planned = planned
        return order

    # ---- the mirror on a real order -----------------------------------------

    def test_both_dates_mirror(self):
        order = self._order()
        self.assertEqual(order.l10n_et_date_order, "2017-11-01", "Hamle 1, 2017")
        self.assertEqual(order.l10n_et_date_planned, "2017-12-01", "Nehase 1, 2017")

    def test_an_evening_order_is_dated_by_the_day_it_was_in_ethiopia(self):
        """22:00 UTC on 7 July 2025 is 01:00 on 8 July in Addis Ababa.

        A naive `.date()` would file this order under Sene 30 — one day early,
        on a document a vendor and the Ministry of Revenue both read.
        """
        order = self._order(ordered=datetime(2025, 7, 7, 22, 0))
        self.assertEqual(order.l10n_et_date_order, "2017-11-01", "Hamle 1, not Sene 30")
        self.assertEqual(order.l10n_et_display("date_order"), "Hamle 1, 2017")

    def test_the_same_evening_an_hour_earlier_is_the_previous_day(self):
        """The other side of the boundary, so the test above is not passing by
        accident on a converter that returns Hamle 1 for everything."""
        order = self._order(ordered=datetime(2025, 7, 7, 20, 0))
        self.assertEqual(order.l10n_et_date_order, "2017-10-30", "Sene 30, 2017")

    def test_the_values_are_in_the_columns(self):
        order = self._order()
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT l10n_et_date_order, l10n_et_date_planned "
            "FROM purchase_order WHERE id = %s",
            (order.id,),
        )
        self.assertEqual(self.env.cr.fetchone(), ("2017-11-01", "2017-12-01"))

    def test_a_month_of_orders_can_be_filtered_in_one_domain(self):
        inside = self._order(ordered=datetime(2025, 7, 8, 9, 0))
        outside = self._order(ordered=datetime(2025, 7, 7, 9, 0))
        found = self.env["purchase.order"].search(
            [
                ("id", "in", (inside | outside).ids),
                ("l10n_et_date_order", ">=", "2017-11-01"),
                ("l10n_et_date_order", "<=", "2017-11-30"),
            ]
        )
        self.assertEqual(found, inside)

    # ---- on screen ----------------------------------------------------------

    def test_the_fields_are_in_the_form_the_user_opens(self):
        arch = self.env["purchase.order"].get_view(
            self.env.ref("purchase.purchase_order_form").id, "form"
        )["arch"]
        self.assertIn("l10n_et_date_order", arch)
        self.assertIn("l10n_et_date_planned", arch)

    # ---- on the rendered PDF ------------------------------------------------

    def _render(self, order):
        html = self.env["ir.actions.report"]._render_qweb_html(
            "purchase.action_report_purchase_order", order.ids
        )[0]
        return html.decode() if isinstance(html, bytes) else html

    def test_the_pdf_carries_both_calendars_by_default(self):
        order = self._order()
        html = self._render(order)
        self.assertIn("Hamle 1, 2017", html, "the Ethiopian order deadline")
        self.assertIn("Nehase 1, 2017", html, "the Ethiopian expected arrival")
        self.assertIn("07/08/2025", html, "and the Gregorian deadline")

    def test_the_setting_flips_which_calendar_prints(self):
        order = self._order()

        self.company.l10n_et_report_calendar = "ethiopian"
        html = self._render(order)
        self.assertIn("Hamle 1, 2017", html)
        self.assertNotIn("07/08/2025", html, "Gregorian must be gone")

        self.company.l10n_et_report_calendar = "gregorian"
        html = self._render(order)
        self.assertIn("07/08/2025", html)
        self.assertNotIn("Hamle 1, 2017", html, "Ethiopian must be gone")

    def test_expected_arrival_still_prints_once_the_order_is_confirmed(self):
        """Odoo swaps the Order Deadline block for a Confirmation Date on a
        confirmed order, and date_approve is not one of the two fields in
        scope. Expected Arrival prints in both states, and this records which
        of the two survives confirmation so the gap is documented rather than
        discovered on camera."""
        order = self._order()
        order.button_confirm()
        html = self._render(order)
        self.assertIn("Nehase 1, 2017", html, "expected arrival, in Ethiopian")

    # ---- the module itself --------------------------------------------------

    def test_the_dependency_closure_carries_nothing_unexpected(self):
        Module = self.env["ir.module.module"]
        seen, frontier = set(), {"l10n_et_calendar_purchase"}
        while frontier:
            found = Module.search([("name", "in", list(frontier))])
            seen |= frontier
            frontier = set(found.dependencies_id.mapped("name")) - seen
        ours = {n for n in seen if n.startswith(("sapian_", "l10n_et_"))}
        self.assertEqual(
            ours,
            {"l10n_et_calendar_purchase", "l10n_et_calendar"},
            "a bridge must bridge exactly two things",
        )
        self.assertIn("purchase", seen)

    def test_it_is_an_auto_install_bridge(self):
        module = self.env["ir.module.module"].search(
            [("name", "=", "l10n_et_calendar_purchase")], limit=1
        )
        self.assertTrue(module.auto_install, "it must appear on its own")
        self.assertEqual(
            set(module.dependencies_id.mapped("name")), {"l10n_et_calendar", "purchase"}
        )

    def test_a_date_field_and_a_datetime_field_agree_on_the_same_day(self):
        """Cross-check between the two bridges: an invoice dated 8 July and an
        order placed at 09:00 on 8 July must carry the same Ethiopian date.
        Skipped when the invoice bridge is absent, which is itself the correct
        behaviour for an auto-install bridge."""
        if "l10n_et_invoice_date" not in self.env["account.move"]._fields:
            self.skipTest("l10n_et_calendar_account is not installed")
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": date(2025, 7, 8),
            }
        )
        order = self._order(ordered=datetime(2025, 7, 8, 9, 0))
        self.assertEqual(move.l10n_et_invoice_date, order.l10n_et_date_order)
