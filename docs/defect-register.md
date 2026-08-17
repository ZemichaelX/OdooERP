# SapianERP — defect register

Observed, not inferred. Each entry says what was seen, where, and whether it is
confirmed on current master, on Zemichael's tenant, or only in CI.

Last updated: 17 August 2026.

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

**8. Withholding tax has no threshold logic and no buyer test**
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

What *is* wrong is that there are no conditions. `INV/26-27/0003` applies
withholding to a **1,100 birr** sale of goods when the threshold is **20,000**,
and applies it *instead of* the 15% VAT rather than alongside it, so a
VAT-registered seller issued an invoice with no VAT.

Withholding needs **three tests**, none of which exist:

1. **Is the buyer a withholding agent?** A government body, a PLC or Share
   Company, or a WHT-registered organisation — yes. An ordinary individual
   buying for personal use — no. Needs a flag on the partner.
2. **Is the value over the threshold?** 20,000 goods / 10,000 services, judged on
   the **transaction or supply contract**, not the individual invoice.
3. **Does the supplier have a valid TIN and business licence?** If not, the buyer
   must withhold **30%**, and it becomes a final tax.

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

**10. The transport allowance exemption is not implemented**
— rule **RESOLVED** 17 Aug. No payslip carries a non-taxable allowance and
`taxable_income = gross` on all six, so no exemption logic can be observed.

The rule is the **lower of 2,200 and a quarter of the salary.** Accountant 2:
*"Below 2200 or quarter of the salary"* and, to the direct question,
*"That is exactly correct."* Accountant 1 had given only the 2,200 cap — which is
what always binds above roughly 8,800 birr salary, so her answer was incomplete
rather than wrong.

The safer default this register had already chosen turns out to be the actual
rule. Build `min(25% × salary, 2,200)`, keep the cap and the percentage as
settings so a directive change is a settings edit, and show on the payslip which
limit bound.

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

---

**9. The website record is still called "My Website"**
Verified on tenant, 17 Aug. The browser tab reads `Login | My Website`. The
`website` record's name was never moved off Odoo's default, so it leaks into the
tab title, the page metadata and some mail templates. Zemichael is fixing this
one in Settings on his tenant.

**The code owed is prevention, not that fix:** `scripts/build_demo.sh` should
seed the website name from the company name, so a fresh demo never ships "My
Website" and nobody has to remember the Settings step. Same shape as the
launcher-defaults provisioning call — installing the module is not enough.

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
