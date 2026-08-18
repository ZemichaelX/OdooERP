# l10n_et_reports — Ethiopian Compliance (SapianERP)

Ships as the top-level app **Ethiopian Compliance** (menu renamed from
"Ethiopian Statutory Reports" and unparented from Accounting > Reporting when
it was promoted): compliance is the obligation the client is buying, the
reports are how it is discharged.

Thin statutory-reports slice (Epic B of the revised backlog, CLAUDE.md; spec
`docs/plan-2026/07-ethiopian-localization.md` §5 — everything else in §5 stays
deferred). Depends on `l10n_et_base` and reuses its tax records/WHT kind
markers — nothing re-declared here.

## Reports
- **Monthly VAT Declaration** (`l10n.et.vat.declaration`): output VAT (15% /
  zero-rated / exempt sales, base + tax per row), input VAT (purchases), net
  payable or credit carried forward (Proc 1341/2024, monthly period).
- **WHT Summary** (`l10n.et.wht.summary`): one row per vendor bill per WHT rate
  (3% / 30% / 15%) with supplier, TIN, base and amount; totals by rate; grand
  total. Missing supplier TINs get the MISSING marker + fix-before-filing
  warning (MoR rejects filings without identifiers). Remit within 30 days of
  month end.
- **Profit and Loss** (`l10n.et.profit.loss`): revenue, cost of sales, gross
  profit, other income, operating expenses, depreciation, net profit — for a
  date range, live from posted journal items, with PDF and CSV output.

  Odoo Community ships **no** profit & loss statement, and neither does any OCA
  repository we surveyed (`account_financial_report` has a general ledger and a
  trial balance but no P&L or balance sheet; `mis_builder` is an engine with
  zero templates). Until this existed a client could not see whether the
  business made money — defect register entry 27.

  **The section grouping is not in this module.** Which account belongs on which
  line is decided by the account's `account_type`, set once in the chart by
  `l10n_et_base`. Core `l10n_et` types all 58 of its expense accounts `expense`
  and none `expense_direct_cost`, so on the stock chart no P&L of any origin can
  show a gross profit line; `l10n_et_base` retypes nine of them (see its
  `CORE_ACCOUNT_FIXES`). A prefix table inside this report would have fixed one
  report and hidden the chart defect from every other.

  **Two checks print on the face of the statement**, and each is written so it
  cannot pass by the work not happening (CLAUDE.md rule 2):

  1. *Net profit vs the general ledger* — the statement's total, built from the
     section totals, against an independent search over the full period movement
     of every account whose `internal_group` is income or expense. The two sides
     are read by different queries from different definitions on purpose.
  2. *Accounts classified* — `61 of 62 accounts classified`, naming any
     shortfall. An account the statement cannot place is **left out of the
     totals**, so check 1 goes red as well, rather than being swept into "other
     expenses" where it would stop being a question.

  `592100 Other` is deliberately held back from a section
  (`ACCOUNTS_AWAITING_CLASSIFICATION` in `l10n_et_base`): its name gives no
  corroboration for the 59x cost-of-sales range, and an account typed by code
  range alone is where a silent misclassification lives. It is printed in its own
  visible section and counted as unclassified **on every printing** until the
  accountants answer. That is why a clean tenant reads `61 of 62`, not `62 of
  62` — the shortfall is the open question, not a bug.
- **Balance Sheet** (`l10n.et.balance.sheet`): assets, liabilities and equity as
  at a closing date, with retained earnings brought forward and the result for
  the period shown separately, PDF and CSV.

  **A position, not a flow.** The P&L reads movement inside its period; this
  reads every posted line up to and including `date_to`, which is one overridden
  method (`_statement_line_domain`). `date_from` still matters: it splits the
  accumulated result into *brought forward* and *result for the period*, and
  that is what lets the two statements be tied to each other.

  **Three checks print on the face of it:**

  1. *Total assets vs total liabilities and equity.* Different accounts,
     different queries — the left side from the asset sections, the right from
     the liability and equity sections plus the result summed off the income and
     expense accounts. An account that falls out of either side moves one and
     not the other.
  2. *Result for the period vs the profit & loss statement.* This statement sums
     it straight off the ledger; the P&L builds the same figure up from its
     section totals. **This is the check that makes the two statements one set of
     books rather than two opinions**, and it is deliberately independent of
     check 1 — breaking the P&L makes check 2 red and leaves check 1 green.
  3. *Accounts classified*, as on the P&L. Off-balance-sheet accounts are
     excluded **by definition**, and their count is reported so they never become
     invisible.

  Not built, deliberately: **trial balance and general ledger**. OCA's
  `account_financial_report` has both, and neither has any Ethiopian character
  worth owning.


## Design
- Reports read LIVE from posted journal items — a record is a period window
  over the GL, not a snapshot; reprinting after corrections shows current
  numbers. Refunds net out.
- **Tie-out guarantee**: every report carries reconciliation rows comparing its
  totals against the FULL GL movement of the accounts the underlying taxes post
  to (VAT payable 300700, VAT receivable 221200, WHT payable 300600). A manual
  journal entry that bypasses the tax engine renders a visible warning — a
  mismatch never passes silently.
- Tax records are resolved per company from the chart-template xmlids
  (`id_tax03/04/06/07/08/10`, WHT via the `l10n_et_wht_kind` marker), so the
  module is inert on companies not on the Ethiopian chart.

## ⚠ WHT anti-avoidance (accountant note, Jul 2026)
The 20,000/10,000 WHT thresholds are PER TRANSACTION, but the authority may
AGGREGATE deliberately split invoices (one supply invoiced as several
sub-threshold pieces) and assess the WHT that was avoided. The WHT summary
reports what was actually withheld per posted bill — it does not detect
splitting. Advise clients: never split a supply to duck the threshold; when
in doubt, withhold.

## ⚠ Verify against current MoR forms
The computations are exact and golden-tested; the ROW LAYOUT of the printed
declaration is a simple section-level rendering. Before filing with the
Ministry of Revenue, verify the current official VAT return / WHT schedule
layout and map these sections onto it.

## Tests
Golden values hand-computed from the Epic 3 demo document set (README of
`tests/common.py`): output 1,500 / input 10,950 / net −9,450 credit; WHT
{3%: 1,500, 30%: 4,500, 15%: 1,200} = 7,200 tied to GL.

Profit & loss goldens over the same July-2026 fixture: revenue 10,000.00, cost
of sales 73,000.00, gross profit −63,000.00, net profit −63,000.00. Neither the
cost-of-sales figure nor the gross-profit line existed before register entries
26 and 27 were fixed — every bill posted to a current asset, and every expense
account carried the same type.

Balance sheet goldens as at 2026-07-31 over the same fixture: receivables
11,500.00, input VAT 10,950.00, **total assets 22,450.00**, liabilities
85,450.00, result for the period −63,000.00, **total liabilities and equity
22,450.00** — the identity, both sides.

**Half of the statement tests prove the checks GO RED**, because a statement whose
self-check cannot fail invites trust it has not earned:
dropping a section's account type makes the ledger check differ by exactly the
amount that fell out; flipping a section's sign makes it differ while coverage
stays clean (so the two checks are not the same check twice); an account whose
type no section claims is named; and a company with no income or expense
accounts is refused rather than reported as reconciling perfectly.

For the balance sheet: dropping the receivables section unbalances it by exactly
11,500.00 while leaving its agreement with the P&L intact, and breaking the P&L
instead makes the two statements disagree by 10,000.00 while the balance sheet
still balances — each check failing on what the other cannot see. An asset
raised before `date_from` must still appear, which is the guard against reading
a period and calling it a position: that mistake would drop every opening
balance and still reconcile, because both sides would lose the same lines.
