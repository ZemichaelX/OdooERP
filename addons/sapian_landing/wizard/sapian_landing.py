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
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    period_label = fields.Char(
        compute="_compute_period_label",
        help="The filing period, in the calendar the deadlines are set in.",
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
        """Ethiopian, because that is what the deadlines are set in.

        `l10n_et_calendar` is a hard dependency of this module for exactly this
        line. It is not decoration: an operator who is told a return is due
        "30 Nehase" and reads "5 September" on the page has to convert in their
        head every month, and the conversion is where mistakes live.
        """
        for landing in self:
            landing.period_label = landing._ethiopian_period_label()

    def _ethiopian_period_label(self):
        self.ensure_one()
        if not self.date_from or not self.date_to:
            return False
        from odoo.addons.l10n_et_calendar.reference import (  # noqa: PLC0415
            et_calendar,
        )

        start = et_calendar.gregorian_to_ethiopian(self.date_from)
        end = et_calendar.gregorian_to_ethiopian(self.date_to)
        if (start.year, start.month) == (end.year, end.month):
            return "%s %s" % (et_calendar.month_name(start.month), start.year)
        return "%s %s – %s %s" % (
            et_calendar.month_name(start.month),
            start.year,
            et_calendar.month_name(end.month),
            end.year,
        )

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

    def _source_records(self):
        """Every report this page reads, created once per period."""
        self.ensure_one()
        window = {
            "company_id": self.company_id.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
        }
        return {
            "vat": self._find_or_create("l10n.et.vat.declaration", dict(window)),
            "wht": self._find_or_create("l10n.et.wht.summary", dict(window)),
            "pl": self._find_or_create("l10n.et.profit.loss", dict(window)),
            "bs": self._find_or_create("l10n.et.balance.sheet", dict(window)),
        }

    def _payroll_run_domain(self):
        self.ensure_one()
        return [
            ("company_id", "=", self.company_id.id),
            ("date_from", ">=", self.date_from),
            ("date_to", "<=", self.date_to),
        ]

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
        """One statutory filing: amount, period, deadline, status."""
        self.ensure_one()
        days = self.env["sapian.filing.deadline"]._days_for(key, self.date_to, self.company_id)
        deadline = filing_status.deadline_for(self.date_to, days)
        filed_on = self.env["sapian.filing"]._filed_on_for(key, self.date_to, self.company_id)
        row = {
            "section": COMPLIANCE,
            "kind": "amount",
            "key": key,
            "label": label,
            "source_model": source_model,
            "source_key": source_key,
            "deadline": deadline,
            "filed_on": filed_on,
            "status": filing_status.status_for(
                deadline, filed_on, today=fields.Date.context_today(self)
            ),
            "available": True,
        }
        row.update(extra)
        return row

    def _compliance_rows(self):
        self.ensure_one()
        sources = self._source_records()
        vat = sources["vat"]
        runs = self.env["l10n.et.payroll.run"].sudo().search(self._payroll_run_domain())

        rows = []

        vat_row = self._filing_row(
            "vat",
            self.env._("Value Added Tax"),
            "l10n.et.vat.declaration",
            "net_vat",
            source_res_id=vat.id,
        )
        if vat.off_chart:
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

        payroll_missing = self.env._(
            "No payroll run covers this period, so there is no employment "
            "income tax to declare. That is not the same as declaring nothing."
        )
        paye = self._filing_row(
            "paye",
            self.env._("Employment Income Tax (PAYE)"),
            "l10n.et.payroll.run",
            "total_paye",
            source_domain=repr(self._payroll_run_domain()),
        )
        pension = self._filing_row(
            "pension",
            self.env._("Pension"),
            "l10n.et.payroll.run",
            "total_pension_all",
            source_domain=repr(self._payroll_run_domain()),
        )
        if not runs:
            for row in (paye, pension):
                row.update(available=False, unavailable_reason=payroll_missing)
        rows.extend([paye, pension])
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
        rows.append(
            self._check_row(
                "vat_on_chart",
                self.env._("VAT resolves against the Ethiopian chart"),
                not vat.off_chart,
                (
                    self.env._("This company is not on the Ethiopian chart of accounts.")
                    if vat.off_chart
                    else self.env._("VAT codes resolve.")
                ),
                "l10n.et.vat.declaration",
                vat.id,
            )
        )
        wht_warnings = wht._get_report_data()["warnings"]
        rows.append(
            self._check_row(
                "wht_identifiers",
                self.env._("Every withholding line carries a supplier TIN"),
                not wht_warnings,
                wht_warnings[0] if wht_warnings else self.env._("No missing identifier."),
                "l10n.et.wht.summary",
                wht.id,
            )
        )
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
