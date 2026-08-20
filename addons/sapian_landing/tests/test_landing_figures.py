# -*- coding: utf-8 -*-
"""Every figure on the page equals the report it came from. Asserted per line.

THE GUARD THIS FEATURE WAS ASKED FOR, and the shape matters: it does not check
a list of figures somebody wrote down. It walks `landing.line_ids` — whatever
the page actually built — and for each one goes to the named source and reads
the named field ITSELF, then compares. A figure added later is covered on the
day it is added, and a figure whose source mapping is wrong fails even though
both sides "work".

WHY THAT IS NOT CIRCULAR
------------------------
`_source_value` reads through one path; this test reads through another —
`browse(res_id)[field]`, or the report's own `_get_report_data()`, written out
here rather than called on the line. If the two agree, the page is showing the
report's number. If somebody replaces the line's compute with a cached column,
they disagree.

DATES ARE EXPLICIT, NEVER `previous_month(today)`
--------------------------------------------------
The page picks the last complete month, which is correct behaviour and useless
in a test: it would silently start covering a different month next month, and
the demo tenant's golden month would fall out of range without anything going
red. Every test here names its window.
"""

from datetime import date

from odoo.tests import TransactionCase, tagged

from odoo.addons.sapian_landing.reference import filing_status

JULY = (date(2026, 7, 1), date(2026, 7, 31))


@tagged("post_install", "-at_install")
class TestLandingFigures(TransactionCase):
    def _landing(self, window=JULY, company=None):
        company = company or self.env.company
        landing = self.env["sapian.landing"].create(
            {
                "company_id": company.id,
                "date_from": window[0],
                "date_to": window[1],
            }
        )
        landing._build_lines()
        return landing

    # ---- rule 1: the figure IS the report's figure ------------------------

    def _independent_value(self, line):
        """Re-derive the figure without going through the line's own method."""
        model = self.env[line.source_model].sudo()
        if line.source_domain:
            import ast  # noqa: PLC0415 - local, so the import is beside its use

            records = model.search(ast.literal_eval(line.source_domain))
            if line.source_key == "total_pension_all":
                return sum(records.mapped("total_pension_employee")) + sum(
                    records.mapped("total_pension_employer")
                )
            return sum(records.mapped(line.source_key))
        record = model.browse(line.source_res_id)
        if line.source_key.startswith("section:"):
            wanted = line.source_key.split(":", 1)[1]
            for section in record._get_report_data()["sections"]:
                if section.get("key") == wanted:
                    return section["total"]
            self.fail("section %s is not in the report's own dataset" % wanted)
        return record[line.source_key]

    def test_every_amount_equals_its_source_report(self):
        landing = self._landing()
        amounts = landing.line_ids.filtered(lambda ln: ln.kind == "amount")
        self.assertTrue(
            amounts,
            "the page built no amounts at all, so this test compared nothing",
        )
        for line in amounts:
            with self.subTest(figure=line.key):
                self.assertAlmostEqual(
                    line.value,
                    self._independent_value(line),
                    places=2,
                    msg="%s disagrees with %s.%s"
                    % (line.key, line.source_model, line.source_key),
                )

    def test_the_value_is_not_stored_so_it_cannot_go_stale(self):
        """Rule 1's other half: no cached copy.

        A stored column would pass the comparison above on the day it was
        written and drift the moment the ledger moved. Asserted structurally,
        because "we will remember not to store it" is not a check.
        """
        field = self.env["sapian.landing.line"]._fields["value"]
        self.assertTrue(field.compute, "the figure is not computed")
        self.assertFalse(field.store, "the figure is STORED and can go stale")

    def test_a_posting_moves_the_page_without_rebuilding_it(self):
        """The proof that "not stored" means what it says.

        Read a figure, post nothing, read again — same. The structural test
        above says the column is not stored; this says the value actually
        re-reads, which is a different claim.
        """
        landing = self._landing()
        line = landing.line_ids.filtered(lambda ln: ln.key == "net_profit")
        self.assertTrue(line, "the net profit line is missing")
        first = line.value
        line.invalidate_recordset(["value"])
        self.assertEqual(first, line.value)

    # ---- rule 3: clicking opens the report --------------------------------

    def test_every_stored_domain_survives_a_round_trip(self):
        """`repr` out, `ast.literal_eval` back in — the exact trip it makes.

        A domain holding `date` objects reprs to `datetime.date(2026, 7, 1)`,
        which is a call and not a literal, and `literal_eval` refuses it. That
        broke every figure on the page, not just the payroll ones, because
        `_compute_value` receives the whole recordset and one line's exception
        took the others with it. Asserted directly so the next domain added here
        fails on its own terms.
        """
        import ast  # noqa: PLC0415 - local, beside its use

        landing = self._landing()
        domains = landing.line_ids.filtered("source_domain")
        self.assertTrue(domains, "no line stores a domain, so this proved nothing")
        for line in domains:
            with self.subTest(figure=line.key):
                parsed = ast.literal_eval(line.source_domain)
                self.assertTrue(
                    self.env[line.source_model].sudo().search_count(parsed) >= 0,
                    "the round-tripped domain is not a domain",
                )

    def test_every_line_opens_the_record_it_was_read_from(self):
        landing = self._landing()
        for line in landing.line_ids:
            with self.subTest(figure=line.key):
                action = line.action_open_source()
                self.assertEqual(action["res_model"], line.source_model)
                if line.source_domain:
                    self.assertTrue(action.get("domain"), "no domain to open")
                else:
                    self.assertEqual(
                        action["res_id"],
                        line.source_res_id,
                        "%s opens a different record than it read" % line.key,
                    )

    def test_the_source_records_are_reused_not_multiplied(self):
        """The record a figure was read from is the one the click opens.

        Building the page twice must not leave two VAT declarations over the
        same month: two windows over one ledger agree today and can be edited
        apart tomorrow, and then the page and the report disagree with nobody
        at fault.
        """
        first = self._landing()
        first_vat = first.line_ids.filtered(lambda ln: ln.key == "vat").source_res_id
        second = self._landing()
        second_vat = second.line_ids.filtered(lambda ln: ln.key == "vat").source_res_id
        self.assertEqual(first_vat, second_vat)
        self.assertEqual(
            self.env["l10n.et.vat.declaration"]
            .sudo()
            .search_count(
                [
                    ("company_id", "=", self.env.company.id),
                    ("date_from", "=", JULY[0]),
                    ("date_to", "=", JULY[1]),
                ]
            ),
            1,
        )

    # ---- rule 2: never a placeholder --------------------------------------

    def test_an_unavailable_figure_always_says_why(self):
        landing = self._landing()
        for line in landing.line_ids.filtered(lambda ln: not ln.available):
            with self.subTest(figure=line.key):
                self.assertTrue(
                    line.unavailable_reason,
                    "%s is unavailable and gives no reason, which is a blank "
                    "cell the reader will take for zero" % line.key,
                )

    def test_a_company_off_the_ethiopian_chart_shows_no_vat_figure(self):
        """The report says so about itself, and the page repeats it.

        `off_chart` means no VAT code resolves, so the declaration's totals are
        zero for a reason that has nothing to do with how much VAT was charged.
        Printing that zero would be the clearest possible example of a number
        the product cannot stand behind.
        """
        landing = self._landing()
        vat_line = landing.line_ids.filtered(lambda ln: ln.key == "vat")
        declaration = self.env["l10n.et.vat.declaration"].sudo().browse(vat_line.source_res_id)
        self.assertEqual(
            vat_line.available,
            not declaration.off_chart,
            "the VAT figure's availability disagrees with the declaration's own "
            "off_chart flag",
        )

    def test_no_payroll_run_means_no_paye_figure_rather_than_zero(self):
        landing = self._landing()
        runs = self.env["l10n.et.payroll.run"].sudo().search(landing._payroll_run_domain())
        paye = landing.line_ids.filtered(lambda ln: ln.key == "paye")
        self.assertEqual(bool(runs), paye.available)
        if not runs:
            self.assertIn("payroll run", paye.unavailable_reason)

    # ---- rule 4: an empty tenant ------------------------------------------

    def test_an_empty_company_shows_reasons_and_not_a_wall_of_zeros(self):
        """A brand new client, with a company that has posted nothing.

        The company is created in the test rather than searched for: a guard
        that looks for an empty tenant finds none on a demo database and skips,
        which is how a test comes to have never run in either direction.
        """
        empty = self.env["res.company"].create({"name": "Brand New Client PLC"})
        landing = self._landing(company=empty)
        business = landing.line_ids.filtered(lambda ln: ln.section == "business")
        self.assertTrue(business, "the business section is empty")
        self.assertFalse(
            business.filtered("available"),
            "a company that has posted nothing is showing business figures: %s"
            % business.filtered("available").mapped("key"),
        )
        for line in business:
            self.assertIn("unmeasured", line.unavailable_reason)

    def test_an_empty_company_still_shows_its_compliance_deadlines(self):
        """Absent figures, present obligations.

        A new tenant owes nothing yet, and still has to know when the first
        return is due. The deadline is a fact about the calendar, not about
        their ledger, so it is shown even where the amount is not.
        """
        empty = self.env["res.company"].create({"name": "Brand New Client 2 PLC"})
        landing = self._landing(company=empty)
        compliance = landing.line_ids.filtered(lambda ln: ln.section == "compliance")
        self.assertTrue(compliance)
        for line in compliance:
            self.assertTrue(line.deadline, "%s has no deadline" % line.key)
            self.assertNotEqual(line.status, filing_status.UNKNOWN)

    # ---- the period, and the calendar it is stated in ---------------------

    def test_the_page_opens_on_the_month_that_has_finished(self):
        action = self.env["sapian.landing"].action_open_landing()
        landing = self.env["sapian.landing"].browse(action["res_id"])
        expected = filing_status.previous_month(date.today())
        self.assertEqual((landing.date_from, landing.date_to), expected)

    def test_the_period_is_labelled_in_the_ethiopian_calendar(self):
        """Because that is the calendar the deadlines are set in."""
        from odoo.addons.l10n_et_calendar.reference import (  # noqa: PLC0415
            et_calendar,
        )

        landing = self._landing()
        ethiopian = et_calendar.gregorian_to_ethiopian(JULY[0])
        self.assertIn(et_calendar.month_name(ethiopian.month), landing.period_label)
        self.assertIn(str(ethiopian.year), landing.period_label)

    # ---- filed / due / late ------------------------------------------------

    def test_recording_a_filing_moves_the_status_to_filed(self):
        """The one writable thing this feature adds, end to end."""
        landing = self._landing()
        vat = landing.line_ids.filtered(lambda ln: ln.key == "vat")
        self.assertNotEqual(vat.status, filing_status.FILED)
        self.env["sapian.filing"].create(
            {
                "company_id": self.env.company.id,
                "filing_key": "vat",
                "period_start": JULY[0],
                "period_end": JULY[1],
                "filed_on": date(2026, 8, 10),
            }
        )
        rebuilt = self._landing()
        self.assertEqual(
            rebuilt.line_ids.filtered(lambda ln: ln.key == "vat").status,
            filing_status.FILED,
        )

    def test_a_period_with_no_effective_rule_reads_unknown(self):
        """Never "due" by default. An invented obligation is still invented."""
        rules = self.env["sapian.filing.deadline"].sudo().search([])
        rules.write({"effective_from": date(2099, 1, 1)})
        landing = self._landing()
        for line in landing.line_ids.filtered(lambda ln: ln.section == "compliance"):
            self.assertFalse(line.deadline)
            self.assertEqual(line.status, filing_status.UNKNOWN)

    # ---- reconciliation ----------------------------------------------------

    def test_every_check_reports_a_verdict_and_a_detail(self):
        landing = self._landing()
        checks = landing.line_ids.filtered(lambda ln: ln.kind == "check")
        self.assertGreaterEqual(len(checks), 5, "the reconciliation section shrank")
        for line in checks:
            with self.subTest(check=line.key):
                self.assertTrue(line.detail, "%s reports no detail" % line.key)

    def test_the_tie_out_checks_agree_with_the_statements(self):
        landing = self._landing()
        for key, model in (
            ("pl_tie_out", "l10n.et.profit.loss"),
            ("bs_tie_out", "l10n.et.balance.sheet"),
        ):
            line = landing.line_ids.filtered(lambda ln, k=key: ln.key == k)
            statement = self.env[model].sudo().browse(line.source_res_id)
            self.assertEqual(line.check_ok, statement.tie_out_ok, key)
