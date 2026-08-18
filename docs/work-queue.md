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
| 1 | **TIN on documents** | **IN PROGRESS** |
| 2 | #51 — re-run, merge if green | todo |
| 3 | #50 — diagnose before fixing | todo |
| 4 | Profit and loss | todo |
| 5 | Balance sheet | todo |
| 6 | #49 — remove the write-tripwire, make the fix order-independent | todo |
| 7 | Palette additions | todo |
| 8 | PR 4 — the four remaining "Powered by Odoo" mails | todo |
| 9 | Landing slot and grid toggle — Phase A discovery first | todo |
| 10 | Branch cleanup — 35 remote branches | todo |

---

### 1. TIN ON DOCUMENTS — design approved, build it

Design: `docs/design-tin-identifier.md`. Blocker; ahead of the P&L because a
client is sending non-compliant invoices *today*.

**Done when:** the invoice is sent through `account.move.send.wizard`, captured at
the **SMTP boundary**, its PDF text extracted, and **both** TINs asserted in the
bytes — and the guard **fails loudly if the renderer is unpatched** rather than
passing on the half it cannot see.

Not: flipping `is_invoice_report`. That fixes one document and leaves 17
external-layout blocks guarded on an empty `company.vat`.

### 2. #51 — re-run now the incident is over, merge if green

Ten minutes. It was never diagnosed as red on its merits; it was caught by the
GitHub incident.

### 3. #50 — genuinely red from 09:59 UTC, four hours before the incident

**Never diagnosed. Diagnose before fixing** — a fix aimed at an undiagnosed red is
a guess. Windows verification stays **OWED BY THE OPERATOR** in the PR body
(rule 4): Linux evidence is not proof for a Windows bug.

### 4. PROFIT AND LOSS — design approved

Design: `docs/design-pl-account-types.md`. **Account types first, then the
report** — the grouping belongs in `l10n_et_base` beside `CORE_ACCOUNT_FIXES`, in
three-digit rules, nine accounts. `592100 "Other"` stays **unclassified** until
the accountants answer, and the tie-out must **name it as unclassified** rather
than absorb it.

Tie-out, approved as proposed: net profit vs the ledger, and
`112 of 112 accounts classified, unclassified: none`.

### 5. BALANCE SHEET

After 4 and 5 the reporting blocker (register entry 27) is cleared.
**Trial balance and general ledger are deliberately NOT in this queue.**

### 6. #49 — the write-tripwire and load order

Remove the write-tripwire probe from **shipping** code, and make the fix
**order-independent**. 132's green was luck: our module moved between 26/30 and
27/30 across identical runs. **The guard must force `mail_bot` to load after us,
not hope for it.**

### 7. PALETTE ADDITIONS — one PR

Focus ring and outline inside `.o_sapian_auth`, outline on "Choose a user", and
the property guard **enumerating every interactive control**. It must run on a
page **with a stored user list**, or it cannot see the element that started this
(register entry 1). Fix the CDP `TimeoutError` that made the first attempt
establish nothing — an attempt that establishes nothing is rule 3.

### 8. PR 4 — the four remaining "Powered by Odoo" mails

Three `auth_signup` templates into the existing `sapian_theme_auth_signup` bridge
(they are `mail.template` data records, so they need a `body_html` override), and
the `im_livechat` transcript into a **new** bridge. Register entry 4.

### 9. LANDING SLOT AND GRID TOGGLE — Phase A discovery first

**Report which stock overview holds the slot and what tiles each renders. Do not
pick one yourself.** Register entry 12: the landing page becomes a configurable
slot so swapping it later is a data change, not a code change.

### 10. BRANCH CLEANUP

35 remote branches. Delete the merged ones; **list what was kept and why.**

---

## Deliberately NOT in this queue

**The compliance dashboard** (register entry 13). It needs the **two e-Tax CSVs**,
which nobody has supplied, and it is the next major piece after this list. It is
not forgotten and it is not deprioritised — it is **blocked on information**, and
the register's "Still owed by Zemichael" section is where that unblocks.
