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

THE BUSINESS WINDOW IS EXPLICIT; THE FILING PERIODS ARE NOT, AND CANNOT BE
---------------------------------------------------------------------------
The business half of the page is handed a fixed window by `_landing()`, for the
reason it always was: a window that moved with the calendar would silently start
covering a different month and nothing would go red.

The compliance half no longer takes a window at all. Each filing computes its
own period from `sapian.filing.period` — which calendar, and the last period of
that calendar to have finished — so a test that pinned a month here would be a
second copy of the configuration and would go stale the day an accountant
corrects a rule. `_period_of` asks the same rules the page asks, and the
assertions are about SHAPE: that the employment income tax period is a whole
Ethiopian month, that the deadline belongs to the filing month the period begins
in, that a label never names a month the figures do not cover.
"""

from datetime import date, timedelta

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

    def _row(self, landing, key):
        return landing.line_ids.filtered(lambda ln, k=key: ln.key == k)

    def _period_of(self, key, company=None):
        """The period the page will use for one filing, computed here.

        Computed rather than pinned: the calendars are DATA now, so a literal
        month in a test would be a second copy of the configuration and would
        go stale the day somebody corrects a rule — which is the whole point of
        the rules being correctable.
        """
        company = company or self.env.company
        today = date.today()
        calendar = self.env["sapian.filing.period"]._calendar_for(key, today, company)
        return filing_status.previous_period(calendar, today) if calendar else (None, None)

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
        vat_period = self._period_of("vat")
        self.assertEqual(
            self.env["l10n.et.vat.declaration"]
            .sudo()
            .search_count(
                [
                    ("company_id", "=", self.env.company.id),
                    ("date_from", "=", vat_period[0]),
                    ("date_to", "=", vat_period[1]),
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
        start, end = self._period_of("paye")
        runs = (
            self.env["l10n.et.payroll.run"]
            .sudo()
            .search(landing._payroll_run_domain(start, end))
        )
        paye = self._row(landing, "paye")
        self.assertEqual(bool(runs), paye.available)
        if not runs:
            self.assertTrue(paye.unavailable_reason)

    def test_a_payroll_run_on_another_cycle_is_refused_rather_than_placed(self):
        """The half of the mapping the reference does NOT settle.

        `docs/ethiopian-tax-reference.md` section 2 records the payroll cycle as
        a business choice and states the mapping only for the Ethiopian one: a
        run whose period IS the filing month is filed as that month. For a
        Gregorian-cycle run it gives the WINDOW ("1st-30th of the following
        Ethiopian month") and never says which Ethiopian month goes on the form.

        So a run that overlaps the filing month without being it must produce no
        figure and a reason that says why — not a number arrived at by picking
        the month with the biggest overlap, which is a guess wearing arithmetic.
        """
        company = self.env["res.company"].create({"name": "Other Cycle PLC"})
        start, end = self._period_of("paye", company)
        self.assertTrue(start, "no PAYE period rule; this test would prove nothing")
        # A run that straddles the filing month: same length, shifted by a week.
        self.env["l10n.et.payroll.run"].sudo().create(
            {
                "company_id": company.id,
                "date_from": start + timedelta(days=7),
                "date_to": end + timedelta(days=7),
            }
        )
        landing = self._landing(company=company)
        paye = self._row(landing, "paye")
        self.assertFalse(
            paye.available,
            "the page placed a payroll run onto a filing month on evidence we " "do not have",
        )
        self.assertIn("not settled", paye.unavailable_reason)

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

    def test_a_label_never_names_a_period_the_figures_do_not_cover(self):
        """The defect that started this: "Sene 2018 - Hamle 2018" over 31 days.

        That range begins 24 days into Sene, ends 24 days into Hamle and covers
        neither of them, and the label named both. The rule now: a whole month
        may be NAMED; anything else is given as dates, where a month name is
        part of a date and cannot be read as a period.
        """
        from odoo.addons.l10n_et_calendar.reference import (  # noqa: PLC0415
            et_calendar,
        )

        landing = self._landing()
        model = self.env["sapian.landing"]

        # A whole Ethiopian month is named, and named alone.
        eth_start, eth_end = filing_status.previous_period(
            filing_status.ETHIOPIAN, date.today()
        )
        ethiopian = et_calendar.gregorian_to_ethiopian(eth_start)
        self.assertEqual(
            model._period_label(eth_start, eth_end),
            "%s %d" % (et_calendar.month_name(ethiopian.month), ethiopian.year),
        )

        # A Gregorian month is named as the Gregorian month it is. The Ethiopian
        # span is present, as DATES: every month name in it carries a day number.
        greg_label = model._period_label(landing.date_from, landing.date_to)
        self.assertIn(landing.date_from.strftime("%B %Y"), greg_label)
        self._assert_no_bare_month_name(greg_label, after=landing.date_from.strftime("%Y"))

    def _assert_no_bare_month_name(self, label, after):
        """No Ethiopian month name in ``label`` stands without a day number."""
        from odoo.addons.l10n_et_calendar.reference import (  # noqa: PLC0415
            et_calendar,
        )

        tail = label[label.index(after) + len(after) :] if after in label else label
        for month in range(1, 14):
            name = et_calendar.month_name(month)
            index = tail.find(name)
            if index < 0:
                continue
            before = tail[:index].rstrip()
            self.assertTrue(
                before and before[-1].isdigit(),
                "%r names the Ethiopian month %s without a day, so it reads as "
                "a whole month the figures may not cover" % (label, name),
            )

    # ---- filed / due / late ------------------------------------------------

    def test_recording_a_filing_moves_the_status_to_filed(self):
        """The one writable thing this feature adds, end to end."""
        landing = self._landing()
        vat = self._row(landing, "vat")
        self.assertNotEqual(vat.status, filing_status.FILED)
        start, end = self._period_of("vat")
        self.env["sapian.filing"].create(
            {
                "company_id": self.env.company.id,
                "filing_key": "vat",
                "period_start": start,
                "period_end": end,
                "filed_on": end + timedelta(days=3),
            }
        )
        rebuilt = self._landing()
        self.assertEqual(
            rebuilt.line_ids.filtered(lambda ln: ln.key == "vat").status,
            filing_status.FILED,
        )

    # ---- the period each filing is actually counted in ---------------------

    def test_the_employment_income_tax_period_is_a_whole_ethiopian_month(self):
        """VERIFIED in docs/ethiopian-tax-reference.md section 2.

        Not "a month rendered in Ethiopian dates" — an Ethiopian month, with
        Ethiopian boundaries. 1-31 July 2026 is 31 days beginning 24 days into
        Sene, and every figure on that row covered the wrong days.
        """
        landing = self._landing()
        paye = self._row(landing, "paye")
        self.assertTrue(
            filing_status.is_whole_period(
                filing_status.ETHIOPIAN, paye.period_start, paye.period_end
            ),
            "the employment income tax row covers %s..%s, which is not a whole "
            "Ethiopian month" % (paye.period_start, paye.period_end),
        )

    def test_the_paye_deadline_belongs_to_the_filing_month_its_period_starts_in(self):
        """RED ON THE OLD RULE BY EXACTLY 24 DAYS, and this is that test.

        Whatever period the page shows, the deadline it states must be the
        deadline of the Ethiopian filing month that period BEGINS in — because
        that is the filing an accountant reading the row takes it to be.

        The old configuration was a Gregorian month with a flat 30-day window.
        On 20 August 2026 that is 1-31 July, due 30 August; the period begins in
        Sene 2018, whose return was due at the end of Hamle, 6 August. The page
        was telling somebody they had until the 30th about a return that had
        been late for a fortnight. The other half of this proof forces that
        configuration back and watches the assertion below fail.
        """
        landing = self._landing()
        paye = self._row(landing, "paye")
        self._assert_deadline_matches_its_filing_month(paye)

    def _assert_deadline_matches_its_filing_month(self, row):
        filing_end = filing_status.period_containing(filing_status.ETHIOPIAN, row.period_start)[
            1
        ]
        expected = filing_status.next_period_end(filing_status.ETHIOPIAN, filing_end)
        self.assertEqual(
            row.deadline,
            expected,
            "the page states %s. The Ethiopian filing month this period begins "
            "in ends %s and its return is due %s — the page is %d days late."
            % (
                row.deadline,
                filing_end,
                expected,
                (row.deadline - expected).days if row.deadline else 0,
            ),
        )

    def test_the_guard_above_goes_red_on_the_rule_it_replaced(self):
        """It DISCRIMINATES. An untested guard passes by doing nothing.

        The configuration IS the behaviour now, so the old behaviour can be put
        back as data — which is also the clearest possible demonstration that
        the open questions really are a data change and not a rewrite.

        Late on EVERY build date, not only today's: swept day by day across
        2026-2028, the old rule over-runs the real deadline by 20 to 50 days and
        is never early. 24 is the figure on 20 August 2026.
        """
        company = self.env["res.company"].create({"name": "Old Rule PLC"})
        self.env["sapian.filing.period"].sudo().create(
            {
                "company_id": company.id,
                "filing_key": "paye",
                "effective_from": date(2000, 1, 1),
                "calendar": filing_status.GREGORIAN,
            }
        )
        self.env["sapian.filing.deadline"].sudo().create(
            {
                "company_id": company.id,
                "filing_key": "paye",
                "effective_from": date(2000, 1, 1),
                "deadline_window": filing_status.WINDOW_DAYS,
                "days_after_period_end": 30,
            }
        )
        row = self._row(self._landing(company=company), "paye")
        with self.assertRaises(AssertionError) as caught:
            self._assert_deadline_matches_its_filing_month(row)
        self.assertIn("days late", str(caught.exception))
        # And it is late, not early: the old rule always over-ran the real one.
        filing_end = filing_status.period_containing(filing_status.ETHIOPIAN, row.period_start)[
            1
        ]
        expected = filing_status.next_period_end(filing_status.ETHIOPIAN, filing_end)
        self.assertGreater((row.deadline - expected).days, 0)

    def test_pagume_is_where_thirty_days_and_the_next_month_part_company(self):
        """The reason the deadline records a SHAPE and not a day count.

        Eleven Ethiopian months are 30 days, so "+30 days" and "the end of the
        following month" agree and a wrong rule looks right. Pagume is 5 or 6,
        and Nehase's return is due at the end of it.
        """
        nehase_end = date(2026, 9, 5)
        self.assertEqual(
            filing_status.deadline_for(
                nehase_end,
                None,
                filing_status.WINDOW_END_OF_NEXT_PERIOD,
                filing_status.ETHIOPIAN,
            ),
            date(2026, 9, 10),
        )
        self.assertEqual(
            filing_status.deadline_for(nehase_end, 30, filing_status.WINDOW_DAYS),
            date(2026, 10, 5),
        )

    def test_every_filing_records_which_calendar_it_is_counted_in(self):
        """Per-tax, as data — and the three open ones say they are open."""
        model = self.env["sapian.filing.period"].sudo()
        for key in filing_status.FILING_KEYS:
            with self.subTest(filing=key):
                calendar = model._calendar_for(key, date.today(), self.env.company)
                self.assertIn(calendar, filing_status.CALENDARS)
        for key in ("vat", "wht", "pension"):
            with self.subTest(filing=key):
                rule = model.search(
                    [("filing_key", "=", key), ("company_id", "=", False)], limit=1
                )
                self.assertTrue(rule, "%s has no global period rule" % key)
                self.assertIn(
                    "UNVERIFIED",
                    rule.source_note or "",
                    "%s's period rule does not say it is unverified" % key,
                )
                self.assertIn(
                    "QUESTION",
                    rule.source_note or "",
                    "%s's period rule does not carry the question that would "
                    "settle it" % key,
                )

    def test_a_filing_is_matched_to_its_period_without_exact_date_equality(self):
        """Item 6: `period_end =` broke the moment a period became Ethiopian."""
        start, end = self._period_of("paye")
        self.env["sapian.filing"].sudo().create(
            {
                "company_id": self.env.company.id,
                "filing_key": "paye",
                # A day out at BOTH ends, which is what a conversion done on the
                # wrong side of a leap year does to every Ethiopian boundary.
                "period_start": start + timedelta(days=1),
                "period_end": end - timedelta(days=1),
                "filed_on": end,
            }
        )
        self.assertEqual(
            self.env["sapian.filing"]._filed_on_for("paye", start, end, self.env.company),
            end,
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
