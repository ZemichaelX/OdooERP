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
| Employment Income Tax | `l10n.et.payroll.run.total_paye`, summed over the month | no payroll run covers the period |
| Pension | the run's employee + employer halves | no payroll run covers the period |

Each carries the period, the deadline, and `filed` / `due` / `late` / `deadline
unknown`.

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
the old rule. **The seeded 30-day window is UNVERIFIED**: it is what this
project recorded for pension ("POESSA declaration + bank slip within 30 days",
accountant-verified Jul 2026), applied to the other three by analogy. The page
says so in as many words, and an accountant can fix it in the UI without a code
change. A period that ends before every rule reads *deadline unknown* — it does
not borrow a rule written later.

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
