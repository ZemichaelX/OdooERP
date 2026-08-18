# SapianERP — work queue

**One item per turn. Do the top unfinished item, then stop.** Do not start the
next one in the same turn.

**This file is the handover.** A fresh session reads, in this order:

1. `CLAUDE.md` — the rules, and they override everything.
2. `docs/defect-register.md` — what is broken, what is decided, and the five rules
   with their worked examples.
3. `docs/product-readiness.md` — what was measured, how, and on what.
4. **this file** — what to do next.

No transcript replay is needed or wanted. If something is not written down here or
in those three, it is not context — it is a rumour.

**"Done" for every item includes: every CI check completed green.** Not "green
except", not "green after the flake". CI's own floor (`MIN_EXPECTED_TESTS`) is
part of that, so a suite that did not run is not a pass.

**Where an item needs an answer Zemichael has not given** — TIN vs VAT
registration number, the fiscal device, tax-inclusive pricing, `592100` — design
so his answer changes a **VALUE**, not the **MECHANISM**, and carry on. Never
block on it, and never guess it into code.

---

## Queue

| # | Item | State |
|---|---|---|
| 1 | **TIN on documents** | **DONE** — PR #52 merged |
| 2 | #51 — re-run, merge if green | **DONE** — merged as `20cbe4a` |
| 3 | **Account types** — nine accounts, three-digit rules | **DONE** — PR #53 merged |
| 4 | **Profit and loss** | **DONE** — merged, both checks proved red |
| 5 | **Balance sheet** | todo |
| 6 | #50 — **DIAGNOSED**: nothing to fix here, it carries #49's defect | blocked on 7 |
| 7 | #49 — write-tripwire out, fix order-independent | todo |
| 8 | Palette additions | todo |
| 9 | PR 4 — the four remaining "Powered by Odoo" mails | todo |
| 10 | Landing slot and grid toggle — Phase A discovery first | todo |
| 11 | Branch cleanup — 35 remote branches | todo |

**Reordered 18 Aug** so the reporting blocker (register entry 27) clears today.
The two reports moved up; **#50 moved down because its diagnosis is unbounded** and
an unbounded item must not sit in front of a dated one. The old item 4 was **split
in two — account types (3) and the P&L (4)** — because a data migration and a new
report are different risks, and one PR each keeps the report from waiting on a
migration review.

**If the day runs short, what gives is item 6 onwards — never the tie-outs on 4
and 5.** A P&L whose tie-out does not discriminate is worse than no P&L, because it
invites trust it has not earned. **If ever tempted to ship one without a
proven-red tie-out: stop and say so instead.**

---

### 1. TIN ON DOCUMENTS — code complete, CI not yet run

Design: `docs/design-tin-identifier.md`. Blocker; ahead of the P&L because a
client is sending non-compliant invoices *today*.

**Done when:** the invoice is sent through `account.move.send.wizard`, captured at
the **SMTP boundary**, its PDF text extracted, and **both** TINs asserted in the
bytes — and the guard **fails loudly if the renderer is unpatched** rather than
passing on the half it cannot see.

Not: flipping `is_invoice_report`. That fixes one document and leaves 17
external-layout blocks guarded on an empty `company.vat`.

**State, 18 Aug.** Built and proved locally on **both** paths — fresh `-i` and
`-u` upgrade — **77 tests, 0 failed, 0 skipped**, lint clean. The upgrade proof is
discriminating: the country label was nulled first, so the migration had to do the
work.

**`done` is NOT yet met, because CI has not run.** `.github/workflows/ci.yml`
triggers on `push: [master]` and `pull_request` only, so **nothing runs on a bare
feature branch** — this branch has zero workflow runs. Closing item 1 needs a PR
opened against `master`, which is an outward action and was not authorised.
**Awaiting the go-ahead; do not mark this item done until CI has actually run
green.**

### 2. #51 — re-run now the incident is over, merge if green

Ten minutes. It was never diagnosed as red on its merits; it was caught by the
GitHub incident.

### 3. ACCOUNT TYPES — the chart, not the report

Design: `docs/design-pl-account-types.md`. **Nine accounts, three-digit rules**, in
`l10n_et_base` beside `CORE_ACCOUNT_FIXES`, with a **versioned migration** — the
template merge covers fresh chart loads only, and `_pre_reload_data` does not update
fields on accounts that already exist.

`592100 "Other"` stays **UNCLASSIFIED** until the accountants answer. An account
whose name says nothing, typed by code range alone, is where a silent
misclassification lives.

Measured and already known: the change is **allowed with posted entries present**,
**no total moves** (139,993.00 before and after), and only **one** of the nine
carries posted entries. Prior-period statements reprint with a gross-profit line
they did not have — net profit unchanged, so nothing filed is contradicted.

**Watch the two-digit trap:** a `63` rule wrongly catches `632100`/`632200`/`632400`
(construction, i.e. capex) as depreciation. `631` only.

### 4. PROFIT AND LOSS

Reuses `l10n.et.report.period.mixin` almost wholesale — `_period_line_domain`,
`_account_movement`, **`_tie_out_row`**, `_store_csv`, `_csv_tie_out_rows`. What is
new: the section grouping (now reading account **types**, thanks to item 3), the
model, and two templates.

**Tie-out, approved as proposed, and non-negotiable:**

1. **Net profit vs the ledger** — the statement's net profit against the
   independently summed movement of every income and expense account.
2. **`112 of 112 accounts classified, unclassified: none`** — going red **by name**
   when an account falls through. While `592100` is unmapped this reads
   `111 of 112, unclassified: 592100 Other`, on every run, until somebody answers.

**The tie-out must be proved RED before it is trusted.** Break the classification
on purpose and watch it fail.

**DONE, 18 Aug — merged.** `l10n.et.profit.loss`, 15 tests, `l10n_et_reports`
27 -> 42, CI floor 385 -> 400.

Rendered on the readiness tenant for calendar 2026: revenue 397,345.00, cost of
sales 54,350.00, **gross profit 342,995.00**, operating expenses 85,643.00, net
profit 257,352.00 — in a 70,225-byte PDF whose extracted text carries all of
them. Check 1: 257,352.00 against a ledger total of 257,352.00, difference 0.00.
Check 2: `61 of 62 accounts classified`, naming `592100 Other`.

**Both checks proved red, counts predicted before running and matched exactly:**
forcing the coverage check to always report `ok` gave **4 failed of 33**, the
four predicted by name; removing the cost-of-sales section gave **7 failed of
33**, the seven predicted by name. 0 skips in both.

**Two corrections reality made to the design, neither material:**

1. **`61 of 62`, not `111 of 112`.** 112 is the whole chart; only **62** of those
   accounts are income or expense, which is what a P&L is responsible for. The
   mechanism is exactly as designed — the denominator was mis-stated in the
   design note.
2. **A section sign flip is not a break this check can see.** It was going to be
   the proof that the two checks differ. Flipping `credit_positive` negates twice
   — once making the row report-positive, once adding the section to net profit —
   and cancels: the face of the statement misprints (revenue shown negative)
   while the total does not move. Replaced with a break the check genuinely
   catches (a row filter eating an account) and the limit is written into the
   test rather than papered over.

### 5. BALANCE SHEET

Same shape. Its own tie-out: **assets − (liabilities + equity + net profit) = 0.00**,
which also ties the two statements to each other.

After 4 and 5 the reporting blocker is cleared.
**Trial balance and general ledger are deliberately NOT in this queue.**

### 6. #50 — DIAGNOSED 18 Aug, and the heading below was wrong

**"Genuinely red on its own account" is refuted.** Register entry 45 has the
evidence. #50 has ONE red job of nine — `SapianBot survives an upgrade`, failing
`'OdooBot' != 'SapianBot'` 4 of 10 on the **upgrade** phase while phase 1 passes
0-of-10-failed. That is **item 7's defect**. #50 changes
`scripts/update_local.sh` and has no causal connection to the system partner.

**So item 6 has nothing to fix, and this item should follow item 7, not precede
it.** Recommended reorder, NOT applied — it needs Zemichael's word.

Two things mean #50 cannot close on code alone anyway:

1. Its base is five merges behind master — it needs a rebase and a fresh run
   whatever happens to the bot job.
2. **Windows verification is OWED BY THE OPERATOR** (rule 4). Linux evidence is
   not proof for a Windows path, and no work in this container can supply it.

**Why the wrong reading survived:** this queue recorded a red and a timestamp
but not WHICH JOB was red. A PR-level red is an aggregate over nine jobs, and an
aggregate is never a diagnosis.

### 7. #49 — the write-tripwire and load order

Remove the write-tripwire probe from **shipping** code, and make the fix
**order-independent**. 132's green was luck: our module moved between 26/30 and
27/30 across identical runs. **The guard must force `mail_bot` to load after us,
not hope for it.**

### 8. PALETTE ADDITIONS — one PR

Focus ring and outline inside `.o_sapian_auth`, outline on "Choose a user", and
the property guard **enumerating every interactive control**. It must run on a
page **with a stored user list**, or it cannot see the element that started this
(register entry 1). Fix the CDP `TimeoutError` that made the first attempt
establish nothing — an attempt that establishes nothing is rule 3.

### 9. PR 4 — the four remaining "Powered by Odoo" mails

Three `auth_signup` templates into the existing `sapian_theme_auth_signup` bridge
(they are `mail.template` data records, so they need a `body_html` override), and
the `im_livechat` transcript into a **new** bridge. Register entry 4.

### 10. LANDING SLOT AND GRID TOGGLE — Phase A discovery first

**Report which stock overview holds the slot and what tiles each renders. Do not
pick one yourself.** Register entry 12.

### 11. BRANCH CLEANUP

35 remote branches. Delete the merged ones; **list what was kept and why.**

---

## CI is not giving verdicts, from 10:52 UTC on 18 Aug

**Read register entry 46 before touching CI.** From 10:52 every job of every
NEW workflow run fails in 3–4 seconds with `runner_id: 0`, no log (404) and an
empty check-run output — across two different workflow files. Runs created
before 10:52 ran to completion normally (master's run 143: **6 of 6 green**).

**This is an account-level Actions condition, not our code.** It needs
Zemichael: Actions minutes / spending limit, or waiting for the allowance to
reset.

**Confirmed idle, 11:03.** PR #56's run was created with every other run
finished and the account idle — and failed identically. So this is NOT
contention and NOT caused by run-stacking (the register's first reading, since
corrected). It is a hard cutover at ~10:52 that persists at zero load.

**Do not re-run and do not reopen PRs to force a run** — three re-run attempts
and one reopen all reproduced it exactly. Stop creating runs; treat CI as having
given **no verdict in either direction** (rule 3).

**What this blocks:** #55 (item 5, the balance sheet) cannot merge, because
"done" requires every check completed green and there is no completed run
against its head. The code itself is proved locally — 60 tests, 0 failed, 0
skipped; both new checks proved red at 9-of-50 and 1-of-50 against counts stated
in advance; the statement rendered on the readiness tenant balancing at
885,766.75 both sides. **The gap is bookkeeping, not doubt** — but it is still a
gap, and the rule is the rule.

---

## Deliberately NOT in this queue

**The compliance dashboard** (register entry 13). It needs the **two e-Tax CSVs**,
which nobody has supplied, and it is the next major piece after this list. It is
not forgotten and it is not deprioritised — it is **blocked on information**, and
the register's "Still owed by Zemichael" section is where that unblocks.
