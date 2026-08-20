# -*- coding: utf-8 -*-
"""The page a person lands on: what the business owes, then what it earned.

WHAT THIS MODEL DOES NOT DO
---------------------------
It does not compute a single figure. Not one. Every amount on the page is read
off the report that owns it, at the moment the page is read, through
`SapianLandingLine._source_value`. There is no second implementation to drift
from the first, and no cached copy to go stale, because there is no copy: the
value fields are computed and NOT stored.

That is the whole architecture, and it is the answer to "if the P&L says 28,007
the landing page says 28,007" — the landing page does not know 28,007. It asks
the P&L, every time.

WHY THE SOURCE RECORDS ARE REAL AND SHARED
-------------------------------------------
`_source_records` finds or creates the period's VAT declaration, withholding
summary, profit & loss and balance sheet. Finds FIRST: the record the operator
opens by clicking a figure is the same record the figure was read from, so the
page and the report cannot be looking at two different windows over the ledger.
Creating one per (company, period) is bounded — a month has one of each — and
those records are the operator's declarations for the month anyway.

WHY A FIGURE CAN BE ABSENT
--------------------------
Rule 2 of this feature, and the reason the product is worth anything: a number
it cannot stand behind is not shown. Each line carries `available` and, when
false, the reason — never zero, never a dash that might be zero. The reasons are
themselves derived from data:

  * the company is not on the Ethiopian chart, so no VAT code resolves
    (`l10n.et.vat.declaration.off_chart` — the report says so itself);
  * no payroll run exists for the period, so there is no employment income tax
    to declare — which is different from declaring nothing;
  * no journal entry was posted in the period, so revenue and profit are not
    zero, they are unmeasured.

The last one is what makes a brand-new tenant readable. A company that has
existed for a day has no P&L, and printing "Revenue 0.00 / Net profit 0.00" for
it is a wall of zeros pretending to be a business.

ONE PERIOD PER FILING, NOT ONE PERIOD PER PAGE
-----------------------------------------------
The page used to compute a single Gregorian month and put all four filings under
it. For employment income tax that is wrong: `docs/ethiopian-tax-reference.md`
section 2 is VERIFIED that the period is an ETHIOPIAN month. So each filing now
asks `sapian.filing.period` which calendar it is counted in, and gets its own
`period_start`, `period_end` and label. The BUSINESS half of the page is still a
Gregorian month, because sales and cash are not a filing and have no calendar
question attached.

Three of the four calendars are still open questions and their rows say so in
the data. This module does not reason across from the one that is settled.
"""

import ast
import logging

from odoo import api, fields, models

from ..reference import filing_status

_logger = logging.getLogger(__name__)

COMPLIANCE = "compliance"
RECONCILIATION = "reconciliation"
BUSINESS = "business"


class SapianLanding(models.TransientModel):
    _name = "sapian.landing"
    _description = "SapianERP Landing Page"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    # THE BUSINESS WINDOW, and only that. Each compliance line carries its own
    # period, in its own calendar — see `_filing_period`.
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    period_label = fields.Char(
        compute="_compute_period_label",
        help="The month the business figures cover. Never a filing period: the "
        "four filings each carry their own, which may be in another calendar.",
    )
    line_ids = fields.One2many("sapian.landing.line", "landing_id")
    compliance_line_ids = fields.One2many(
        "sapian.landing.line",
        "landing_id",
        domain=[("section", "=", COMPLIANCE)],
    )
    reconciliation_line_ids = fields.One2many(
        "sapian.landing.line",
        "landing_id",
        domain=[("section", "=", RECONCILIATION)],
    )
    business_line_ids = fields.One2many(
        "sapian.landing.line",
        "landing_id",
        domain=[("section", "=", BUSINESS)],
    )

    # ---- the period ------------------------------------------------------

    @api.depends("date_from", "date_to", "company_id")
    def _compute_period_label(self):
        """The business month, described as what it actually is."""
        for landing in self:
            landing.period_label = landing._period_label(landing.date_from, landing.date_to)

    @api.model
    def _period_label(self, date_from, date_to):
        """Name a range only if it IS that period; otherwise say what it is.

        THE DEFECT THIS REPLACES. The old label converted both endpoints of a
        Gregorian month to Ethiopian and printed the two MONTH NAMES it landed
        in: "Sene 2018 – Hamle 2018" for 1–31 July 2026. That reads as two whole
        Ethiopian months — 8 June to 6 August, sixty days — over a range that
        begins 24 days into Sene, ends 24 days into Hamle and covers neither of
        them. A label that names a period the figures do not cover is the defect
        whichever calendar turns out to be right.

        So: a whole Ethiopian month is NAMED. A whole Gregorian month is named
        as the Gregorian month it is, with the Ethiopian span given as DATES —
        "24 Sene – 24 Hamle 2018" is a date range and cannot be read as a month.
        Anything else gets the date range alone.
        """
        if not date_from or not date_to:
            return False
        from odoo.addons.l10n_et_calendar.reference import (  # noqa: PLC0415
            et_calendar,
        )

        def ethiopian_span():
            start = et_calendar.gregorian_to_ethiopian(date_from)
            end = et_calendar.gregorian_to_ethiopian(date_to)
            if start.year == end.year:
                return "%d %s – %d %s %d" % (
                    start.day,
                    et_calendar.month_name(start.month),
                    end.day,
                    et_calendar.month_name(end.month),
                    end.year,
                )
            return "%d %s %d – %d %s %d" % (
                start.day,
                et_calendar.month_name(start.month),
                start.year,
                end.day,
                et_calendar.month_name(end.month),
                end.year,
            )

        if filing_status.is_whole_period(filing_status.ETHIOPIAN, date_from, date_to):
            ethiopian = et_calendar.gregorian_to_ethiopian(date_from)
            return "%s %d" % (et_calendar.month_name(ethiopian.month), ethiopian.year)
        if filing_status.is_whole_period(filing_status.GREGORIAN, date_from, date_to):
            return "%s (%s)" % (date_from.strftime("%B %Y"), ethiopian_span())
        return ethiopian_span()

    # ---- opening the page ------------------------------------------------

    @api.model
    def action_open_landing(self):
        """Build a fresh page for the last complete month and show it.

        Fresh every time: the figures are live, but WHICH period is being shown
        must move when the month does, and a reused transient would pin the page
        to whichever month it was first opened in.
        """
        company = self.env.company
        date_from, date_to = filing_status.previous_month(fields.Date.context_today(self))
        landing = self.create(
            {"company_id": company.id, "date_from": date_from, "date_to": date_to}
        )
        landing._build_lines()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Overview"),
            "res_model": "sapian.landing",
            "res_id": landing.id,
            "view_mode": "form",
            "views": [(self.env.ref("sapian_landing.view_sapian_landing_form").id, "form")],
            "target": "current",
            "context": {"create": False, "edit": False},
        }

    # ---- the source reports ----------------------------------------------

    def _find_or_create(self, model, values):
        """The period's report record, reused if it already exists.

        Reused so that the record a figure was read from is the record the
        operator opens by clicking it. Two records over the same window would
        compute the same numbers today and could be edited apart tomorrow.
        """
        self.ensure_one()
        domain = [(name, "=", value) for name, value in values.items()]
        record = self.env[model].sudo().search(domain, limit=1)
        return record or self.env[model].sudo().create(values)

    def _filing_period(self, filing_key):
        """(calendar, first_day, last_day) for one filing, or (None, None, None).

        The calendar comes from `sapian.filing.period` — data with an effective
        date — and the period is the last one of that calendar to have FINISHED
        before today. Not defaulted to Gregorian when no rule is recorded:
        defaulting is how the original defect got in, and a filing whose calendar
        nobody has written down is one this page cannot put a period against.
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        calendar = self.env["sapian.filing.period"]._calendar_for(
            filing_key, today, self.company_id
        )
        if not calendar:
            return None, None, None
        start, end = filing_status.previous_period(calendar, today)
        return calendar, start, end

    def _report_for(self, model, date_from, date_to):
        """One report record over one window."""
        self.ensure_one()
        return self._find_or_create(
            model,
            {
                "company_id": self.company_id.id,
                "date_from": date_from,
                "date_to": date_to,
            },
        )

    def _source_records(self):
        """Every report this page reads.

        The profit & loss and the balance sheet are on the BUSINESS window,
        because they are not filings. The VAT declaration and the withholding
        summary are on their OWN filing periods, so that clicking either figure
        opens the record that figure was read from — which is the point of
        finding before creating, and would be defeated by building them over a
        window neither of them is filed for.
        """
        self.ensure_one()
        records = {
            "pl": self._report_for("l10n.et.profit.loss", self.date_from, self.date_to),
            "bs": self._report_for("l10n.et.balance.sheet", self.date_from, self.date_to),
        }
        for key, model in (
            ("vat", "l10n.et.vat.declaration"),
            ("wht", "l10n.et.wht.summary"),
        ):
            _calendar, start, end = self._filing_period(key)
            records[key] = (
                self._report_for(model, start, end) if start else self.env[model].browse()
            )
        return records

    def _payroll_run_domain(self, period_start, period_end):
        """The runs that ARE this filing month, as a domain that survives `repr`.

        THE MAPPING RULE, and it is deliberately only the half the evidence
        settles. `docs/ethiopian-tax-reference.md` section 2 records that the
        payroll CYCLE is a business choice — accountant 1 runs Ethiopian months,
        accountant 2 runs Gregorian ones — and that "the mapping to the Ethiopian
        filing month and its window is what is mandatory". For accountant 1 that
        mapping is the identity: a run whose period IS Hamle 2018 is filed as
        Hamle 2018. That is what this domain expresses.

        For a Gregorian-cycle run the reference states the WINDOW ("1st–30th of
        the following Ethiopian month") and never states which Ethiopian month
        goes on the form. `_unmappable_runs` finds those runs and the page says
        it cannot place them, naming the open question, rather than picking a
        month. See docs/defect-register.md.

        The dates are ISO strings, not `date` objects, and that is the whole
        reason this method exists rather than the domain being written inline.
        The domain is stored on the line so the figure and the click-through
        open exactly the same set, which means it makes a round trip through
        `repr` and `ast.literal_eval` — and `repr(date(2026, 7, 1))` is
        `datetime.date(2026, 7, 1)`, a CALL, which `literal_eval` refuses.
        """
        self.ensure_one()
        return [
            ("company_id", "=", self.company_id.id),
            ("date_from", "=", str(period_start)),
            ("date_to", "=", str(period_end)),
        ]

    def _unmappable_runs(self, period_start, period_end):
        """Runs that OVERLAP the filing month without being it.

        The difference between "this company ran no payroll" and "this company
        runs payroll on a cycle we cannot yet place onto a filing month" is the
        whole of the honest answer, and they are two different sentences on the
        page.
        """
        self.ensure_one()
        return (
            self.env["l10n.et.payroll.run"]
            .sudo()
            .search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("date_from", "<=", period_end),
                    ("date_to", ">=", period_start),
                ]
            )
        )

    def _has_posted_entries(self):
        """Did anything at all happen in the ledger this period?

        The predicate behind "unmeasured, not zero". Deliberately the crudest
        possible question — one posted line is enough — because anything
        cleverer would be this page deciding what counts as trading, which is
        not its job.
        """
        self.ensure_one()
        return bool(
            self.env["account.move.line"]
            .sudo()
            .search_count(
                [
                    ("company_id", "=", self.company_id.id),
                    ("parent_state", "=", "posted"),
                    ("date", ">=", self.date_from),
                    ("date", "<=", self.date_to),
                ],
                limit=1,
            )
        )

    # ---- building the page ------------------------------------------------

    def _build_lines(self):
        self.ensure_one()
        self.line_ids.unlink()
        rows = self._compliance_rows() + self._reconciliation_rows() + self._business_rows()
        for sequence, row in enumerate(rows, start=10):
            row["sequence"] = sequence
            row["landing_id"] = self.id
        self.env["sapian.landing.line"].create(rows)
        _logger.info(
            "sapian_landing: built %d lines for %s %s..%s (%d unavailable)",
            len(rows),
            self.company_id.display_name,
            self.date_from,
            self.date_to,
            len([r for r in rows if not r.get("available", True)]),
        )
        return self.line_ids

    def _filing_row(self, key, label, source_model, source_key, **extra):
        """One statutory filing: its own period, amount, deadline and status."""
        self.ensure_one()
        calendar, period_start, period_end = self._filing_period(key)
        row = {
            "section": COMPLIANCE,
            "kind": "amount",
            "key": key,
            "label": label,
            "source_model": source_model,
            "source_key": source_key,
            "period_start": period_start,
            "period_end": period_end,
            "period_label": self._period_label(period_start, period_end),
            "available": True,
        }
        if not calendar:
            # No recorded calendar means no period, which means no figure — the
            # page does not fall back to "probably a Gregorian month".
            row.update(
                available=False,
                status=filing_status.UNKNOWN,
                unavailable_reason=self.env._(
                    "No filing period rule is recorded for this filing, so the "
                    "period it covers is unknown. Set one under Accounting > "
                    "Filing periods."
                ),
            )
            row.update(extra)
            return row

        rule = self.env["sapian.filing.deadline"]._rule_for(key, period_end, self.company_id)
        window, days = rule if rule else (None, None)
        deadline = (
            filing_status.deadline_for(period_end, days, window, calendar) if rule else None
        )
        filed_on = self.env["sapian.filing"]._filed_on_for(
            key, period_start, period_end, self.company_id
        )
        row.update(
            deadline=deadline,
            filed_on=filed_on,
            status=filing_status.status_for(
                deadline, filed_on, today=fields.Date.context_today(self)
            ),
        )
        row.update(extra)
        return row

    def _compliance_rows(self):
        self.ensure_one()
        sources = self._source_records()
        vat = sources["vat"]

        rows = []

        vat_row = self._filing_row(
            "vat",
            self.env._("Value Added Tax"),
            "l10n.et.vat.declaration",
            "net_vat",
            source_res_id=vat.id,
        )
        if vat and vat.off_chart:
            # The report says so about itself: with no Ethiopian chart no VAT
            # code resolves, and its own totals are zero for that reason rather
            # than because no VAT was charged.
            vat_row.update(
                available=False,
                unavailable_reason=self.env._(
                    "This company is not on the Ethiopian chart of accounts, so "
                    "no VAT code resolves and no VAT figure can be stated."
                ),
            )
        rows.append(vat_row)

        rows.append(
            self._filing_row(
                "wht",
                self.env._("Withholding Tax"),
                "l10n.et.wht.summary",
                "total_wht",
                source_res_id=sources["wht"].id,
            )
        )

        rows.extend(self._payroll_rows())
        return rows

    def _payroll_rows(self):
        """Employment income tax and pension, which share their source records.

        Both are read off the payroll runs that ARE the filing month. They can
        each be on a different calendar — employment income tax is VERIFIED as
        Ethiopian, pension's window is marked UNVERIFIED in the reference — so
        they are built independently rather than as two views of one period.
        """
        self.ensure_one()
        rows = []
        for key, label, source_key in (
            ("paye", self.env._("Employment Income Tax (PAYE)"), "total_paye"),
            ("pension", self.env._("Pension"), "total_pension_all"),
        ):
            _calendar, period_start, period_end = self._filing_period(key)
            row = self._filing_row(key, label, "l10n.et.payroll.run", source_key)
            if not period_start:
                rows.append(row)
                continue
            domain = self._payroll_run_domain(period_start, period_end)
            row["source_domain"] = repr(domain)
            runs = self.env["l10n.et.payroll.run"].sudo().search(domain)
            if not runs:
                overlapping = self._unmappable_runs(period_start, period_end)
                row.update(
                    available=False,
                    unavailable_reason=(
                        self.env._(
                            "This company runs payroll on a cycle that does not "
                            "line up with this filing period (%(count)s run(s) "
                            "overlap it). Which filing month such a run belongs "
                            "to is not settled in our tax reference, and this "
                            "page will not guess it — see the filing period "
                            "rule's note.",
                            count=len(overlapping),
                        )
                        if overlapping
                        else self.env._(
                            "No payroll run covers this period, so there is no "
                            "employment income tax or pension to declare. That "
                            "is not the same as declaring nothing."
                        )
                    ),
                )
            rows.append(row)
        return rows

    # ---- what does not tie out -------------------------------------------

    def _check_row(self, key, label, ok, detail, source_model, source_res_id):
        return {
            "section": RECONCILIATION,
            "kind": "check",
            "key": key,
            "label": label,
            "check_ok": ok,
            "detail": detail,
            "source_model": source_model,
            "source_res_id": source_res_id,
            "available": True,
        }

    def _reconciliation_rows(self):
        self.ensure_one()
        sources = self._source_records()
        pl, bs, vat, wht = sources["pl"], sources["bs"], sources["vat"], sources["wht"]
        no_period = self.env._(
            "No filing period rule is recorded for this filing, so there is no "
            "period to reconcile."
        )
        rows = []

        pl_data = pl._get_report_data()
        bs_data = bs._get_report_data()

        rows.append(
            self._check_row(
                "pl_tie_out",
                self.env._("Profit and loss ties to the general ledger"),
                pl.tie_out_ok,
                pl_data["classification"]["message"],
                "l10n.et.profit.loss",
                pl.id,
            )
        )
        rows.append(
            self._check_row(
                "bs_tie_out",
                self.env._("Balance sheet balances"),
                bs.tie_out_ok,
                bs_data["classification"]["message"],
                "l10n.et.balance.sheet",
                bs.id,
            )
        )
        unclassified = bs_data["classification"]["unclassified"]
        rows.append(
            self._check_row(
                "unclassified_accounts",
                self.env._("Every account is classified"),
                not unclassified,
                (
                    self.env._(
                        "%(count)s account(s) carry no type and are held back "
                        "from the statement: %(codes)s",
                        count=len(unclassified),
                        codes=", ".join(row["code"] or "?" for row in unclassified[:5]),
                    )
                    if unclassified
                    else self.env._("No account is awaiting classification.")
                ),
                "l10n.et.balance.sheet",
                bs.id,
            )
        )
        vat_row = self._check_row(
            "vat_on_chart",
            self.env._("VAT resolves against the Ethiopian chart"),
            bool(vat) and not vat.off_chart,
            (
                no_period
                if not vat
                else (
                    self.env._("This company is not on the Ethiopian chart of accounts.")
                    if vat.off_chart
                    else self.env._("VAT codes resolve.")
                )
            ),
            "l10n.et.vat.declaration",
            vat.id,
        )
        if not vat:
            vat_row.update(available=False, unavailable_reason=no_period)
        rows.append(vat_row)

        wht_warnings = wht._get_report_data()["warnings"] if wht else []
        wht_row = self._check_row(
            "wht_identifiers",
            self.env._("Every withholding line carries a supplier TIN"),
            bool(wht) and not wht_warnings,
            (
                no_period
                if not wht
                else (wht_warnings[0] if wht_warnings else self.env._("No missing identifier."))
            ),
            "l10n.et.wht.summary",
            wht.id,
        )
        if not wht:
            wht_row.update(available=False, unavailable_reason=no_period)
        rows.append(wht_row)
        return rows

    # ---- the money --------------------------------------------------------

    def _business_rows(self):
        self.ensure_one()
        sources = self._source_records()
        pl, bs = sources["pl"], sources["bs"]
        traded = self._has_posted_entries()
        unmeasured = self.env._(
            "Nothing was posted to the ledger in this period, so these are "
            "unmeasured rather than zero."
        )

        def money(key, label, model, res_id, source_key):
            row = {
                "section": BUSINESS,
                "kind": "amount",
                "key": key,
                "label": label,
                "source_model": model,
                "source_res_id": res_id,
                "source_key": source_key,
                "available": True,
            }
            if not traded:
                row.update(available=False, unavailable_reason=unmeasured)
            return row

        return [
            money(
                "revenue",
                self.env._("Revenue"),
                "l10n.et.profit.loss",
                pl.id,
                "section:revenue",
            ),
            money(
                "gross_profit",
                self.env._("Gross profit"),
                "l10n.et.profit.loss",
                pl.id,
                "gross_profit",
            ),
            money(
                "net_profit",
                self.env._("Net profit"),
                "l10n.et.profit.loss",
                pl.id,
                "net_profit",
            ),
            money(
                "cash",
                self.env._("Bank and cash"),
                "l10n.et.balance.sheet",
                bs.id,
                "section:cash",
            ),
            money(
                "receivables",
                self.env._("Receivables"),
                "l10n.et.balance.sheet",
                bs.id,
                "section:receivables",
            ),
        ]


class SapianLandingLine(models.TransientModel):
    _name = "sapian.landing.line"
    _description = "SapianERP Landing Page Figure"
    _order = "sequence, id"

    landing_id = fields.Many2one("sapian.landing", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(related="landing_id.company_id")
    currency_id = fields.Many2one(related="landing_id.currency_id")
    section = fields.Selection(
        [
            (COMPLIANCE, "Compliance"),
            (RECONCILIATION, "Reconciliation"),
            (BUSINESS, "Business"),
        ],
        required=True,
    )
    kind = fields.Selection([("amount", "Amount"), ("check", "Check")], required=True)
    key = fields.Char(required=True)
    label = fields.Char(required=True)

    # ---- where the number comes from, and nowhere else -------------------
    source_model = fields.Char(required=True)
    source_res_id = fields.Integer()
    source_domain = fields.Char(
        help="Set instead of source_res_id when the figure is the sum of a "
        "field over several records — the payroll runs in a month, say. "
        "Clicking opens exactly this domain.",
    )
    source_key = fields.Char(
        help="What to read off the source: a field name, `section:<key>` for a "
        "section total of the report's own dataset, or `data:<key>` for a "
        "top-level key of it.",
    )

    value = fields.Monetary(
        compute="_compute_value",
        help="Read from the source report on every read. Not stored, so it "
        "cannot be a stale copy of anything.",
    )
    available = fields.Boolean(default=True)
    unavailable_reason = fields.Char()

    # ---- compliance ------------------------------------------------------
    # EACH FILING CARRIES ITS OWN PERIOD. The page has no single one: employment
    # income tax is counted in Ethiopian months and the other three in Gregorian
    # ones today, so a shared header period would be wrong for at least one row
    # whichever calendar it used.
    period_start = fields.Date()
    period_end = fields.Date()
    period_label = fields.Char(
        help="The period this figure covers, named only if the range IS that "
        "period. A range that is not a whole month is given as dates.",
    )
    deadline = fields.Date()
    filed_on = fields.Date()
    status = fields.Selection(
        [
            (filing_status.FILED, "Filed"),
            (filing_status.DUE, "Due"),
            (filing_status.LATE, "Late"),
            (filing_status.UNKNOWN, "Deadline unknown"),
        ]
    )
    days_remaining = fields.Integer(compute="_compute_days_remaining")

    # ---- reconciliation ---------------------------------------------------
    check_ok = fields.Boolean()
    detail = fields.Char()

    # ---- the one method that reads a number ------------------------------

    def _source_value(self):
        """The figure, from the report that owns it. The only read there is.

        Three shapes, all of them the source's OWN computation:

          * a field on one record — `net_vat`, `gross_profit`;
          * `section:<key>` — the total of one section of the report's own
            `_get_report_data()`, which is how "Revenue" and "Bank and cash"
            are the statement's revenue and cash rather than a re-query;
          * a field summed over a domain — the payroll runs in a month. The sum
            is an aggregation of the report's numbers, not a second way of
            arriving at them.
        """
        self.ensure_one()
        if not self.source_model or not self.source_key:
            return 0.0
        model = self.env[self.source_model].sudo()
        if self.source_domain:
            records = model.search(ast.literal_eval(self.source_domain))
            if self.source_key == "total_pension_all":
                # The remittance is the two halves together; both are the run's
                # own fields and neither is recomputed here.
                return sum(
                    records.mapped("total_pension_employee")
                    + records.mapped("total_pension_employer")
                )
            return sum(records.mapped(self.source_key))
        record = model.browse(self.source_res_id)
        if not record.exists():
            return 0.0
        if self.source_key.startswith("section:"):
            wanted = self.source_key.split(":", 1)[1]
            for section in record._get_report_data()["sections"]:
                if section.get("key") == wanted:
                    return section["total"]
            return 0.0
        if self.source_key.startswith("data:"):
            return record._get_report_data()[self.source_key.split(":", 1)[1]]
        return record[self.source_key]

    @api.depends("source_model", "source_res_id", "source_domain", "source_key")
    def _compute_value(self):
        for line in self:
            line.value = line._source_value() if line.kind == "amount" else 0.0

    @api.depends("deadline")
    def _compute_days_remaining(self):
        today = fields.Date.context_today(self)
        for line in self:
            line.days_remaining = filing_status.days_remaining(line.deadline, today) or 0

    # ---- clicking a figure opens the report it came from ------------------

    def action_open_source(self):
        """Rule 3, and it opens the SAME record the figure was read from."""
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": self.label,
            "res_model": self.source_model,
            "target": "current",
        }
        if self.source_domain:
            action.update(
                view_mode="list,form",
                domain=ast.literal_eval(self.source_domain),
            )
        else:
            action.update(view_mode="form", res_id=self.source_res_id)
        return action
