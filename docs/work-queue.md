# SapianERP — work queue

**One item per turn. Do the top unfinished item, then stop.** Do not start the
next one in the same turn.

**This file is the handover.** A fresh session reads, in this order:

1. `CLAUDE.md` — the rules, and they override everything.
2. `docs/defect-register.md` — a pointer. The register itself moved to the private
   `sapianerp-internal` repository when this one was opened; the five rules it
   carries are restated in `CLAUDE.md`.
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
| 0 | **CI trigger hygiene** — push on master only, `paths-ignore`, concurrency | **DONE** — PR #59 merged |
| 1 | **TIN on documents** | **DONE** — PR #52 merged |
| 2 | #51 — re-run, merge if green | **DONE** — merged as `20cbe4a` |
| 3 | **Account types** — nine accounts, three-digit rules | **DONE** — PR #53 merged |
| 4 | **Profit and loss** | **DONE** — merged, both checks proved red |
| 5 | **Balance sheet** | **DONE** — both new checks proved red |
| 6 | #50 — diagnose before fixing | todo |
| 7 | #49 — write-tripwire out, fix order-independent | todo |
| 8 | Palette additions | todo |
| 9 | PR 4 — the four remaining "Powered by Odoo" mails | todo |
| 10 | Landing slot and grid toggle — Phase A discovery first | todo |
| 11 | Branch cleanup — 35 remote branches | **DONE** — 33 deleted, 7 live branches remain |
| 12 | **Self-hosted CI runner** | **DONE, then deliberately undone** — see below |

## Items 0 and 12: the runner decision, settled — do not re-litigate

Recorded here so no future session reopens it from first principles.

**What happened.** On 18 August the account's GitHub-hosted Actions minutes hit
2,000 of 2,000, with a reset on 1 September. CI could not run at all, and CI is
the only gate this repository has. A self-hosted runner on the operator's own
machine was registered and all six jobs were pointed at it (item 12, PR #57),
together with two trigger changes that make a single sequential runner bearable:
`push` restricted to master, `paths-ignore` for docs, and a concurrency block so
a superseded run stops sitting in front of the run somebody is waiting on
(item 0).

Two things had to be built just to make that runner work at all, because the
bottleneck was the operator's home internet connection rather than CPU or disk:
git installed into the Odoo container from a persistent local apt cache, and
Chrome resolved from a local path instead of downloaded per job.

**Why it was undone.** The repository went public on 18 August and Actions
minutes became unlimited. **Item 0's cost concern is therefore moot** — nothing
is metered any more. PR #59 put CI back on `ubuntu-latest` and deleted the git
bootstrap and the browser cache, which existed only to survive a slow domestic
link and are pure risk on a hosted runner: measured there, Chrome installs in
**13 seconds**.

**What was kept, and why it was worth keeping.** The concurrency block and the
`paths-ignore` triggers stayed. They were built for a scarce runner but they are
good hygiene on an abundant one too — a cancelled superseded run and a skipped
docs-only run are wins regardless of who is paying. Both are proved, not assumed:
see "the paths-ignore filter discriminates" below.

**The state now.** CI is hosted. The self-hosted runner stays *registered and
idle* as a fallback for the next time minutes run out. To switch back, change
`runs-on: ubuntu-latest` to `runs-on: [self-hosted, linux-x64-docker]` on all six
jobs — the **custom** label, never bare `self-hosted`, which would also match any
runner registered later including one without Docker, and every job here needs a
Docker daemon for its `container:` and `services:` blocks. The git bootstrap and
browser cache would need to come back with it; they live in PR #57's history
rather than being carried here as dead weight. `PYTHONDONTWRITEBYTECODE` is
already in `ci.yml` for exactly that eventuality: inert on hosted, load-bearing
on self-hosted, so switching back is one edit instead of two.

**Do not re-derive this.** Going self-hosted was right under a hard quota and is
wrong without one. The trigger changes are keepers either way.

## The paths-ignore filter discriminates

`ci.yml` ignores `docs/**` and `*.md`, then negates `!CLAUDE.md` and
`!.github/workflows/**`. `CLAUDE.md` is matched by `*.md`, so if the negation
were ignored, a change to the rulebook would silently skip every test.

Proved on 19 August with two throwaway pull requests, because one alone could not
settle it — CI running on a `CLAUDE.md` change is equally consistent with the
filter working and with the filter being inert:

- **PR #60**, changing *only* `CLAUDE.md`: all six jobs **ran**.
- **PR #61**, changing *only* `docs/work-queue.md`: the six jobs **skipped**.

`gitleaks` was the control in both — `secret-scan.yml` carries no path filter, so
its presence proves the event fired and that a missing job is suppression rather
than silence. Both pull requests were closed once the answer was recorded;
the branches are pending deletion.

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

**DONE, 18 Aug.** `l10n.et.balance.sheet`, `l10n_et_reports` 42 -> 60 tests,
CI floor 400 -> 418.

**Bigger than its queue line, on purpose.** Written naively it would have copied
~150 lines of section and coverage machinery out of the P&L, and two copies of
one check drift apart quietly — one gets a fix, the other keeps the bug, both
green. So the PR is two commits: extract `l10n.et.statement.mixin` and prove the
P&L suite runs UNCHANGED (42 tests, 0 failed, 0 skipped, not one assertion or
golden moved), then add the balance sheet on top. Two commits so a red CI has
one suspect.

**Three checks, not two.** The identity; the **cross-statement** check (result
for the period vs what the P&L reports for the same dates); and coverage.

**Re-measured 19 Aug after the rebase, in CI.** The figures previously recorded
here came from a hand-built `scratch_readiness` database that no longer exists
and cannot be reproduced, so they are replaced by the goldens the suite actually
asserts on the July-2026 fixture — which are reproducible on every run:
**total assets 22,450.00 = total liabilities and equity 22,450.00**, difference
**0.00**, with the result for the period **-63,000.00** equal to the profit &
loss's net profit to the cent. Coverage: every balance-sheet account classified,
`unclassified: none`, with off-balance accounts excluded from the denominator
and counted separately on the statement.

**Red proofs, re-run 19 Aug on the rebased branch, one throwaway branch each so
the two breaks could not contaminate one another.** Counts and names written
down before running:

| Break | Predicted | Observed |
|---|---|---|
| C — current liabilities removed from the shipped section table | 9 failures, named | **9 failed, 0 errors, of 432** — an EXACT set match |
| D — cross-statement check made to consult itself instead of the P&L | 1 failure, named | **1 failed, 0 errors, of 432** — the one named |

D's single failure is a strict subset of C's nine. `l10n_et_reports` ran **60
tests** in both. **Skips: 16 in the whole run, 0 in `l10n_et_reports`** — the 16
are `sapian_theme` app-rail and backend-footer tests skipping on
`websocket-client module is not installed`, they skip identically in the green
run, and they are covered by the dedicated browser job which installs it. The
module under test skipped nothing in either direction.

**One aborted run, discarded rather than reported.** The first attempt at proof
D restored the previous break with `assert 'current_liabilities' not in src` —
which is **always false, because `non_current_liabilities` contains that
string**. The restore silently did nothing and the run measured C+D together,
returning the same 9 failures. It was thrown away and D was re-run in isolation.
A substring guard on a name that is a suffix of another name is a guard that
cannot fire.

### 6. #50 — genuinely red from 09:59 UTC, four hours before the incident

**Never diagnosed. Diagnose before fixing** — a fix aimed at an undiagnosed red is
a guess. Moved down the queue on 18 Aug precisely because that diagnosis is
unbounded. Windows verification stays **OWED BY THE OPERATOR** in the PR body
(rule 4): Linux evidence is not proof for a Windows bug.

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

## Deliberately NOT in this queue

**The compliance dashboard** (register entry 13). It needs the **two e-Tax CSVs**,
which nobody has supplied, and it is the next major piece after this list. It is
not forgotten and it is not deprioritised — it is **blocked on information**, and
the register's "Still owed by Zemichael" section is where that unblocks.
