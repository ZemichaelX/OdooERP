# sapian_landing — the page a person lands on

Logging in used to land on the app launcher, and before that on whatever list
the home action happened to point at. Neither answers the question the person
opening the system at 8am actually has: **what do we owe, by when, and did last
month make money.**

Two sections, in that order, and the order is the decision: compliance first,
because it is the only thing on the page that gets worse while nobody looks at
it, then the money.

## The one architectural rule

**No figure on this page is computed here.** Not one.

Every amount is read from the report that owns it, at the moment the page is
read, through `SapianLandingLine._source_value`. The `value` field is computed
and **not stored**, so there is nothing to go stale — and `test_landing_figures`
asserts both: that the field is unstored (structure) and that every line agrees
with its source when re-derived independently (behaviour).

If the profit & loss says 28,007, this page says 28,007, because it asks the
profit & loss. It does not know 28,007.

Three source shapes, all of them the source's own computation:

| Shape | Example | What it reads |
|---|---|---|
| a field on one record | `net_vat` | `l10n.et.vat.declaration.net_vat` |
| `section:<key>` | `section:revenue` | the total of that section of the report's own `_get_report_data()` |
| a field over a domain | `total_paye` | summed across the payroll runs in the month |

The third is an aggregation of the report's numbers, not a second way of
arriving at them: PAYE per run is the run's own field, and the month is the sum
of the runs.

The record a figure is read from is the record clicking it opens
(`_find_or_create` searches before it creates), so the page and the report can
never be two different windows over the same ledger.

## What is on it, and where each figure comes from

### Due to the Ministry of Revenues

| Figure | Source | Absent when |
|---|---|---|
| Value Added Tax | `l10n.et.vat.declaration.net_vat` | the company is not on the Ethiopian chart, so no VAT code resolves — the declaration's own `off_chart` flag |
| Withholding Tax | `l10n.et.wht.summary.total_wht` | — |
| Employment Income Tax | `l10n.et.payroll.run.total_paye`, summed over the filing month | no payroll run IS that filing month |
| Pension | the run's employee + employer halves | no payroll run IS that filing month |

Each carries **its own period**, the deadline, and `filed` / `due` / `late` /
`deadline unknown`.

### The period is per-tax, and it is data

The four filings are not all counted in the same calendar, so the page has no
single period and its heading no longer claims one — it names the **business
month**, and each compliance row carries the period that row covers.

| Filing | Period | Confidence |
|---|---|---|
| Employment Income Tax | **Ethiopian month**, filed during the following Ethiopian month | **VERIFIED** — `docs/ethiopian-tax-reference.md` §2, two accountants and PwC |
| Value Added Tax | Gregorian month, 30 days | **UNVERIFIED** — the reference is silent |
| Withholding Tax | Gregorian month, 30 days | **UNVERIFIED** — the reference is silent |
| Pension | Gregorian month, 30 days | **UNVERIFIED** — the reference marks this exact question open |

The three UNVERIFIED rows record **what the product does today, not an answer**,
and each carries the question that would settle it — read them at *Accounting →
Filing Periods*, or in `data/filing_period_data.xml`. They are
`sapian.filing.period` records with an effective date, so closing one of those
questions is a row an accountant edits, not a release. The open questions are
written up in `docs/defect-register.md`.

**The label never names a period the figures do not cover.** The defect this
replaced converted both ends of a Gregorian month into Ethiopian dates and
printed the two month names it landed in: *"Sene 2018 – Hamle 2018"* for 1–31
July 2026 — sixty days' worth of month names over a 31-day range that begins 24
days into Sene, ends 24 days into Hamle and covers neither. Now a whole month is
NAMED (`Hamle 2018`), a Gregorian month is named as itself with the Ethiopian
span given as dates (`July 2026 (24 Sene – 24 Hamle 2018)`), and anything else
gets the dates alone. A month name only ever appears with a day number beside
it, where it cannot be read as a period.

**A payroll run must BE the filing month.** The reference records the payroll
cycle as a business choice — one accountant runs Ethiopian months, the other
Gregorian — and states the mapping onto a filing month only for the first: a run
whose period is Hamle 2018 is filed as Hamle 2018. For a Gregorian-cycle run it
gives the filing *window* and never says which month goes on the form, so the
page says it cannot place the run and names the open question rather than
picking a month. That is `Open 4` in the defect register.

### What does not reconcile

| Check | Source |
|---|---|
| Profit and loss ties to the general ledger | `l10n.et.profit.loss.tie_out_ok` |
| Balance sheet balances | `l10n.et.balance.sheet.tie_out_ok` |
| Every account is classified | the balance sheet's own `classification` block |
| VAT resolves against the Ethiopian chart | `off_chart` |
| Every withholding line carries a supplier TIN | the WHT summary's own warnings |

### The business

Revenue, gross profit, net profit (profit & loss), bank and cash, receivables
(balance sheet) — each the statement's own section total or field.

## Absent, never zero

A figure this page cannot stand behind is not shown, and the row says why in
the place the number would have been. The reasons are themselves derived:

* **not on the Ethiopian chart** — the VAT declaration says so about itself;
* **no payroll run for this period** — which is not the same as declaring nil;
* **nothing was posted to the ledger** — so revenue and profit are *unmeasured*,
  not zero. This is what makes a brand-new tenant readable: a company that has
  existed for one day has no profit & loss, and printing `0.00` five times for
  it is a wall of zeros pretending to be a business.

## Deadlines, and the two things that had no source at all

Neither existed anywhere in this product before this module, and both are
stated here rather than quietly invented.

**When a filing is due.** Nothing knew. `sapian.filing.deadline` is
effective-dated configuration — CLAUDE.md rule 4, the same discipline as PAYE
bands — so correcting a deadline never moves a period already assessed against
the old rule. A period that ends before every rule reads *deadline unknown* — it
does not borrow a rule written later.

A deadline has **two shapes**, because the evidence has two:

* **a number of days** — pension's shape: "POESSA declaration + bank slip within
  30 days", accountant-verified Jul 2026. VAT and withholding are given the same
  window **by analogy, which is not evidence**, and their rows say UNVERIFIED.
* **the end of the following period** — employment income tax's shape, and
  VERIFIED: the return is filed *"during the following Ethiopian month"*.

They agree for eleven months of the Ethiopian year, because an Ethiopian month
is 30 days — which is how a wrong rule looked right. They part at **Pagume**,
which is 5 or 6 days: Nehase 2018's return is due 10 September 2026, where
"+30 days" says 5 October. That is why the rule records the shape and not the
coincidence.

Swept day by day across 2026–2028, the old Gregorian-month-plus-30-days rule
over-ran the real employment-income-tax deadline by **20 to 50 days and was
never early** — 24 days on 20 August 2026, the day it was found.

**Whether it was filed.** Nothing knew this either, and nothing can derive it: a
posted payroll run means payslips were confirmed, not that a declaration reached
the Ministry of Revenues, and those are different events weeks apart.
`sapian.filing` records the submission — date, reference, who recorded it. It is
the only writable model this feature adds.

## The grid button

"Login lands on an admin list" and "the grid button goes one way" are the same
defect from two ends, and the fix is one line of behaviour, not a patch to the
vendored tree.

`sapian_theme` sets `is_redirect_home = True` with **no** home action, which
makes the launcher the landing surface. In that mode `AppsMenu.onMenuClick`
takes its `is_redirect_to_home` branch — juggling a `redirect_menuId` in
localStorage and rewriting the URL — so a second click does not come back,
because there is nothing behind the launcher to come back to.

Giving the user a home action fixes both. web_responsive's own model does the
rest: `res_users.py:42` clears `is_redirect_home` for any user that has an
`action_id`, so the grid button falls into its plain branch —
`setOpenState(!this.state.open)` — and opens the launcher *over* the page, then
closes it back onto the page.

`sapian_theme` keeps its launcher default, because it must install on a database
carrying no other product module and the landing action does not exist there.
This module moves users that have no home action of their own; one that has
chosen a home action keeps it.

## What is NOT on the page, and why

**Overdue receivables.** Asked for, and not shipped. Odoo Community has no aged
receivable report — `account_reports` is Enterprise — so there is nothing whose
computation this page could read. Building one here would be a second
implementation of an ageing, which is the one thing this page is not allowed to
be. The balance sheet's **Receivables** total is shown instead, which is the
whole balance rather than the overdue part, and is labelled as what it is.

The honest fix is an aged-receivable report in `l10n_et_reports`, after which
this page reads it in three lines.
