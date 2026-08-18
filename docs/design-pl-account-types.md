# Design note — put the P&L's grouping in the chart, not in the report

**Status: DESIGN, measured 18 Aug 2026. No code written.**

**The revision, and it is right.** 58 of 58 expense accounts typed plain `expense`
with zero `expense_direct_cost` is a **chart defect**, not a reporting
inconvenience: on this chart **no** P&L can show a gross profit line — ours,
OCA's, `base_accounting_kit`'s or Odoo Enterprise's. Fixing the types in
`l10n_et_base` fixes it once for every report that will ever read them; putting
prefix rules inside our P&L would fix it for exactly one report and hide the
defect from every other.

**Verdict: do it in the chart. It is less risky than it sounds — with one
correction to my own proposal.**

## Which accounts change

Measured against the live `et` chart (112 accounts):

| Code | Name | now | proposed |
|---|---|---|---|
| 511100 | Cost of Goods and Services | `expense` | **`expense_direct_cost`** |
| 590100 | Inventory Adjustments | `expense` | **`expense_direct_cost`** |
| 591100 | Purchase Returns and Allowances | `expense` | **`expense_direct_cost`** |
| 592100 | Other | `expense` | **`expense_direct_cost`** |
| 593100 | Social Welfare Levy on Imports | `expense` | **`expense_direct_cost`** |
| 631100 | Depreciation of vehicles and other vehicles | `expense` | **`expense_depreciation`** |
| 631300 | Depreciation of plant, machinery and equipment | `expense` | **`expense_depreciation`** |
| 631400 | Depreciation of buildings, furnishings | `expense` | **`expense_depreciation`** |
| 631500 | Depreciation of livestock and transport animals | `expense` | **`expense_depreciation`** |

**12 accounts matched my first draft of the rules. Three of them were wrong**, and
finding that is the argument for this placement rather than against it.

## The correction: a two-digit prefix rule is not safe

My proposed `63 → expense_depreciation` also caught:

- `632100` **Pre-construction activities**
- `632200` **Construction of buildings**
- `632400` **Construction of infrastructure**

Those are **construction / capital work, not depreciation.** Typing them
`expense_depreciation` would put capex in the depreciation line of every P&L
forever. The rules must be **three or four digits** (`631` yes, `632` no), and
each one wants an eye on it.

**This is exactly why the mapping belongs in the chart module.** In
`l10n_et_base` it sits beside `CORE_ACCOUNT_FIXES`, in one reviewable table, with
the account names next to the codes. Buried in a report it would have shipped, and
`632100 Construction of buildings` would have been depreciation in every statement
we ever printed, invisibly.

**592100 "Other" is DELIBERATELY LEFT UNCLASSIFIED** until Zemichael's accountants
answer. Its name says nothing and only the code range argues for cost of sales —
and an account whose name says nothing, typed by code range alone, is exactly
where a silent misclassification lives.

**The tie-out must count it as unclassified, not quietly absorb it.** That is the
point of the `112 of 112 accounts classified, unclassified: none` line: while
`592100` is unmapped the statement reports `111 of 112, unclassified: 592100
Other` **by name**, every time it is printed, until somebody answers. An
unclassified account must be visible on the face of the report — never defaulted
into "other expenses" where it would stop being a question.

## What it breaks on an existing tenant with posted entries

Measured on the readiness tenant, then rolled back:

| Question | Measured |
|---|---|
| Accounts changing type | **12** proposed, **9** correct (see above) |
| Of those, carrying posted entries | **1** — `511100`, 2 posted lines |
| Does Odoo block the change with posted entries? | **No — ALLOWED.** `511100 expense → expense_direct_cost` succeeded |
| Does any total move? | **No.** Derived expense total stayed **139,993.00** — identical |
| Reconcile flag | ended `False`, which is correct for an expense account |

**Nothing recomputes and no balance moves.** `account_type` is a classification,
not an amount: the same debits land in the same accounts, and only the *section*
a report puts them in changes.

**The one real consequence: history reclassifies.** A P&L run over a prior period
after the change will show a gross profit line that the same period did not show
before. Net profit is unchanged, so nothing already filed is contradicted — but if
a client has printed and signed a prior-period statement, its *shape* will differ
from a reprint. That is worth a line in the release note, not a blocker.

## Does it need a migration?

**Yes, and for the reason the expense-account fix taught us:** the template merge
covers fresh chart loads only, and `_pre_reload_data` deliberately does not update
fields on accounts that already exist. An existing tenant would keep every account
on `expense`, CI would be green, and nothing would say so.

The mechanism already exists and needs no invention: **`CORE_ACCOUNT_FIXES` in
`models/template_et.py` already does exactly this job** for the six mis-typed core
accounts (`221200`, `221300`, `221400`, `300600`, `300700`, `300800`), and
`_l10n_et_base_reload_for_company` already walks it and writes the differences.
The nine accounts above are more rows in that same table, applied by the same
loop, reached by the post-init hook and a versioned migration.

## Risk assessment, stated plainly

**Lower risk than the expense-account fix, which is already shipped and green.**
That one changed where *new postings land* — a behavioural change. This one
changes only how *existing postings are grouped in reports* — a presentational
change, with no amount moving and no posting behaviour altered.

**The risk that is real is the mapping itself**, not the mechanism: three of my
twelve proposed rows were wrong on first pass. Mitigation is that the table is
small, explicit, code-and-name paired, and reviewable by an accountant in one
sitting — which a prefix expression inside a report would not be.

**Recommendation: proceed with the chart fix**, with the corrected `631`-only
depreciation rule, and with `592100` flagged for an accountant's confirmation
before it is called cost of sales.

## The tie-out this enables — approved as proposed

1. **Net profit vs the ledger** — the statement's net profit against the
   independently summed movement of every income and expense account.
2. **`112 of 112 accounts classified, unclassified: none`** — accounts with
   movement in the period versus accounts the statement placed, going red **by
   name** if any account falls through.

The second line is the one that catches a silently dropped account, and once the
types carry the grouping it becomes a genuinely strong check: an account with a
type the P&L does not know about is now a **chart** error that the statement
reports, rather than a report bug nobody can see.
