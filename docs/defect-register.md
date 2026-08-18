# SapianERP — defect register

Observed, not inferred. Each entry says what was seen, where, and whether it is
confirmed on current master, on Zemichael's tenant, or only in CI.

Last updated: 17 August 2026.

**Entry numbers are identities, not an ordering.** A new entry takes the next
free number and keeps it for life — including when it moves to Closed. Two
branches numbering independently is how 9, 23, 24 and 25 each briefly existed
twice on 18 Aug; check the highest number in the file before adding one.

**Read the status words literally.** *Verified on tenant* means someone looked at
`demo_allapps` on Zemichael's machine after upgrading it. *Green in CI* means
nothing about the tenant — see rule 5 below.

---

## The five rules this project keeps re-learning

These belong in `CLAUDE.md`. They are here because every entry below is an
instance of one of them.

1. **A secret in a transcript is a published secret.**
2. **A success signal that can be produced by doing nothing is not a success
   signal.**
3. **A run that could not start is not a run that failed.**
4. **Platform-specific fixes must be verified on that platform.**
5. **The environment that verifies is not always the environment that runs.**

Rule 5 has fired five times:

| # | Where | Shape |
|---|---|---|
| 1 | `ir.asset._fill_asset_paths` | Module installed in the database, absent from the addons path of the process serving the bundle |
| 2 | #47's auth tests | Every local run had `website`, which drags in `auth_signup`; the theme-alone CI job did not |
| 3 | The SapianBot rename | A data record applies at install (`mode='init'`) and is skipped at upgrade (`mode='update'`, `d_noupdate` true). CI installs; clients upgrade |
| 4 | The 17 Aug audit | Claude Code cannot reach Zemichael's machine, so it built its own `demo_allapps` and measured that instead of saying "could not measure" |
| 5 | #47 and #48 themselves | Merged and green for a day while the tenant still served pre-#47 code, because nothing had ever pulled and upgraded |

A corollary, from instance 4: **a substitute for the thing asked about is not a
measurement of it.**

---

### Rule 2, worked example: the renderer that could not render what the guard asserted on

**This is not a sixth rule. It is rule 2 in a costume nobody recognised**, and it
is recorded here because the costume is good enough to fool a careful reader.

*A success signal that can be produced by doing nothing is not a success signal* —
and a PDF guard running on a renderer that cannot draw the thing it asserts on is
exactly that. It cannot fail. It is not a guard; it is a decoration that returns
green.

**What happened, 17–18 Aug.** The readiness assessment measured customer invoices
by extracting text from the rendered PDF — deliberately, because reading the
template proves nothing about the bytes a customer receives. It reported that the
invoice carried no supplier TIN.

Half of that was true and half was unprovable, for a reason invisible from the
result. Odoo splits a report into `bodies, res_ids, header, footer, …`
(`ir_actions_report._prepare_html`) and hands the header to wkhtmltopdf as
`--header-html`. **An unpatched-Qt wkhtmltopdf ignores it.** The container was
running Ubuntu's `wkhtmltopdf 0.12.6` — no `(with patched qt)` — so
`is_patched_qt` was `False` and **every report header was silently absent from
every PDF measured.**

- The **buyer** TIN lives in the body → genuinely absent, genuinely proved.
- The **seller** TIN lives in the header → **would have been absent whatever the
  field contained.** The assertion could not have failed differently.

Proved by fixing the renderer rather than by argument: installing
`wkhtmltox 0.12.6.1-3` — `0.12.6.1 (with patched qt)`, the build the `odoo:19.0`
image ships — the same invoice rendered **75,016 bytes instead of 30,259**, and
the before/after became discriminating:

| State | Seller TIN in PDF | Buyer TIN in PDF |
|---|---|---|
| `vat` empty | **no** | **no** |
| `vat` populated | **yes** | **yes** |

**The general form, which is what to carry forward:**

> **A PDF guard must assert that the renderer can render what it is asserting on,
> or it is not a guard.**

Concretely, for anything that reads rendered output:

- **Assert the renderer's capability first**, and **fail** on a renderer that
  cannot draw the asserted region. Do not skip — a skip is silent, and silence is
  what this rule is about. `is_patched_qt` is one line to check.
- **Know which stream your assertion lives in.** Header, body and footer are three
  different pipelines in wkhtmltopdf, and only one of them survives on an
  unpatched build.
- **Prefer the body.** Our own reports print the TIN in the body and were correct
  on the broken renderer; core's letterhead was not. A legal identifier in a page
  header is one paper-format change away from vanishing — which is precisely how
  this was discovered.
- The same shape applies beyond PDFs: a screenshot guard on a headless browser
  that never painted, an asset guard on a bundle that was not built, a mail guard
  on a transport that discarded the body.

### Rule 2, worked example: the HTML named `.pdf`

Found while building the TIN guard, one layer beneath the renderer example above.

`_render_qweb_pdf` **returns HTML during tests** unless `force_report_rendering`
is in the context (`ir_actions_report.py:1027`). So the invoice attachment the
guard captured at the SMTP boundary was named `INV_....pdf`, was **8,083 bytes**,
and began `<!DOCTYPE html>`.

**And it contained both TINs.** Every content assertion in the guard — seller TIN
present, buyer TIN present — would have passed, on a document that was not a PDF
and that no customer would ever receive. The guard would have been green, the
feature would have shipped, and the thing it was written to prove would have been
untested.

Only the format check saw it:

```python
self.assertTrue(pdfs[0].startswith(b"%PDF-"), ...)
```

**The general form:**

> **When asserting on a rendered artefact, assert its FORMAT before its CONTENT.
> Correct content in the wrong format passes silently.**

Cheap to apply everywhere: magic bytes for a PDF, a parse for JSON or XML, an
image decode for a PNG, a non-zero page count for a document. One line, and it is
the line that stands between "the bytes say what we want" and "the bytes are the
thing we think they are".

### Rule 2, standing check: `noupdate` is three for three

**Not a lesson any more — a check to run before writing the XML.**

An XML record targeting a core `ir_model_data` row whose `noupdate` is true is
**skipped with no error and no log line**. Worse than silent: the loader prints
`loading <module>/data/<file>.xml` while writing nothing, so the log positively
suggests the work happened.

Three for three, on three separate occasions:

| Target | Where it bit |
|---|---|
| `base.partner_root` | #49 — the SapianBot rename would have reached new databases only |
| **`base.et`** | The TIN work, 18 Aug — `vat_label = TIN` loaded and did nothing |
| The chart template | Entry 26 — a template is read once at chart load and never re-read |

For `base.et` the flag was read directly after the failure:

```sql
select module, name, noupdate from ir_model_data where module='base' and name='et';
--  base | et | t
```

**The standing check, before writing XML that targets a core xmlid:**

1. Read that row's `noupdate` flag.
2. If it is **true**, the value **must be set in code** — a post-init hook for
   fresh installs and a versioned migration for existing databases. Both, because
   CI installs and clients upgrade.
3. Assert the **value**, never the file loading. Every one of these three was
   caught by a test that read the resulting state; none would have been caught by
   checking that the data file was listed in the manifest or appeared in the log.

---

### 45. #50 is not red on its own account — it is carrying #49's defect

Diagnosed 18 Aug, work-queue item 6, which said *"#50 is genuinely red on its
own account"*. **That was wrong**, and this entry corrects both the queue and
the note under the CI-incident entry above.

#50 has **one** red job of nine, and it is not a job that touches #50's code:

| Job | Result |
|---|---|
| **SapianBot survives an upgrade** | **FAILURE** |
| Odoo integration tests | success |
| App rail rendered in a browser | success |
| Launcher defaults reach the page | success |
| Calendar installs, and uninstalls, alone | success |
| Theme login vs website | success |
| Lint + reference golden tests | success |
| gitleaks (×2) | success |

Phase 1 of that job passed — `0 failed, 0 error(s) of 10 tests`. Phase 2, the
**upgrade**, failed **4 of 10**:

```
FAIL: TestTheSystemPartnerIsOurs.test_the_bot_address_is_ours
  AssertionError: 'odoobot@example.com' != 'sapianbot@example.com'
FAIL: TestTheSystemPartnerIsOurs.test_the_bot_carries_our_name
  AssertionError: 'OdooBot' != 'SapianBot'
FAIL: TestTheSystemPartnerIsOurs.test_the_bot_is_not_named_after_odoo
FAIL: TestTheBotSignsTheChatter.test_a_system_authored_message_is_signed_by_us
```

That is **entry 44 / work-queue item 7 verbatim** — the OdooBot revert on
upgrade, the order-dependent `mail_bot` load. #50 changes
`scripts/update_local.sh` and nothing else; it has no causal connection to the
system partner.

**Consequences for the order of work:** item 6 has nothing to fix. Fixing item 7
is what turns #50 green. Two further facts mean #50 cannot close on code alone:

1. Its base is five merges behind master, so it needs a rebase and a fresh run
   whatever happens to the bot job.
2. **Its Windows verification is owed by the operator** (rule 4) and no work
   here can supply it.

**How the wrong reading survived:** the queue recorded a red and a timestamp
without recording WHICH JOB was red. A PR-level "red" is an aggregate over nine
jobs; the aggregate is never a diagnosis. Name the job and the assertion, or the
note is a rumour with a timestamp attached.

### 46. GitHub Actions stopped placing jobs at 10:52, and the failures look like code failures

Observed 18 Aug. **The first version of this entry blamed the wrong thing** — see
"what the evidence actually supports" below; the correction is part of the
lesson.

From 10:52 onward **every job of every new run failed in 3–4 seconds** with
`runner_id: 0`, no downloadable log (HTTP 404 on the log endpoint) and a
completely empty check-run `output`. Runs created BEFORE that point kept running
to completion normally:

| Run | Created | Result |
|---|---|---|
| 143 (master) | 10:45:44 | 6 of 6 green |
| 144 (branch) | 10:50:30 | 5 of 6 green when cancelled |
| 145, attempts 1–3 | 10:52–10:58 | every job failed in 3–4s |
| reopen-triggered run | 10:59:24 | same |
| gitleaks — a DIFFERENT workflow file | 10:52 | same |
| PR #56's run, created with **nothing else running** | 11:03:27 | same |

**Two tells that this is not our code**, and both are cheap to check:

- **The clock.** A red in 3 seconds against a green that never takes less than
  ~2 minutes is not a red. Rule 3 already says this.
- **The absence of a log.** A job that failed has a log. A job with `runner_id:
  0` and a 404 on its log never started.

**What the evidence actually supports.** The first version of this entry said
the cause was *this session stacking five runs in seven minutes* and exhausting
a concurrency allowance. **That is refuted.** The run created for PR #56 at
**11:03:27 — with every other run finished and the account completely idle for
three minutes — failed exactly the same way.** Contention cannot explain a
failure that reproduces at zero load.

What the evidence does support is a **hard cutover at ~10:52**: everything
created before it runs, everything created after it is rejected instantly,
across multiple workflow files, persisting while idle. That is the shape of an
**account-level Actions quota or spending limit**, and it needs the operator, not
code. Heavy use earlier in the day may have brought the limit forward; it is not
the mechanism.

**The correction is the lesson.** "I did five runs, then runs broke" is a
sequence, not a cause, and it was written into this register as fact after one
supporting observation and before the one test that could refute it — creating a
run while idle. **A causal claim needs the control case**, especially a
self-blaming one, which feels rigorous and so gets less scrutiny than it
deserves.

**Do not re-run.** Re-running a run whose jobs never placed reproduces it
exactly — three attempts proved that — and reopening the PR to force a fresh run
reproduced it too. Treat CI as having given **no verdict in either direction**
(rule 3), and wait for the operator.

**Three mistakes made here, recorded because each is repeatable:**

1. **The clock was read wrong.** A job six minutes into a ten-minute step was
   called "21 minutes, hung" and **cancelled** — throwing away a run that was
   5 of 6 green, and the only run that had exercised the new code. Print the
   current time next to the job's `started_at`; do not estimate elapsed time
   from memory of how long a conversation felt. This one stands regardless of
   what caused the outage.
2. **A correct diagnosis was abandoned on the strength of that same bad
   arithmetic.** Concurrency was identified first, then rejected because "at
   10:58 nothing else was running" — which was false.
3. **A watchdog was built that could not fire.** A polling loop authenticated
   with `$GITHUB_TOKEN` against `api.github.com` directly; that token is not
   valid for direct calls (the proxy answers *"GitHub access is not enabled for
   this session"*), so the loop would have spun silently to its timeout. It
   printed nothing on the failure path because the JSON parsed fine and simply
   never matched `completed`. **A poller must assert that its poll SUCCEEDED,
   not merely that the terminal state has not appeared yet** — otherwise "not
   finished" and "cannot see" are the same output. Same family as rule 2.

## The branding rule

**Inward-facing surfaces are Sapian's. Outward-facing surfaces are the
client's.**

- **Backend** — navbar, sidebar, launcher, footer. Ours. Sapian teal `#14454F`
  for every client.
- **Auth pages** — login, reset, signup. The application's front door, used by
  the client's staff. **Ours, teal.**
- **The client's public website** — home, shop, contact. **Theirs**: their logo,
  colours, copy.
- **Documents and email to their customers** — invoice, quotation, receipt.
  The client's identity, plus our attribution, which they may switch off.

Attribution string, one everywhere: **"Powered by SapianERP"** → sapiantech.com.
Product name markets; company name (`Sapian Technologies PLC`) does the legal
line in the backend footer.

**The bot is the system speaking** — neither vendor nor client — so it is
`SapianBot`, a constant in `vendor.py`, not an `ir.config_parameter` (which
`base.group_system`, i.e. the client, can write). Accepted consequence, on the
record: the bot authors chatter messages that portal users see, so this name
reaches the client's customers on a portal invoice.

---

## Open

**1. "Choose a user" on `/web/login` renders the client's colour**
Verified on tenant, 17 Aug, after upgrading past #47.

Not a specificity contest — an **element-type gap**. Our scope block is two
rules: `.o_sapian_auth .btn-primary` and `.o_sapian_auth a`. The control is
`<button class="o_user_switch_btn btn btn-sm btn-link">`
(`web/static/src/core/user_switch/user_switch.xml:25`). `.btn-link` doesn't match
the first rule; the second matches `<a>` and not `<button>`. The winning
declaration is Bootstrap's `.btn-link` colour, rebuilt from the website editor
palette by `html_editor` — Selam green. "Reset Password" beside it is an `<a>`
and renders teal, which is the giveaway.

**Fix shape, decided:** stop enumerating elements. Scope Bootstrap's *variables*
inside `.o_sapian_auth` rather than adding a rule per control, or we chase
elements forever.

**2. ~~A purple wedge at the top-left of both auth pages~~ — CLOSED, NOT OURS**
Closed 17 Aug. It disappears in an incognito window with extensions disabled, so
it was a **browser extension badge**, not anything this repository serves.

Recorded rather than deleted because the elimination was earned twice and both
halves are reusable. First, `--btn-bg` IS what this Bootstrap build reads —
measured on the upgraded tenant, `.o_skip_to_content` computes `#14454F` and the
winning rule is `.o_sapian_auth .btn-primary`, beating `.btn-primary`'s
`#714B67`. So the candidate could not have stayed purple. Second, the element is
`[x,y,w,h] = [-1,-1,1,1]`, clipped to `rect(0,0,0,0)` and off-viewport, and Tab
on the tenant goes straight to "Choose a user" — there is no skip-to-content
link in the tab order at all.

**3. Five shipped templates hardcode a purple** — pinned
Journal Notification, New eInvoices Notification, two Purchase templates, 2FA.
All internal or supplier-facing. The sweep goes red if a sixth appears or a
customer-facing one joins them.

**4. Four more outgoing mails still say "Powered by Odoo"** — approved, PR 4
One concern: *no mail leaving a client's system advertises Odoo.*

- `auth_signup.set_password_email` — new employee
- `auth_signup.portal_set_password_email` — **the client's own customer**
- `auth_signup.mail_template_data_unregistered_users`
- `im_livechat` transcript, `im_livechat/data/mail_templates.xml:105` — **the
  client's website visitor**, with a UTM link

The three `auth_signup` ones are `mail.template` data records, not views, so they
need a `body_html` override. They go in the existing `sapian_theme_auth_signup`
bridge. The livechat one needs a new `im_livechat` bridge.

**4b. The module graph order is not stable between identical CI runs**
Measured 17 Aug, same commit, two runs of the `SapianBot survives an upgrade`
job: `sapian_theme_mail` loaded at **27/30** and then at **26/30**. `mail_bot` is
in that set and loads at **22/30 locally** — before us — so a defect that depends
on loading after `mail_bot` will reproduce intermittently forever.

**Consequence for whatever the SapianBot fix turns out to be: it must not depend
on our module loading after `mail_bot`.** An ordering that happens to hold today
is not a fix.

**5. Odoo's identity elsewhere in Discuss** — #49, red, not merged
Nine leaks swept 16 Aug against a 229-module database. Six in scope for #49
(a–f), two deferred to PR 4 (g livechat mail, h chatbot avatar), one left alone
(i, "FOR WEBSITES BUILT WITH ODOO" — internal config screen, and the sentence is
true).

**Correction to this register:** an earlier entry called *"Looking for help"* an
Odoo channel. It is not — it is `im_livechat`'s conversation **status** and the
Discuss sidebar category grouping conversations in it, alongside "In progress"
and "Waiting for customer". The client's own support queue, hidden when empty.
Written up from a screenshot without reading the code.

**6. Every one of our 16 modules renders as garbage in Settings → Apps**
Confirmed and quantified 17 Aug. All 16 addons ship `README.md`; none sets a
`description` key; `ir_module.py:204` renders whatever it finds through
`docutils.core.publish_string`, which is reStructuredText. One `-u mail` log
carried **43** `ERROR/3` lines. The recurring ones are structural, not cosmetic:
`Undefined substitution referenced: "---"` (our horizontal rules),
`Unexpected indentation`, `Inline literal start-string without end-string`
(backticks), `Line block ends without a blank line` (tables).

Client-visible. Low urgency, trivial fix: set `description` explicitly, or ship
an RST README.

**7. Company logo is a broken image in outgoing email** — unconfirmed
Referenced at a `localhost` URL Gmail cannot reach. **Probably a local
artifact.** Confirm on a real domain before treating it as a defect.

**8. Withholding has no buyer test and no contract aggregation**
**Rewritten 17 Aug after measurement. The previous title — "no threshold logic and
no buyer test" — was half wrong, and the half that was wrong had been written from
reading the symptom rather than exercising the engine.** See
`docs/product-readiness.md` flow (d) for the run.

**Thresholds and the supplier-credentials test both EXIST, and both discriminate.**
Measured on a scratch tenant, four bills, expectations written down before running:

| Bill | Withheld |
|---|---|
| goods 5,000 (under the 20,000 threshold) | **nothing** |
| services 8,000 (under the 10,000 threshold) | **nothing** |
| services 15,000 (over 10,000, under goods' 20,000) | **450.00** at 3% |
| goods 50,000, supplier with **no TIN** | **15,000.00** at 30% |

Row three proves the services threshold is a separate figure from the goods one;
row four proves the punitive path fires on credentials. The configuration the
engine read is effective-dated, not hard-coded: `WHT 3% from 2025-08-01`,
`threshold_goods=20,000`, `threshold_service=10,000`, `rate_standard=0.03`,
`rate_punitive=0.30`, `punitive_respects_thresholds=True`.

**The "instead of VAT" claim below is also refuted for the purchase side:**
50,000 + 7,500 VAT − 15,000 WHT = **42,500**, so VAT is charged alongside
withholding. The 1,100-birr sale invoice that prompted this entry was a
hand-selected tax on a sale line — the sale side has no automation to have got it
wrong.

**What is genuinely absent, and this is now the whole of the entry:**

1. **The buyer-is-a-withholding-agent test.** Measured: a 60,000 sale to Mebrat
   Construction **PLC** and a 60,000 sale to a **walk-in individual** produce
   byte-identical invoices — `15%` VAT only on both. There is no `res.partner`
   field matching `agent`, and no `res.company` field matching `wht`/`withhold`.
   Moot on purchases, where the buyer is always the company; **the gap is entirely
   on the sale side.**
2. **Contract aggregation.** Measured: two 9,000 goods bills to one supplier on
   one day withheld nothing and raised no warning, activity or chatter note. A
   search of every model in the database for `contract`/`agreement` returns only
   `hr.contract.type` and `publisher_warranty.contract` — there is no
   supply-contract concept. The engine applies the threshold **per transaction**,
   which is accountant 1's rougher reading; the tax reference resolves the unit to
   **the agreement** on accountant 2's stronger answer.
3. **The company setting decided below** — *show the withholding deduction on the
   invoice*, defaulting ON — **was never built.** The sale-side tax
   `3% WHT (Withheld by Customer)` exists and, applied by hand, is correct:
   100,000 + 15,000 VAT − 3,000 = **112,000**, debiting *Withholding Receivable on
   Sale*. Only the decision to apply it is missing.

**Lesson worth keeping:** this entry asserted three missing tests from one bad
invoice. Two of the three were present and working. An entry that says "none of
these exist" needs a run behind it, not an inference from a symptom.

---

The presentation question below stands unchanged, and was the useful half.

Two accountants answered on 17 Aug and they **disagree about presentation** while
agreeing on everything that decides the amount.

- Accountant 1: *"No, it shows Before VAT, VAT and Total Price."* The 3% is taken
  by the buyer at payment, evidenced by a withholding receipt.
- Accountant 2: *"Yes. A single commercial tax invoice can display both the 15%
  VAT added and the 3% WHT deducted to clearly show the net amount due"*, and
  gives the structure: base → VAT added → 3% deducted **from the base only** →
  net payable.

**Reading: showing it is permitted, not required.** Accountant 1 describes her own
house practice. So this becomes a company setting — *show the withholding
deduction on the invoice* — defaulting to ON, because it tells the customer what
to pay. **This corrects an earlier entry in this register that called the invoice
model wrong; it is not.**

The three statutory tests, for reference — **2 and 3 are built and proved above;
1 is not:**

1. **Is the buyer a withholding agent?** A government body, a PLC or Share
   Company, or a WHT-registered organisation — yes. An ordinary individual
   buying for personal use — no. Needs a flag on the partner. **ABSENT.**
2. **Is the value over the threshold?** 20,000 goods / 10,000 services.
   **BUILT per transaction; the contract unit is ABSENT.**
3. **Does the supplier have a valid TIN and business licence?** If not, the buyer
   must withhold **30%**, and it becomes a final tax. **BUILT and proved.**

See `docs/ethiopian-tax-reference.md`.

**9. Payroll periods and the Ethiopian filing month**
Downgraded 17 Aug from "confirmed defect" after the second accountant answered.
The two run payroll differently and both are correct:

- Accountant 1 calculates salaries **by Ethiopian month**.
- Accountant 2 processes **by Gregorian month**, explicitly *"to align with bank
  statements and simplify reconciliation"*, then files in the following Ethiopian
  month.

**So the payroll cycle is a business choice and must be configurable.** What is
not optional is the **mapping to the Ethiopian filing month and its window** —
that is the same for both, and it is the part the module does not have.

Smaller than the rework this register previously described.

**11. A client with `website_sale` can never open customer self-registration**
The override returns `b2b` unconditionally, and Settings → Website still reads
"Free sign up" while sign-up is closed. Wanted: a Sapian-level setting defaulting
to CLOSED that the override consults.

**12. The apps-grid button only goes one way**
The launcher is an overlay; closing it reveals the page underneath. When the
launcher **is** where the user landed there is nothing underneath, so closing
resolves to nothing.

**Design decided, not built:** the landing page becomes a **slot** — one
configurable action, so swapping it later is a data change, not a code change.
Closing the launcher resolves to the previous action if one exists, otherwise to
the landing action. Never nothing.

**Correction to an assumption:** the GraceERP screen used as the reference —
*All RFQs / To Send / Waiting / Late*, *Avg Order Value*, *Lead Time to
Purchase* — is **stock `purchase`**, not a GraceERP build, and is already
installed here. A "dashboard like GraceERP's" is free today; it is just a
*departmental* page, not a company front door.

**13. The compliance dashboard does not exist**
The SapianERP app opens the Module Catalog — a configuration list where clicking
a row edits a name and a tier. That is the front door of the product.

**Reshaped 17 Aug, twice, by asking two accountants what actually takes their
time. Neither said payroll.**

| Question | Accountant 1 | Accountant 2 |
|---|---|---|
| Longest job | **VAT** | **Bank reconciliation**, then reconciling AP, AR and the VAT / 3% WHT balances |
| Always checked by hand | **"Excel summations"** — does not trust the totals | Manual voucher checks: that invoice, receipt, purchase order and **delivery note match**; that 15% VAT and 3% WHT are accurate; ledger coding; management signatures |

They point at the same thing from two directions: **the work is making numbers
agree, and neither of them trusts the tax figures.** That, not a declaration
calendar, is what the dashboard is for.

Tiles the evidence supports, in order:

1. **What doesn't reconcile.** Unmatched bank lines first — accountant 2's
   longest job, and the one Odoo's bank statement matching already half-solves.
   Then AR, AP, and the VAT and WHT control accounts against what was declared.
2. **Tax figures showing their working.** Both accountants re-check VAT and WHT
   by hand. A tile that displays a total *and its components* so it can be
   verified without exporting to Excel attacks the distrust directly. This is
   cheap and high-value.
3. **Documents that don't match** — invoice against purchase order against
   delivery note. Accountant 2 does this by hand every month, and it is the same
   defect as *goods invoiced but never delivered*: Odoo moves stock on a delivery,
   never on an invoice, so a trader who bills over the counter has permanently
   wrong inventory and COGS and nothing complains.
4. **Ethiopian filing month status** — which month is open and how many days are
   left in the window. Small, and it is the one thing GraceERP's Gregorian-first
   product cannot do naturally.
5. **Possible invoice splitting** — several sub-threshold invoices to one partner
   under one agreement, which is exactly where the withholding contract rule
   bites and where the system cannot decide for itself.

**Also surfaced and not a dashboard item:** accountant 2 checks *"all required
management signatures are present"* by hand. That is an approval workflow the
product does not have.

**14. Nothing deploys a merged PR to the tenant**
New 17 Aug, and the most consequential process defect found so far. #47 and #48
were merged, green and invisible for a day. Zemichael's tenant served pre-#47
code — reset button green, no logo on the reset page — matching this register's
own pre-#47 description line for line.

`scripts/update_local.sh` exists on `claude/update-local-deploy` to close this.
**Verified on Linux through a compose shim only.** The real compose path and
Git-Bash-on-Windows behaviour are UNVERIFIED — see rule 4.

Its verification caught two defects in itself, the second serious: `-i` on
`auto_install` bridges pulled in `l10n_et_calendar`, `account` and `purchase`,
taking a base+theme database from a handful of modules to **65**. On a client
tenant that is an accounting and purchasing rollout dressed as a deploy.
`auto_install` means *"install me when my dependencies are already present"*, not
*"install me and my dependencies"*. The rule now reads Odoo's own `get_manifest`
normalisation rather than re-interpreting the flag.

**15. sapiantech.com has expired** — go-live gate, not a defect
Expired a few weeks before 17 Aug. Decision: leave the links wired, because this
is a demo. **Two things must happen before any client sees this build:** renew
the domain, and re-check `support@sapiantech.com` in the backend footer, which is
currently dead mail on every page of the product.

**23. The payslip PDF prints an exempt allowance as "Taxable: Yes"**
New 17 Aug, measured on a scratch tenant (`docs/product-readiness.md` flow (e)).
Carried forward from item 10, which asked for the opposite behaviour.

The rendered payslip for an employee on basic 6,000 with a 2,000 transport
allowance reads:

```
Earnings   Description                    Amount        Taxable
           Basic Salary                   6,000.00 Br   Yes
           Transport allowance August     2,000.00 Br   Yes
           Gross                          8,000.00 Br
```

**Only 500.00 of that 2,000.00 was taxable.** The engine knows it — PAYE was
computed on 6,500 and is correct — so the document contradicts the calculation
behind it. The word **"exempt" does not appear anywhere in the payslip**, checked
against the rendered text rather than the template.

Consequences: an employee or a labour inspector reconciling the payslip by hand
cannot arrive at the PAYE shown, and the payslip is the document staff argue
about. The tax reference asks explicitly to *"show on the payslip which limit
bound"* — that is unbuilt, and the column that does exist states the wrong thing.

Ledger and filings are unaffected. **OUR CODE.** Fix shape: the split is already
computed, so the payslip template needs the exempt/taxable portions and the
binding limb, not new arithmetic.

**24. The bank salary file exports with empty account numbers and does not warn**
New 17 Aug, measured. **This is rule 2 exactly** — an export that succeeds while
carrying nothing a bank can use.

Two newly-hired employees with no bank account produced a named, sized, reported
export:

```
Employee Name,Bank Name,Account Number,Net Pay
Meseret Bekele — መሰረት በቀለ,,,6780.00
Tesfaye Alemu — ተስፋዬ አለሙ,,,9395.00
TOTAL,,,16175.00
```

`_l10n_et_identifier_warnings()` returned `[]`. Reading its source: it checks
**employee TIN** and **POESSA pension ID** and nothing else. There is no bank
check. The six demo employees *do* carry account numbers (`1000200030001`…`6`), so
the field exists and is normally populated — **the failure appears only for a
newly-hired employee, which is the routine event**, and it appears in the file the
client hands to their bank.

The TOTAL row reconciles to the run's net (16,175.00), so even the internal
cross-check passes. Nothing in the artefact distinguishes "exported correctly"
from "exported unusable".

**OUR CODE.** Fix shape: extend the warning function that already exists for the
other two identifiers — it is the right place and it already has the reporting
path into chatter and the report banner.

**25. Onboarding collects no company email and no outgoing mail server, so a
customer invoice leaves as `OdooBot <odoobot@example.com>`**
New 17 Aug, captured at the SMTP boundary, not inferred from settings.

Sending a posted customer invoice by email produced a real message whose `From:`
header read, verbatim: **`OdooBot <odoobot@example.com>`**. Measured causes on the
tenant as the product's own onboarding leaves it:

| Setting | Value |
|---|---|
| `company.email`, company partner email | `False`, `False` |
| admin user email / partner email | `False` / `False` |
| `ir.mail_server` records | **0** |
| `mail.default.from` / `mail.catchall.domain` | `False` / `False` |

`sapian_core/wizard/sapian_onboarding_wizard.py` collects `company_name`, `tin`,
`street`, `city`, `fiscal_year`, `logo`, `primary_color` and the module picks. It
collects **no email address and no mail server**. So a tenant provisioned entirely
through the product's own go-live path is *by construction* unable to send a
customer-acceptable email, and the send reports success either way — rule 2 again.

**These are two defects wearing one symptom, and they must not be merged.** #49
and PR 4 address Odoo's **name** appearing in outgoing mail. This entry is about
the **absence of an address to send from**. Fixing every "Powered by Odoo" string
in the product leaves this invoice going out from `odoobot@example.com`; and
conversely, configuring SMTP by hand leaves the strings. Neither fix touches the
other.

This is also the branding rule pointed at the most outward-facing surface there
is — an invoice to the client's own customer — and it is in the `From:` line
rather than the footer.

**OUR CODE (onboarding gap) + CONFIGURATION.** Fix shape: onboarding asks for the
company email and either SMTP credentials or an explicit "mail is configured
elsewhere" acknowledgement, and go-live refuses to report success without one.

**26. Every client hits Goods in Transit on their first purchase** — **BLOCKER**
New 17 Aug, measured (`docs/product-readiness.md` flows (b), (f), (g)).

On the demo tenant, **12 of 12 products have no product category** (`categ_id` is
`False`) while three categories exist unused. With no category and no account on
the product, Odoo falls back and resolves purchases to **`230100 Goods in Transit`,
an `asset_current` account**. Measured consequences:

- That account stands at **453,800.00** across the tenant's bills, and **nothing
  clears it.**
- The `STJ` (Inventory Valuation) journal holds **0 entries** after a completed
  receipt of 200 units and a completed delivery of 40.
- So **no cost of goods sold is ever posted**: the P&L shows revenue with no cost,
  gross margin cannot be read from the accounts, and inventory — a trader's
  largest asset — never reaches the balance sheet.

**ROOT CAUSE, corrected 17 Aug after chasing it to the bottom. The first version
of this entry blamed the missing product categories. That was wrong, and it would
have produced a fix that changed nothing.**

A default IS wired. It is wired to the wrong account, by **Odoo's own Ethiopian
localisation**:

- `odoo/addons/l10n_et/models/template_et.py` lines 32–33 set
  `'expense_account_id': 'l10n_et2301'` and `'income_account_id': 'l10n_et1100'`.
- `l10n_et2301` is **`230100 Goods in Transit`, `account_type = asset_current`**.
- Odoo's generic `chart_template.py` propagates `company.expense_account_id` into
  `ir.default` for `product.category.property_account_expense_categ_id` — measured
  on the tenant as **id 18 = 230100**.
- **The discriminating measurement:** the existing *Goods* category, before being
  touched, already read `property_account_expense_categ_id = 230100`. So assigning
  every product to a category would have moved nothing. The missing categories
  made this *look* like our demo data's fault; it is not.

**So: core `l10n_et` designates a current-asset transit account as the default
expense account for every Ethiopian company on the chart.** A client who
categorised their whole catalogue correctly would still land in `230100`.

**Attribution: STOCK ODOO (core `l10n_et`) as the source, OUR CODE for not
overriding it.** `l10n_et_base` exists to extend that chart and this is exactly
what it is for. The severity does not move: whoever's mistake it is upstream, it
ships to our clients under our name.

**Fix shape, therefore, is not what the first version of this entry implied:**
override `expense_account_id` in our chart extension so every Ethiopian company
gets a real expense account. Assigning products to categories is a secondary
tidy-up, not the fix.

**THIS IS NOT ONLY OUR DEFECT — it affects every Odoo-based Ethiopian deployment.**
The mapping lives in Odoo's own `l10n_et` chart template, so any company anywhere
running Odoo on the Ethiopian chart books its purchases into a current-asset
transit account by default, sees no cost of sales in its P&L, and overstates
profit until someone notices. That includes every competitor building on the same
localisation.

**FILED UPSTREAM: [odoo/odoo#282865](https://github.com/odoo/odoo/issues/282865)**
— *"[l10n_et] Default expense account is a current asset (230100 Goods in
Transit), so purchases never reach the P&L"*, opened by ZemichaelX against 19.0,
17 Aug 2026. A one-line change to `expense_account_id` in `template_et.py` fixes
it for every Ethiopian deployment, competitors included.

**Our override is not a stopgap. It is the only mechanism that ever moves an
existing database**, and that is worth stating precisely rather than as a hedge.

A chart template is read **once**, when the chart is loaded. It is not re-read on
upgrade. So a merged upstream fix corrects `template_et.py` for databases created
*afterwards* and touches **no existing tenant at all** — not on upgrade, not on
restart, never. Every Ethiopian database already in production keeps `230100`
until something rewrites `company.expense_account_id` and the `ir.default` row
behind it, and the only thing that does that is
`_l10n_et_base_fix_default_expense_account`.

Upstream therefore fixes the *next* deployment; we fix *this* one. Both are worth
doing, and neither substitutes for the other.

Separately, `data-templates/`, which CLAUDE.md describes as spreadsheet import
templates for onboarding, contains **only `README.md`** — so there is no import
path that could carry product accounting fields either.

**Why BLOCKER and not SERIOUS.** *Cheap to fix* and *blocking* are different axes,
and an earlier draft of the readiness report conflated them: it reasoned that the
client could still operate and file, and graded it SERIOUS on that basis. But this
is an **accounting system sold to a trading company**, and a P&L that shows revenue
with no cost is not a product that company can use to run itself, whatever it can
still file. The fix being an afternoon's work does not change what it blocks.

The periodic-valuation default is stock Odoo's and is a legitimate choice.

**Blast radius, measured rather than asserted** (`docs/product-readiness.md` flow
(m)): correcting the account for **one** product and posting **one** 54,000.00
bill moved that purchase out of the asset account and **reduced reported profit by
exactly 54,000.00** (294,852.00 → 240,852.00), taking cost of sales from 22.6% to
36.8% of revenue. `230100` still holds **453,800.00** of earlier purchases, since
the correction is not retroactive. The books balance in both states — a balanced
ledger cannot detect a classification error, which is why nothing complained.

---

*Entries 27–38 were all raised by the 17 Aug readiness assessment
(`docs/product-readiness.md`), which listed ten items as owed. It is twelve here,
not ten: the reconciliation item split into a missing UI (28) and a missing
importer (29), which are a build and a market question respectively, and the
payments absence (30) was recorded in that assessment as NOT NEEDED YET rather
than on the owed list. Both were called for explicitly. Padding a list is a fault;
so is dropping a real item to hit a round number.*

**27. There is no profit & loss, balance sheet, trial balance or general ledger**
— **BLOCKER**. New 17 Aug, measured (`docs/product-readiness.md` flow (m)).

The build ships **four** `account.report` records and all four are tax reports.
A search across `ir.actions.act_window`, `ir.actions.client` and
`ir.actions.report` for Profit / Loss / Balance Sheet / Income Statement / Trial
Balance / General Ledger returns **NONE**, and no menu exists for any of them.
`account_reports`, the Enterprise module that carries them, is **not in the addons
path**.

An Ethiopian PLC needs a P&L and a balance sheet for its annual business-profit
return and for its bank. Correct VAT and correct payroll do not substitute. This
was invisible from tier 1 because every tier 1 flow reads the ledger directly.

Computed by hand from posted lines, the books **do** balance (assets − liabilities
− equity − profit = 0.00 before and after the entry-26 experiment), so this is a
missing *presentation* layer, not a broken ledger.

CLAUDE.md's Epic B says of statements: *"Skip: … IFRS statement engine (use
Odoo/OCA reports)."* **That assumption was never closed** — no OCA financial
report module is vendored (`vendor/` holds only `oca_web`) and Community ships
none.

**Attribution: STOCK ODOO (Community/Enterprise split) + OUR CODE (an unclosed
planning assumption).**

**Decision pending, with the coverage facts measured 17 Aug from the OCA `19.0`
branches (nothing vendored):**

| | `account_financial_report` | `mis_builder` |
|---|---|---|
| General ledger | **YES** | via KPI expressions |
| Trial balance | **YES** | via KPI expressions |
| Profit & loss | **NO** | engine only, no template ships |
| Balance sheet | **NO** | engine only, no template ships |

`account_financial_report` provides Aged Partner Balance, General Ledger, Journal
Ledger, Open Items, Open Items Partner, Trial Balance and VAT Report; a search of
the module for profit/balance-sheet terms returns nothing. `mis_builder` ships
**no report templates at all** — its only `mis.report` record is
`mis_report_expenses` in `mis_builder_demo` — so it is a framework in which a P&L
must be authored against the `et` chart, which is work we do either way.

Both look maintained: 34 and 35 non-translation commits in 90 days, 17 and 6
distinct non-bot authors, manifests at `19.0.0.0.19` and `19.0.1.2.0`, last
substantive commits 29 Jul and 3 Aug 2026. Both are **AGPL-3**, where
`web_responsive` is LGPL-3 — a different obligation for a sold product, to be
checked by someone qualified before shipping.

**Cost not previously counted: this is four repos, not two.** Both depend on
`date_range` (OCA/server-ux) and `report_xlsx` (OCA/reporting-engine), neither of
which is in Odoo core.

**Recommendation, not a decision:** take GL and trial balance from OCA — pure
plumbing with no Ethiopian character worth owning — and **build P&L and balance
sheet ourselves in the shape of the VAT report's GL tie-out**, which prints the
total, the ledger's total and `OK` beside them. Both accountants said they re-add
computed numbers by hand; a statement that proves it reconciles is the thing
neither Odoo nor OCA nor GraceERP does.

**HALF CLOSED, 18 Aug — the profit & loss exists** (`l10n.et.profit.loss` in
`l10n_et_reports`, work-queue item 4). Rendered on the readiness tenant for
calendar 2026: revenue **397,345.00**, cost of sales **54,350.00**, gross profit
**342,995.00**, operating expenses **85,643.00**, net profit **257,352.00**, in a
**70,225-byte PDF** whose extracted text carries every one of those figures. Both
checks printed on it: net profit **257,352.00 against a ledger total of
257,352.00, difference 0.00**, and `61 of 62 accounts classified` naming
`592100 Other`.

The chart half of this entry closed first (PR #53): core `l10n_et` types all 58
of its expense accounts `expense`, so before that no P&L of any origin — ours,
OCA's, Enterprise's — could have shown the 342,995.00 gross profit line at all.

**Both checks were proved red, with the failure counts stated before running:**

| Break | Predicted | Observed | Skips |
|---|---|---|---|
| A — coverage check forced to always report `ok` | 4 failures, named | **4 failed of 33**, the four named | 0 |
| B — cost-of-sales section removed from the shipped table | 7 failures, named | **7 failed of 33**, the seven named | 0 |

**Still open on this entry: the balance sheet** (work-queue item 5), and the
deliberate decision that trial balance and general ledger are **not** being built
— OCA's `account_financial_report` has both.

**One wording defect the rendered PDF caught, and no test would have.** The first
real statement reconciled exactly and still printed *"This statement does not
reconcile"*, because the banner fired on `tie_out_ok`, which is the AND of the
amount check and the coverage check. An accountant who reads that once, finds the
amounts perfect, and learns to skip the banner is how the real mismatch gets
missed three months later. The banner now distinguishes the two, and a test
asserts both wordings in the rendered document.

**28. Bank reconciliation has no screen — but Community already finds the matches**
New 17 Aug, measured (flow (i)). **Half defect, half product opportunity.**

`account_accountant`, which carries Odoo's bank-reconciliation widget, is
Enterprise and absent. Measured on this build: **no reconciliation menu**
(`ir.ui.menu` search returns `[]`), and the only related action is
*"Reconciliation Models"*, which configures rules rather than doing the work. A
statement line posts `Bank` dr / `Bank Suspense` cr, and clearing it means opening
the entry, repointing the suspense line's account and partner, saving, then
selecting the pair in the ledger and reconciling.

**Measured effort:** 2 operations per matchable line, 3 for a line needing an
account decision — **7 operations for a 4-line statement**. Derived (not observed
in a browser, and labelled as derived): ~10–12 clicks per line, so **600–2,400
interactions a month** on a 60–200-line statement. This is accountant 2's stated
**longest monthly job**.

**The opportunity, and why this entry is not just a complaint:** the hard half is
already solved in Community. Odoo's own `_get_default_amls_matching_domain`
narrowed 23 candidates to **exactly one** on **3 of 4** lines with no help. What
Enterprise sells is the *screen* that shows that suggestion and accepts it in one
click. A one-click accept screen over machinery that already exists takes the job
from ~10–12 interactions per line to ~1.

Two cheap wins beside it: the seeded **`Bank Fees` reconcile model is
`trigger=manual`** and could be `auto_reconcile` with Ethiopian bank-charge
wording (CBE, Awash, Dashen); and see entry 29.

Proof the manual path works: the whole statement cleared, suspense to **exactly
0.00**, ledger balanced at 0.00 over 91 lines.

**Attribution: STOCK ODOO (Community/Enterprise split).** Nothing of ours is
broken; we inherit the gap silently. **Severity: SERIOUS**, and the strongest
build-rather-than-fix candidate found.

**29. No bank-statement importer exists in Community at all** — commercial
New 17 Aug, measured (flow (i)). **An absence in the platform, not in us.**

Odoo 19 Community's addons contain **no statement import module whatsoever** — no
OFX, no QIF, no CAMT; `account_bank_statement_import` is not present under any
name. The only route in is the generic `base_import` CSV/XLSX importer against
`account.bank.statement.line`, or typing.

**Why this is commercial rather than a defect:** the formats that would matter here
are not OFX or CAMT anyway — they are **what Ethiopian banks actually issue**
(CBE, Awash, Dashen, Abyssinia), which no upstream importer will ever cover
because no upstream author has those files. An importer that reads Ethiopian bank
exports with a saved column mapping is a differentiator no global vendor will
build, it removes the typing that precedes entry 28's clicking, and together the
two turn the longest monthly job into a short one.

**Owed first, before any build: sample statement exports from the banks the client
actually uses.** This sits with the two e-Tax CSVs on the "Still owed by
Zemichael" list — the same shape of problem, and the same rule: we cannot build a
parser from a description.

**Severity: NOT NEEDED YET** to go live (statements can be typed), **but high
commercial value.**

**30. Zero payment providers are enabled, and no Ethiopian provider exists in
Odoo** — commercial
New 17 Aug, measured (flow (l)). **Also an absence in the platform, not in us.**

The customer portal works: a portal user logs in, sees **only their own** invoices
(another customer's invoice correctly redirects to `/my`), and downloads a real
**217,264-byte** PDF. What they cannot do is pay.

- **24** payment providers ship (Wire Transfer, Adyen, Stripe, …); **0** are
  enabled — every one is `state=disabled`.
- Searching every provider for `telebirr` / `CBE` / `Chapa` / `Amole` / `birr`
  returns **nothing**. **No Ethiopian payment provider exists in Odoo at all.**
- On an unpaid invoice the portal renders **no payment section whatsoever**, so
  the customer is not even told that paying is unavailable.

Telebirr is how a large share of Ethiopian consumers and small businesses actually
move money, and no global ERP will add it. CLAUDE.md already defers payments until
a client signs; this entry records the size and shape of the gap so that deferral
stays a decision rather than an oversight.

**Severity: NOT NEEDED YET** for a first client whose customers pay by transfer
and cheque — the portal is a working sales asset today without it.

**31. The VAT credit carried forward is never carried, and a declaration has no
state**
New 17 Aug, measured (flow (c)). Two defects in one model.

August's declaration ends *"VAT credit carried forward 8,550.00"*. The September
declaration, created immediately after, reports **output 0.00, input 0.00, net
0.00**. The complete field list is `company_id, csv_export_file,
csv_export_filename, currency_id, date_from, date_to, input_vat_total, name,
net_vat, off_chart, output_vat_total` — **no field for a brought-forward credit**
(a search for forward/carry/previous/opening returns `[]`). Each month is computed
in isolation and the 8,550.00 the client is owed exists only as a sentence in last
month's PDF, tracked in the accountant's own Excel — which is the thing the
product's pitch says it removes.

Second: there is **no `state`, `locked`, `filed` or `submitted` field**, and
creating a second 1–31 August declaration succeeded — two records, same name. So
there is no record of *what was filed*, and a figure can be regenerated after
filing and silently disagree with the return the MoR holds.

**Attribution: OUR CODE** (`l10n_et_reports`). **Severity: SERIOUS**, not a
go-live blocker — a first month can be filed from a freshly generated report.

**Worth preserving in whatever fix lands:** this report's **GL tie-out block**
(`Output VAT vs GL,300700,4950.00,4950.00,OK`) is the best thing found in the
whole assessment and the model for entry 27.

**32. Withholding appears only at posting, so a draft bill's total is wrong**
New 17 Aug, measured (flows (b) and (g)).

A vendor bill for 90,000.00 of goods reads **103,500.00** in draft and posts at
**100,800.00**; a 176,000.00 bill reads 202,400.00 and posts at 197,120.00.
Nothing in the draft shows the withholding about to be deducted, because
`_l10n_et_apply_wht` runs in `_post`.

The posted figure is the correct one, so no ledger number is misstated. The cost
is that the **pre-post check an accountant actually performs** — accountant 2's
manual voucher check in item 13, matching the bill against the supplier's invoice
before posting — is done against a total the system will not use.

**Attribution: OUR CODE** (`l10n_et_base`). **Severity: SERIOUS.** Fix shape:
evaluate on change of lines/partner/date as well as at post, or show the pending
withholding on the draft as an informational line; the engine is already
idempotent by design, which makes re-evaluation safe.

**33. No Ethiopian filing month exists anywhere in the product**
New 17 Aug, measured (flows (c) and (e)). **Extends item 9 rather than replacing
it** — item 9 established that the payroll cycle is a business choice and the
mapping to the Ethiopian filing month is mandatory; this entry measures that the
mapping is absent from the VAT side too.

- `l10n.et.payroll.run`: complete field list contains **no field** matching
  `ethio`, `ec_` or `filing`. The run is named `Payroll 2026-08` and every PDF
  prints `Period: 08/01/2026 – 08/31/2026`.
- `l10n.et.vat.declaration`: same — bounded by Gregorian `date_from`/`date_to`,
  named `2026-08`, PDF printing `08/01/2026 – 08/31/2026 (monthly, Proc
  1341/2024)`.
- `l10n_et_calendar` is **uninstalled** in the shipped set, so no Ethiopian date
  exists in the database at all.

For payroll the reference is VERIFIED and unambiguous: the declaration for one
Ethiopian month is filed during the *following* Ethiopian month, and the mapping
*"is what is mandatory, and it is the same for both"* cycles.

**For VAT the reference is silent on the period basis, and the product has
silently chosen the Gregorian reading.** If the MoR's VAT period is an Ethiopian
month, every declaration is mis-sliced by about a week at both ends — and the
error is undetectable from inside, because the figures tie out perfectly to a GL
sliced the same wrong way. **A tie-out cannot catch a period boundary.** That is a
question for the MoR call, not something to build on.

**Attribution: OUR CODE (absent feature).** **Severity: SERIOUS**, and per item
13(4) it is the one thing a Gregorian-first competitor cannot do naturally.

**34. `data-templates/` ships only a README — no import templates exist**
New 17 Aug, measured (flow (g)). CLAUDE.md describes `data-templates/` as
*"spreadsheet import templates for onboarding"*. The directory contains **only
`README.md`**.

So there is no supported path for getting a client's products, partners or opening
balances into a new tenant, and — relevant to entry 26 — no template that could
carry product accounting fields. Onboarding currently collects a company profile
and module picks (entry 25) and then stops.

**Attribution: OUR CODE (absent).** **Severity: SERIOUS for onboarding**, and it
is what turns entry 26 from a demo-data curiosity into something every client
meets.

**35. Every internal user can read product cost prices**
New 17 Aug, measured (flow (h)) through an authenticated session, not a code read.

A user holding **only** `base.group_user` — no accounting, sales, purchase or HR
rights — successfully called `product.product search_read` with `standard_price`
and got all 12 products with buying **and** selling prices (Binding Wire 200.00,
Cement OPC Dangote 1,000.00, Cement PPC Derba 910.00).

For a trading company **the buying price is the margin**, and it is readable by
any employee with a login — a storekeeper, a driver, a new hire.

**Attribution: STOCK ODOO default.** **Severity: SERIOUS for this business**, and
it is a **go-live configuration decision** (restrict the cost field or the product
form) rather than a code defect. Recorded because a first client will not think to
ask, and because it is the kind of thing an owner discovers after it has gone
round the yard.

**Everything genuinely sensitive was correctly blocked**, and that deserves saying:
payslips, wages via `hr.version`, journal entries, invoices, orders, journals, tax
configuration, and — field by field — employee TIN, pension ID, private address,
bank account, birthday and ID number. Our own `l10n_et_tin` and
`l10n_et_pension_id` are group-restricted alongside Odoo's own, which is CLAUDE.md
rule 8 honoured rather than asserted.

**36. The customer-facing portal page's `<title>` is `Odoo`, and the bot is still
`OdooBot`**
New 17 Aug, measured (flow (l)) on the invoice page a client's customer sees.

- `<title>` renders as **`Odoo`**. The footer is correct — `Copyright © Selam
  General Trading PLC` and **`Powered by SapianERP`** — so the theme reaches the
  body and not the title tag. This is a **new instance** of the branding rule on an
  outward-facing surface, not covered by items 3, 4 or 5, which concern mail
  templates and Discuss.
- `res.users` uid 1 is `name='OdooBot'`, login `__system__`, and the string
  **`SapianBot` appears nowhere in `addons/`**. The register's branding rule states
  the bot *is* `SapianBot`; on current master that is a decision, **not built** —
  consistent with item 5 recording #49 as red and unmerged. The portal invoice page
  shows `-- OdooBot --` in the chatter signature, reaching the client's customer
  exactly as the branding rule's "accepted consequence" paragraph anticipated,
  except with Odoo's name instead of ours.

**Attribution: OUR CODE.** **Severity: COSMETIC** — but on the client's customer's
browser tab. This entry **confirms #49 is still outstanding by measurement**; it
does not replace it.

*Guard against a false reading:* the same page shows `Salesperson: OdooBot`. That
is an **artefact of the assessment**, which created every document through a script
running as `SUPERUSER_ID` (uid 1) — not a product defect.

**37. A delivery drives stock negative with no warning and no block**
New 17 Aug, measured (flow (f)). `Rebar 16 mm` had **0.0** on hand; a delivery of
40 units validated cleanly to **−40.0**. Odoo permits negative stock by default.

For a trader this is how *goods delivered but never received* enters the data —
the twin of item 13(3)'s *goods invoiced but never delivered*, which was also
confirmed by measurement in the same flow: **posting a customer invoice for 25
units moved stock by exactly 0.00.**

**Attribution: STOCK ODOO (default configuration).** **Severity: SERIOUS**, and it
is a **go-live configuration and training decision** — someone must decide whether
counter sales go through a delivery, and the client must be taught that an invoice
is not a goods issue.

## Product default decisions — not defects

*These are choices the product has made by inheriting Odoo's defaults. Both are
correct behaviour for the software and arguably wrong for the market. Recorded so
the default is a decision on the record rather than an accident. **Neither is
decided here.***

**39. VAT is added on top of the shelf price at the counter** — decision pending
New 17 Aug, measured (`docs/product-readiness.md` flow (n)).

A POS sale of 5 × *Cement OPC Dangote 50kg* priced at **1,100.00** produced
untaxed 5,500.00 + VAT 825.00 = **6,325.00** — i.e. **1,265.00 a bag** at the
till. The taxes are configured tax-EXCLUSIVE (`price_include` off), which is
Odoo's default and is what our demo data implies.

**Ethiopian retail shelf prices are normally VAT-inclusive**, so a customer handed
6,325.00 for goods marked 1,100.00 will dispute it at the counter, every time.

**The trade-off, not a verdict:**

- Odoo fully supports tax-inclusive pricing; this is a tax-configuration setting,
  not a code change.
- **For a counter/retail client, inclusive is almost certainly what they want** —
  the sticker is the price.
- **For a B2B trader invoicing construction firms, exclusive is the convention** —
  the invoice shows base, VAT and total separately, which is also what the VAT
  invoice format expects.
- Selam General Trading PLC is **both**, which is exactly why this needs deciding
  rather than defaulting: the same product sells over the counter and on a
  30-day invoice.

**The question is whether tax-inclusive should be OUR default**, per price list or
per POS config rather than globally. **STOCK ODOO** default inherited.
**Severity: not a defect** — but it is a go-live conversation with every retail
client, and getting it wrong is visible to their customers on day one.

**40. Periodic valuation means no per-sale cost of sales, so there is no gross
margin** — decision pending
New 17 Aug, measured (flows (f), (j), (m), (n)).

After two POS sales of cement, `511100 Cost of Goods and Services` was
**unchanged** and the `STJ` (Inventory Valuation) journal held **0 entries**.
Every product category ships `property_valuation = periodic` and
`cost_method = standard`, which is Odoo's default.

Under periodic valuation Odoo posts **no cost entry when something is sold**. Cost
reaches the P&L as *purchases*, and a physical stock count at period end adjusts
it. That is a legitimate, widely used method — and note that **entry 26's fix was
still necessary and is unaffected**: it decided *which account* purchases land in,
which matters under either method.

**What it costs the client:**

- **No gross margin per product, per sale or per day.** For a trader, that is the
  number they care about most — the whole business is buy low, sell higher.
- The P&L's cost line reads *"what we bought"*, not *"what we sold"*, until
  someone counts the stock.
- Inventory does not sit on the balance sheet between counts (measured: 452,000.00
  of stock on hand, `235100 Stock` reading **0.00**).

**What automated (perpetual) valuation would give:**

- A cost entry on every sale, so gross margin is readable per product and per day.
- Inventory continuously on the balance sheet.
- **At the price of** configuring valuation and stock-input/output accounts per
  category, a costing method decision (standard / FIFO / average — note **every**
  category currently reads `standard`), and a discipline the client's staff must
  actually keep: perpetual valuation punishes sloppy receipts far harder than
  periodic does, because every mis-scanned delivery immediately misstates COGS.

**The trade-off is real in both directions and is not decided here.** A small yard
that counts stock monthly and trusts nobody's data entry may be genuinely better
off periodic. A client who asks "what did I make today?" cannot be answered
periodic. **STOCK ODOO** default inherited. **Severity: not a defect** — but it is
the single most consequential default in the product for a trading client, and it
interacts with the P&L design now being specified.

---

**38. An employee cannot read their own payslip**
New 17 Aug, measured (flow (k)). An employee record was linked to a real user
account, the way an employer enabling self-service would; that user then got
**AccessError** reading `l10n.et.payslip`.

`l10n.et.payslip` inherits `['base']` — **no `portal.mixin`**, no mail thread — and
a search of all of `addons/` for `/my/` portal controllers returns **nothing**.
There is no owner-scoped record rule, only the HR-group ACL that correctly blocked
the plain employee in flow (h). So there is nothing to switch on.

Alongside it: `hr_holidays`, `hr_expense` and `hr_attendance` are **uninstalled**,
so there is no time-off request and no expense claim either. Those are
**CONFIGURATION** — the modules are present in the addons path, stock Odoo and
free. The payslip half is **OUR CODE** and is a build.

**Severity: NOT NEEDED YET** for a first client with seven employees who will be
handed printed payslips. Recorded so the absence is a decision on the record: the
moment a client with fifty staff asks for self-service, the payslip half is not a
setting.

---

**41. The website record is still called "My Website"**
Verified on tenant, 17 Aug. The browser tab reads `Login | My Website`. The
`website` record's name was never moved off Odoo's default, so it leaks into the
tab title, the page metadata and some mail templates. Zemichael is fixing this
one in Settings on his tenant.

**The code owed is prevention, not that fix:** `scripts/build_demo.sh` should
seed the website name from the company name, so a fresh demo never ships "My
Website" and nobody has to remember the Settings step. Same shape as the
launcher-defaults provisioning call — installing the module is not enough.

---

**42. A partial GitHub outage is a total CI outage for us, because five jobs
have no git** — hardening item, its own PR

**Not a defect in this repository, and nothing here is broken by it.** On
17 Aug 2026 a GitHub incident opened at **13:40 UTC**: *"Archive downloads and
raw repository content downloads are experiencing an approximate 50% error
rate."* Archive download is exactly the call `actions/checkout` makes when git
is absent, so five of our six CI jobs lost their checkout while the sixth
carried on.

The clock is what identifies the cause, and it rules out every candidate that
lives in a branch:

| Run | Started (UTC) | Result |
|---|---|---|
| master CI #131 | 12:33 | green, 11m19s |
| #49's run 132 | 12:51 | container jobs checked out and ran; 11m41s |
| **incident opens** | **13:40** | |
| #51's run 133 | 14:11 | five jobs dead at checkout; **2m02s** |

Same branch content, same `pull_request` event, same repo settings on either
side of 13:40. **Zemichael did not change the Workflow permissions setting**, and
the `Resource not accessible by integration` string in the annotations is the
incident, not a token — do not record a permissions lesson from this. `ci.yml`
is byte-identical between master and #51, and its checkout steps are identical
to #49's, so the branch was never a candidate either.

**The real exposure, argued on resilience and not on today's red:** five jobs
(`integration-tests`, `calendar-standalone`, `theme-with-website`, `rail-render`,
`launcher-defaults`) declare `container: odoo:19.0`, and that image ships no git.
`actions/checkout` therefore falls back to the REST archive endpoint on every
one of them, every run. The sixth, `lint-and-fast-tests`, runs on the runner,
which has git, and it was untouched all afternoon. So a 50%-error partial outage
of one GitHub endpoint takes 5/6 of our suite to zero, and our only surviving
signal is the job that cannot run an Odoo test.

Two ways to remove the dependency, costed but **not** to be built as a reaction
to this incident:

1. Install git in the container before checkout — small, but keeps CI on an
   invocation path no human runs, and puts Debian's mirrors in the critical path.
2. Check out on the runner and invoke Odoo through
   `docker compose -f docker/docker-compose.yml run --rm odoo …` — removes the
   fallback entirely and makes CI exercise the operator's real command (rule 5
   working for us). Costs, from reading the compose file: `odoo` is `build: .`,
   so CI builds the Dockerfile rather than pulling the pinned image; compose
   hard-fails without `docker/.env` (`DB_PASSWORD` is `:?`-required) and needs
   `config/odoo.runtime.conf` to exist as a file, both gitignored, and neither
   may be created by `preflight.sh::ensure_runtime_conf`, which prints the
   password it generates; every stdout-reading floor must be re-proved to still
   **discriminate** through `compose run`; and the two Chrome jobs install Chrome
   inside the container today, so they are a redesign, not a port.

**While the incident is open, a CI result means nothing in either direction** —
at a 50% error rate a green run is luck and a red run is weather. Wait for
githubstatus.com to report resolved, then re-run **once**.

**What this does not excuse.** #50 is genuinely red on its own account: its run
started 09:59 UTC, nearly four hours before the incident. #49's bot-job failure
on run 130 also predates 13:40, so the OdooBot revert remains a real,
order-dependent defect and the traceback is still the next thing there.

> **Rule 3, with today as the example.** Five jobs that fail at checkout run no
> test body. Those were runs that *could not start*, not runs that failed — and
> **the duration said so before anything else did**: 2m02s against a consistent
> 11m30s across six prior runs, pass and fail alike. When a red arrives far
> faster than a green ever does, read the clock before reading the diff.

**43. Every CI job warns that Node.js 20 is deprecated**
Observed 17 Aug in the annotations of every job. `actions/checkout@v4` and
`actions/setup-python@v5` are being forced onto Node 24. Nothing is failing
today; it is a countdown. The fix is a version bump of both actions, in its own
PR, so that a change in checkout behaviour arrives on a run where it is the only
variable — which is precisely the property this afternoon lacked.

**44. Every branch push runs the whole suite twice**
`ci.yml` triggers on both `push` and `pull_request`, so a push to a branch with
an open PR fires two full runs of six jobs. Double runner time and **no extra
information**: same tree, same jobs, same result. The usual shape is to keep
`pull_request` for branches and restrict `push` to `master`, so master's own
history stays covered without paying twice for every branch commit.

---

## Claude Code's own open state, 17 Aug

Left here deliberately so a fresh session picks it up from the repository rather
than from a transcript (rule 5: the environment that verifies is not the
environment that runs — and a transcript is neither).

- **PR #49 is RED and must not be merged.** Its `SapianBot survives an upgrade`
  job fails at step 1. H2 is answered: the row reads `name='OdooBot'`,
  `email='odoobot@example.com'`, `image_sha1` equal to OUR file — so the hook
  wrote the image and something wrote exactly two fields back, as uid 1. The
  write-tracing probe is pushed and verified loading locally
  (`SAPIAN-TRACE res.partner.write is patched`, one captured write, ours, all
  three fields). **The CI traceback has not been read yet. Read it before
  proposing any fix**, and note what would have to be true for `mail_bot` to be
  responsible: its data block names only `odoobot_state`, so the write would
  have to reach `name` and `email` through `res.users` rather than from that
  block's fields.
  **A Claude Code Remote session cannot fetch that log — do not spend a session
  finding out again.** The jobs and check-runs APIs answer `403 Resource not
  accessible by integration` for the GitHub App token (while `list_workflows`
  and `list_workflow_runs` succeed, so it is a job-level scope gap), and the
  signed run-log ZIP lives on `results-receiver.actions.githubusercontent.com`,
  which the session egress proxy refuses at CONNECT. There is no third copy: the
  run has no artefacts. **The traceback has to come from the operator:**
  `gh run view 32031930149 --log | grep -n -A 30 'SAPIAN-TRACE write on partner 2'`,
  plus `grep -c` on the same string — two blocks are expected, and a count of 1
  means the probe never saw the write, which is a different problem from the one
  being chased.
- **The palette guard has ESTABLISHED NOTHING.** `TestEveryControlIsInThePalette`
  is written and committed, and its first run ended in a CDP `TimeoutError` —
  rule 3, a run that could not start. It is not known to pass, and it is not
  known to discriminate. The `SAPIAN-PALETTE` marker never printed, which is at
  least the CI grep's own failure mode behaving as designed.
- **Three approved Job 2 additions are NOT BUILT:** the focus-ring / outline
  colour inside `.o_sapian_auth` (colour and outline, not colour alone); a guard
  that enumerates controls on a page **with a stored user list**, because
  "Choose a user" only renders when a remembered session exists and a clean page
  is blind to the exact element that started this; and the timeout fix the guard
  needs before either can be measured.
- **PR #50's Windows verification is the operator's**, rule 4. Linux evidence
  through a compose shim is a substitute, not a measurement.

---

## Closed

*(Numbers are identities and do not renumber when an entry moves here. Item 10
began life in Open and keeps its number.)*

**10. The transport allowance exemption**
— **CLOSED 17 Aug. It was UNTESTED, not absent** — which is precisely the
distinction this entry was complaining about, so it is worth saying plainly: the
entry said *"no exemption logic can be observed"*, and it was right that nothing
could be observed. It was wrong to leave the reader with "not implemented" in the
title. **The logic was there the whole time; the demo data could not exercise it.**

**Implemented and seeded**, as `l10n.et.allowance.type` with the rule as
configuration rather than as constants:

| code | rule | ceiling ETB | ceiling % of basic |
|---|---|---|---|
| `transport` | capped | **2,200.00** | **0.25** |
| `hardship`, `medical` | exempt | — | — |
| `housing`, `position` | taxable | — | — |

**Both limbs verified 17 Aug** on a scratch tenant, figures hand-computed before
the run (`docs/product-readiness.md` flow (e)):

| Case | Which limb binds | Exempt | Taxable excess | Taxable income | PAYE | Result |
|---|---|---|---|---|---|---|
| basic 9,000 + transport 2,500 | the **2,200 cap** (25% = 2,250 is higher) | 2,200 | 300 | 9,300 | **1,475.00** | exact |
| basic 6,000 + transport 2,000 | the **quarter** (1,500 < 2,200) | 1,500 | 500 | 6,500 | **800.00** | exact |

The second row is the one that matters: it is the low-earner case accountant 1's
"flat 2,200" answer gets wrong, and the case the tax reference warns
*"under-taxes low earners and leaves the employer liable for the shortfall plus
penalties."* Eleven figures in total (gross, taxable income, PAYE, both pension
sides, net) matched hand arithmetic exactly across the two employees.

**One thing this entry asked for is still not done, and is carried forward as
entry 23:** *"show on the payslip which limit bound"*. The payslip PDF does the
opposite.

**16. The auth pages took their colour from the frontend palette**
— **FIXED, #47 (`a03d1bd`). Verified on tenant 17 Aug** after
`-u sapian_theme,sapian_theme_website,sapian_theme_mail
-i sapian_theme_auth_signup`.

Before, on the tenant: reset button `#1a7f4f` green, no logo. After: both auth
buttons teal, Selam logo on both, "Back to Login" and "Use a Passkey" teal.

The fix is a **scope**, not a palette override: `web.login_layout` sets
`o_sapian_auth` on the body, and the brand rule is scoped to that class instead
of `.oe_login_form`. Overriding the editor palette would have been the same
mistake pointed the other way — that palette is the client's.

Root cause: `html_editor` is `auto_install: True` and rebuilds Bootstrap's
`$theme-colors` from the editor palette, so `$o-brand-primary` never reaches the
frontend bundle.

*Two lessons.* The first red proof predicted 4 failures and got 3; chasing the
shortfall revealed the logo guard was unproven. The second proof matched on count
but failed a **different** test — the logo assertion was being satisfied by the
company name in `website`'s JSON-LD metadata, on a page with no logo block at
all. And the first CI run went red because every local run had `website`
installed: on the theme-alone database `/web/reset_password` is a 404. The route
list is now derived from what is installed, with a guard that the derivation
cannot shrink to nothing.

**17. The password-reset email said "Powered by Odoo"**
— **FIXED, #48 (`a49d38d`).** Measured before, as the public user:
`Powered by <a href="https://www.odoo.com?...' style="color: #14454F;">Odoo</a>`
— **our teal painting Odoo's name**, because #44 seeded the company email colour
and this template uses it. #44 could not have reached the string: the reset mail
is a standalone `ir.ui.view`, not a notification layout.

Now `Powered by SapianERP` → sapiantech.com, honouring
`sapian_email_attribution`; off removes the whole grey band, with a test that the
rest of the mail survives so "off" cannot become a way of breaking the email.

*Capture technique worth keeping:* `action_reset_password` wraps the send in
`contextlib.closing(cr.savepoint())` and rolls back unconditionally, so the
`mail.mail` row is discarded and a counting test reads identical before and
after a successful send. The tests read the body at the SMTP boundary via
`mock_mail_gateway`'s patch of `IrMailServer._build_email__`.

**18. The reset email was signed "Thanks, Public user"**
— **FIXED, #48.** It now signs as the **company, always** — not "the company
when no signature exists". The mail is not from a person; a machine sent it
because somebody forgot a password. Keeping `user.signature` would make the same
email say different things depending on who clicked, and would put an admin's
personal signature in front of a portal customer. `object.company_id`, not
`user.company_id`, so a multi-company tenant is signed by its own company.

**19. White rectangle in the top-left when the launcher is open**
— **FIXED, #46 (`7646fbb`). Confirmed on the tenant 16 Aug.**
Measured from screenshot pixels, not CSS: 9200/9200 page-background before,
3/9200 after. Region is 200×46, not the 250×60 first eyeballed.
`elementFromPoint` was useless — it answered `BODY.o_web_client`.

**20. The payroll engine's arithmetic**
— **VERIFIED CORRECT, 17 Aug**, independently recomputed against the statutory
table on all six payslips of `build_demo.sh`'s run, on both the progressive form
and the `rate × income − constant` form. Every figure exact.

| taxable | tax | net check |
|---|---|---|
| 1,800 | 0 | 1,800 − 0 − 126 = 1,674 |
| 3,500 | 225 | 3,030 |
| 6,000 | 700 | 4,880 |
| 10,000 | 1,650 | 7,650 |
| 12,000 | 2,250 | 9,050 |
| 25,000 | 6,700 | 16,550 |

**And the pension base is settled.** Payslip 5 is the only discriminating row —
basic 10,000, taxable overtime 2,000, gross 12,000 — and pension is **700**,
which is 7% of basic, not 840 of gross. The accountant says basic only. The
engine does basic only.

*Correction to an earlier entry in this register:* the demo data was called
"debris — duplicate payroll runs". That was Zemichael's hand-poked local
database. What `build_demo.sh` produces is one clean run with six employees
crossing every bracket boundary **including a discriminating allowance case**.
That is good demo data.

**21. The reset-password form confirms whether an account exists**
*"No account found for this login"* — user enumeration. **Verified stock Odoo.
Decision: no action.** Revisit before the first internet-facing client.

**22. The build verifier cannot measure a database with `website` installed**
`demo_allapps` failed verification because with `website` installed the root URL
serves the shop front, so the authenticated fetch of `/odoo` was served the login
page. The guard behaved correctly — it refused to report clean on a measurement
it could not take.

---

## Deferred by decision, on the record

- **Client logo at the bottom of the sidebar.** Reasons in
  `docs/SPEC-navigation-chrome.md`.
- **Item 5i**, "FOR WEBSITES BUILT WITH ODOO" — internal config screen, and true.
- **User enumeration on the reset form** — see 21.
- **`sapian_email_attribution` has a Settings UI as of #45**, so "the client may
  switch it off" is a promise a client can exercise.

---

## Still owed by Zemichael, not by code

- The Ministry of Revenues call on e-invoicing accreditation.
- **The two e-Tax CSV files.** Both accountants confirm the monthly filing is a
  CSV upload, and accountant 2 confirms there are **two**: one carrying Schedule A
  employment income tax per employee, and a separate one carrying the 18% pension
  total (11% employer + 7% employee). **Neither has attached an example.**
  Generating those two files is the single highest-value thing this product could
  do for either of them, and we cannot build it from a description. Ask again,
  and accept an old file with the names removed.
- The pension filing deadline, and whether it shares the income-tax window.
  Accountant 2 implies it does — both CSVs go up in the same 1st-to-30th window —
  but she was not asked directly.
- Whether the client is Category A or Category B, and what Category B actually
  pays. See the reference doc.
- The EFDA importer list.
