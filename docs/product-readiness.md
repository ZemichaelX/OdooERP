# SapianERP — product readiness assessment

**What this document is:** coverage, not defects. It asks what a small Ethiopian
trading company actually does, walks those flows end to end on a live database,
and records what happened. `docs/defect-register.md` remains the register of
defects; this file cross-references it by entry number and, at the end, lists the
new register entries this assessment owes.

**No fixes were made.** Where a fix was obvious it was written down instead.

Started: 17 August 2026.

---

## Where this was measured, and where it was not

This matters more than usual here, because defect register rule 5 —
*the environment that verifies is not always the environment that runs* — has
fired five times on this project, and its corollary is *a substitute for the
thing asked about is not a measurement of it.*

**Measured on:** a database called `scratch_readiness`, built from nothing inside
this session's own container on 17 Aug 2026.

**NOT measured on:** Zemichael's `demo_allapps`, `sapian_prod`, or any client
database. Nothing in this assessment touched them. Where a finding depends on
tenant state rather than on code, it is marked as such and is **not** evidence
about any tenant.

### How the container was built, since it is not the documented stack

The documented stack is Docker (`docker/docker-compose.yml`). **There is no
Docker daemon in this container**, so the stack could not be used and the
database was built natively instead. Recorded because it is a difference between
the environment that verified and the environment that runs:

| | Documented stack | This assessment |
|---|---|---|
| Odoo | image `odoo:19.0@sha256:e415f99…` | source clone `odoo/odoo` branch `19.0`, commit `ccce9fcc` (2026-06-29) |
| Postgres | image `postgres:16@sha256:33f923b…` | Ubuntu `postgresql-16` 16.13, local cluster |
| Python deps | image's own | `requirements.txt` into a venv, **two substitutions**: `psycopg2` → `psycopg2-binary`, and `python-ldap` omitted (build deps absent; no LDAP module is installed) |
| PDF engine | image's patched wkhtmltopdf | Ubuntu `wkhtmltopdf 0.12.6`, **unpatched Qt** — PDFs render, headers/footers are not the patched-build layout |
| Ethiopic font | `fonts-sil-abyssinica` in the image | **not installed** — so Amharic glyph rendering in PDFs is UNTESTED here and no claim is made about it either way |

The build followed `scripts/build_demo.sh`'s phase order, which is load-bearing
(country before chart, provisioning strictly after install):

1. `-i base --without-demo=all` → 14 modules.
2. company country set to `ET` before any chart loaded.
3. `-i sapian_demo_trader,sapian_theme,web_responsive --without-demo=all` → **84 modules**.
4. `sapian.demo.trader._provision_demo_tenant(adopt_existing=True)` →
   `>> provisioned: Selam General Trading PLC | chart: et | country: ET`, and
   launcher defaults applied to 2 users.

**84 modules, not 229.** The 229-module database is `--all-apps`, the navigation
-scale build. This assessment is deliberately run on the **shipped default set**,
because that is what a first client gets, and because a sweep across 229 modules
produces hundreds of findings that are all stock Odoo's. Tier 3 lists what is
therefore absent.

Scripts were run through a purpose-built runner (`/workspace/rt/run.py`) rather
than `odoo shell < file`, because `odoo shell` reading a pipe behaves like an
interactive console: a traceback on one line does not stop the next, so a phase
can half-execute in silence. The runner raises, rolls back and exits non-zero.

### The tenant as provisioned, before any flow ran

| | |
|---|---|
| Company | Selam General Trading PLC, id 1, ETB, chart `et`, fiscal year ends 7 July |
| Company TIN (`l10n_et_tin`) | `0088776655` (core `vat` is unset, which is not the TIN field — see flow (a)) |
| Our modules | `l10n_et`, `l10n_et_base`, `l10n_et_payroll`, `l10n_et_reports`, `sapian_core`, `sapian_demo_trader`, `sapian_theme`, `sapian_theme_auth_signup`, `sapian_theme_mail` |
| Journals | INV, BILL, BNK1, MISC, CABA, EXCH, **PAY**, STJ |
| Sale taxes | 15%, 0%, 0% EXEMPT, 0% Out, 15% WH, **3% WHT (Withheld by Customer)** |
| Purchase taxes | 15%, 0%, 0% EXEMPT, 0% Out, **3% WHT (Goods)**, **3% WHT (Services)**, **30% WHT (No TIN/Licence)**, 15% WHT (Foreign Digital), 3% Social Welfare Levy (Imports) |
| Opening documents | 2 posted customer invoices, 3 posted vendor bills, 1 posted payroll entry |
| Employees | 6 + Administrator |
| Users | **1** (`admin`) |

---

## Severity scale

Judged for a **first client going live**, not in the abstract.

- **BLOCKER** — the client cannot operate or cannot file. Go-live stops.
- **SERIOUS** — the client can operate, but someone is doing manual work every
  month, or a number is wrong in a way an accountant would catch.
- **COSMETIC** — visible, embarrassing, harmless.
- **NOT NEEDED YET** — real, but not for the first client.

Attribution is one of: **STOCK ODOO** / **OUR CODE** / **CONFIGURATION** /
**DEMO DATA**.

---

## Tier 1 — a client cannot go live without these

### (a) Accountant — customer invoice → post → email → payment → ledger

**Role:** accountant, as `admin`.

**Steps taken.** Created an invoice the way a user would — pick the customer, pick
the product, let Odoo default everything — for Mebrat Construction PLC (partner 6),
30 × *Cement OPC Dangote 50kg* at the product's own list price. Posted it. Sent it
by email through `account.move.send.wizard`, capturing the message at the SMTP
boundary by patching `IrMail_Server.send_email` and `_connect__`. Registered a
payment against it on the bank journal. Then read the ledger back.

**Measured.**

| | Value |
|---|---|
| Tax Odoo defaulted on the line | `15%` (from the product's own `taxes_id`) — **VAT, not withholding** |
| Draft totals | untaxed 33,000.00 · tax 4,950.00 · total 37,950.00 ETB |
| Posted as | `INV/26-27/0003`, state `posted`, `payment_state` `not_paid` |
| Journal entry | 110000 Sales of Goods and Services **cr 33,000.00** · 300700 VAT Payable **cr 4,950.00** · 221100 Trade Debtors **dr 37,950.00** |
| VAT arithmetic | 33,000 × 15% = 4,950.00 exactly — matches tax reference §5 |
| Customer receivable before / after posting | 40,480.00 → **78,430.00** over 1 → 2 posted lines (+37,950.00) |
| Email captured at SMTP | 1 message. `To:` the customer's address; `Subject: Selam General Trading PLC Invoice (Ref INV/26-27/0003)` |
| PDF attachment | `INV_26-27_0003.pdf`, **36,799 bytes**, generated and attached |
| Body | *"Here is your invoice INV/26-27/0003 amounting in 37,950.00 Br from Selam General Trading PLC"* — the figure in the mail equals the posted total |
| Body mentions "Odoo" | **no** · mentions "SapianERP" — also no |
| `is_move_sent` after send | `True` |
| Payment | `PBNK1/26-27/0001`, state `paid`, 37,950.00 ETB, date 2026-08-12, method *Manual Payment* |
| Payment entry | 211003 Outstanding Receipts **dr 37,950.00** · 221100 Trade Debtors **cr 37,950.00**, receivable line `reconciled=True` |
| Invoice after payment | `payment_state` **paid**, residual **0.0** |
| Customer receivable after payment | 78,430.00 → **40,480.00** (moved −37,950.00), i.e. back to its pre-invoice figure |
| Whole ledger | Σdebit − Σcredit = **0.0** across 30 posted lines |

**Outcome: WORKS.** Every leg reconciles: the invoice's VAT is arithmetically
right, the entry balances, the customer's ledger balance moves by exactly the
invoice total and back by exactly the payment, and the PDF and the email both
exist as artefacts rather than as screens that looked right.

**Two things the accountant should be told, neither of them a defect:**

1. The payment debits **211003 Outstanding Receipts**, not the bank account.
   Account 211001 Bank still reads **0.00 over 0 posted lines** afterwards. This
   is stock Odoo's design — cash moves to the bank account when the payment is
   matched to a bank statement line — but an Ethiopian accountant reading a trial
   balance the day after banking a cheque will see the money in a suspense
   account. It is flow (i)'s other half. **STOCK ODOO, correct, needs explaining
   in training.**
2. The 3% withholding a PLC customer would deduct at payment does not appear
   anywhere in this flow. That is flow (d).

**Finding a-1 — the invoice email leaves as `OdooBot <odoobot@example.com>`.**

Captured `From:` header, verbatim: `OdooBot <odoobot@example.com>`. Measured
causes, all four on the provisioned tenant:

| Setting | Value as provisioned |
|---|---|
| `company.email` | `False` |
| company partner email | `False` |
| admin user email / partner email | `False` / `False` |
| outgoing mail servers (`ir.mail_server`) | **0** |
| `mail.default.from` / `mail.catchall.domain` | `False` / `False` |

This is the branding rule in the defect register pointed at the most
outward-facing surface there is — an invoice to the client's own customer — and
it is worse than the "Powered by Odoo" strings in register items 4 and 17,
because it is in the `From:` line rather than the footer.

**Attribution: OUR CODE (onboarding gap) + CONFIGURATION.** The onboarding wizard
(`sapian_core/wizard/sapian_onboarding_wizard.py`) collects `company_name`, `tin`,
`street`, `city`, `fiscal_year`, `logo`, `primary_color` and the module picks. It
collects **no email address and no outgoing mail server**, so a tenant provisioned
entirely through the product's own onboarding is *by construction* unable to send
a customer-acceptable email. Nothing in the flow warns; the send reports success.
That is register rule 2 — a success signal that survives the work not happening.

**Severity: SERIOUS.** Not a blocker: a deployer who configures SMTP by hand
fixes it in ten minutes, and mail is set up per tenant anyway. It is serious
because the product's own go-live path does not ask, and because the failure is
silent and customer-visible.

**Could not test in this flow:** real SMTP delivery, DKIM/SPF, and whether the PDF
is *correct* rather than merely present — the 36,799 bytes were not opened and
compared against an MoR-compliant invoice layout. Amharic glyph rendering in that
PDF is untestable here: `fonts-sil-abyssinica` is not installed in this container
(see the environment table), so a tofu-box result would be this container's
finding and not the product's.

**Correction to my own earlier reading, recorded because it would have produced a
false finding:** `res.company.vat` is `False` on this tenant, which looks like a
missing TIN. It is not — `l10n_et_base` stores the TIN in `l10n_et_tin`, and the
company's is `0088776655`. Partner TINs are populated too (Mebrat `0022334455`,
Abyssinia `0033445566`, Derba `0011223344`), with two suppliers deliberately
blank (Yonas Transport, BuildSoft Cloud) — which is the 30% punitive path's
fixture. `l10n_et_business_licence_no`, `_expiry`, `l10n_et_has_valid_licence` and
`l10n_et_wht_compliant` all exist as fields. Whether any of them *drives* the tax
applied is flow (d)'s question, not this one's.

---

### (b) Accountant — vendor bill → post → pay

**Role:** accountant, as `admin`.

**Steps taken.** Bill from Derba Midroc Cement Depot (partner 11, TIN
`0011223344`), 100 × *Cement PPC Derba 50kg* at 900.00 = 90,000.00 net. Let the
product default its own purchase taxes. Posted. Paid in full from the bank
journal. Read the ledger back.

**Measured.**

| | Value |
|---|---|
| Tax defaulted on the line | `15%` purchase VAT only |
| **Draft** totals | untaxed 90,000.00 · tax 13,500.00 · **total 103,500.00** |
| **Posted** as | `BILL/26-27/08/0001`, **total 100,800.00** |
| Journal entry | 230100 Goods in Transit **dr 90,000.00** · 221200 VAT Receivable on Purchases **dr 13,500.00** · 300200 Trade Creditors **cr 100,800.00** · **300600 Withholding Tax Payable cr 2,700.00** |
| WHT arithmetic | 90,000 × 3% = 2,700.00, i.e. **3% of the VAT-exclusive base**, not of 103,500 |
| Structure vs tax reference §6 | base 90,000 + VAT 13,500 − WHT 2,700 = **100,800 payable** — the reference's worked example exactly |
| Supplier payable before / after posting | −77,056.00 → **−177,856.00** (moved −100,800.00) |
| Payment | `PBNK1/26-27/0002`, state `paid`, **100,800.00** — the net, not the gross |
| Payment entry | 211004 Outstanding Payments **cr 100,800.00** · 300200 Trade Creditors **dr 100,800.00**, payable line `reconciled=True` |
| Bill after payment | `payment_state` **paid**, residual **0.0** |
| Supplier payable after payment | −177,856.00 → **−77,056.00** (moved +100,800.00), back to its pre-bill figure |
| Whole ledger | Σdebit − Σcredit = **0.0** across 36 posted lines |

**Outcome: WORKS**, and the withholding half is better than the register expected.
The supplier is paid **100,800**, the 2,700 sits in *Withholding Tax Payable*
awaiting remittance to the MoR, and the 3% is computed on the base rather than on
the VAT-inclusive total — the single most commonly-got-wrong figure in Ethiopian
AP, and this gets it right. **Attribution: OUR CODE** (`l10n_et_base`) for the WHT
leg, **STOCK ODOO** for the bill and payment mechanics.

**Finding b-1 — the withholding appears only on posting, so the draft total lies.**
Draft total reads **103,500.00**; the same bill posts at **100,800.00**. Nothing
in the draft shows the 2,700 that is about to be deducted. An accountant checking
a bill against a supplier's invoice before posting — which is exactly accountant
2's manual voucher check in register item 13 — sees a figure the system will not
use. **Attribution: OUR CODE.** **Severity: SERIOUS**, not blocking: the posted
number is the correct one, so nothing is misstated in the ledger; the cost is
that the pre-post check an accountant actually performs is done against the wrong
total.

**Finding b-2 — a consumable's purchase debits `230100 Goods in Transit`.**
Measured above. `Goods in Transit` is a transit/clearing account; nothing in this
flow ever clears it, so on a trader who buys and sells over the counter it
accumulates. Whether that is the ET chart's mapping or the demo products'
`property_account_expense_id` is not established here — it needs one more
measurement, so this is recorded as **unattributed pending that check**, not as a
defect. Picked up again in flow (g), which is where a receipt actually exists to
clear it.

**Could not test in this flow:** partial payment, payment by cash journal,
supplier credit notes, the WHT certificate PDF the supplier is entitled to
(the module ships one per CLAUDE.md; it was not rendered here), and whether the
2,700 in *Withholding Tax Payable* is picked up by the WHT summary report — that
is flow (c)'s neighbour and was not run as part of this flow.

---

### (c) Accountant — produce the VAT figures for a period

Her longest monthly job (register item 13, tax reference §5).

**Role:** accountant, as `admin`.

**Steps taken.** Created an `l10n.et.vat.declaration` for 1–31 August 2026 — the
month containing flow (a)'s invoice and flow (b)'s bill. Read its computed totals.
Then recomputed the same figures independently, twice: once from GL account
movements, once from the posted `account.move.line` tax lines, so the report is
not its own witness. Exported the CSV and rendered the PDF. Then created a
September declaration to see what happens to August's credit.

**Measured.**

| | Value |
|---|---|
| Declaration | id 2, `VAT Declaration 2026-08`, `off_chart=False` |
| Report says | output VAT **4,950.00** · input VAT **13,500.00** · net **−8,550.00** |
| GL 300700 VAT Payable, Aug movement | **−4,950.00** — agrees |
| GL 221200 VAT Receivable on Purchases, Aug movement | **13,500.00** — agrees |
| Tax lines, independently | `15%` on INV/26-27/0003 −4,950.00; `15%` on BILL/26-27/08/0001 +13,500.00 — agrees |
| CSV | `vat_declaration_2026_08.csv`, **556 bytes**, 14 rows |
| CSV tie-out block | `Output VAT vs GL,300700,4950.00,4950.00,OK` and `Input VAT vs GL,221200,13500.00,13500.00,OK` |
| PDF | **22,442 bytes**, magic `%PDF-`, via `l10n_et_reports.report_vat_declaration` |
| PDF carries | taxpayer name, **TIN 0088776655**, `Period: 08/01/2026 – 08/31/2026 (monthly, Proc 1341/2024)`, all rows, and the GL reconciliation block |
| Net treatment | *"VAT credit carried forward 8,550.00"* — matches tax reference §5 (excess input VAT carries forward; refunds are exporter/investor processes) |

**Outcome: WORKS, with two gaps that bite in month two rather than month one.**

The arithmetic is right, it reconciles to the ledger in two independent
recomputations, and it produces both artefacts. **The tie-out block is the single
best thing found in this assessment**: both accountants in register item 13 said
they re-check tax figures by hand and do not trust the totals, and this report
answers that by printing the total *and* the GL figure *and* the word `OK` beside
them. That is the "show its working" tile of item 13, already built and shipping.
**Attribution: OUR CODE** (`l10n_et_reports`).

**Finding c-1 — the credit carried forward is stated but never carried.**
August's declaration ends *"VAT credit carried forward 8,550.00"*. The September
declaration, created immediately after, reports **output 0.00, input 0.00, net
0.00**. The full field list is
`company_id, csv_export_file, csv_export_filename, currency_id, date_from,
date_to, input_vat_total, name, net_vat, off_chart, output_vat_total` — there is
**no field for a brought-forward credit** (`[]` for any field named
forward/carry/previous/opening). So each month is computed in isolation, and the
8,550 the client is owed exists only as a sentence in last month's PDF. The
accountant must track it herself, outside the system, exactly as she does today in
Excel. **Attribution: OUR CODE.** **Severity: SERIOUS** — the product's pitch on
this flow is that it removes the Excel, and on the one line that spans months it
does not.

**Finding c-2 — nothing prevents two declarations for the same month, and none of
them has a state.** Creating a second 1–31 August declaration succeeded: two
records both named `VAT Declaration 2026-08`. There is no `state`, `locked`,
`filed` or `submitted` field. So there is no record of *what was filed*, and
nothing stops a figure being regenerated after filing and silently disagreeing
with the return the MoR holds. **Attribution: OUR CODE.** **Severity: SERIOUS**
for a client who will be audited; **not** a go-live blocker, since a first month
can be filed from a freshly generated report.

**Finding c-3 — WRONG FOR ETHIOPIA, or at least silently assumed: the period is a
Gregorian month.** The declaration is bounded by `date_from`/`date_to` and named
`2026-08`; the PDF prints `08/01/2026 – 08/31/2026`. There is **no Ethiopian month
anywhere in the model** — and `l10n_et_calendar` is `uninstalled` in the shipped
set, so no Ethiopian date exists in this database at all.

Per this job's rule 5 I am reporting the assumption, not building on it:
`docs/ethiopian-tax-reference.md` §2 establishes the Ethiopian-month filing window
for **employment income tax** and is **silent on the VAT period**. So I cannot say
this is wrong. What I can say is that the product has **silently chosen the
Gregorian reading** and shows no sign of having been asked the question. If the
MoR's VAT period is an Ethiopian month, every declaration this report produces is
mis-sliced by roughly a week at both ends, and the error is invisible because the
figures tie out perfectly to a GL sliced the same wrong way — a tie-out cannot
catch a period boundary. **This is a question for Zemichael's MoR call, not a
defect to fix from here.** Cross-references register items 9 and 13(4).

**Finding c-4 — "can she get what she actually files?" is still open, and this
assessment cannot close it.** She gets a correct, reconciled, well-presented
*SapianERP* VAT summary. Whether it is the *MoR return* is unknown: the register's
"Still owed by Zemichael" list records that neither accountant has supplied an
example filing file, and CLAUDE.md's own note on `l10n_et_reports` says to verify
layouts against current MoR forms before filing. The CSV's column layout
(`Section,Row,Base,Tax`) is our own invention. **Severity: BLOCKER for filing,
but it is a BLOCKER ON INFORMATION, not on code** — nothing can be built until
one real form or upload file exists. It is already on the register's owed list;
this assessment raises its priority rather than adding a new item.

**Could not test in this flow:** filing itself (etax.mor.gov.et), whether the CSV
is accepted by any MoR system, Category A vs B treatment (tax reference §7, marked
UNVERIFIED — deliberately not designed against), multi-company VAT, and any period
containing exempt or zero-rated sales, since the demo data has none — every
zero-rated and exempt row above is **0.00 because no such transaction exists**,
not because they were exercised. Those rows are therefore **untested**, not
passing.

**Note, cosmetic:** the rendered HTML wrapper's page title is `Odoo Report`
(stock `web.html_container`). It does not appear in the PDF output and is not
customer-visible in the attachment, but it is another instance of register item 4's
concern and would be visible in an HTML preview.
