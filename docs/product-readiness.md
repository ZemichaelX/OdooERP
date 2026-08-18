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
| PDF engine | image's patched wkhtmltopdf | **Two phases, and it matters —** tiers 1–3 ran on Ubuntu `wkhtmltopdf 0.12.6`, **unpatched Qt**, which silently DROPS all header/footer content from the PDF. Corrected 18 Aug by installing `wkhtmltox 0.12.6.1-3` — `0.12.6.1 (with patched qt)`, the same build the `odoo:19.0` image ships. See *"The renderer that could not render what the guard asserted on"* in the defect register, and the re-check below |
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

### Re-check after the unpatched-renderer finding (18 Aug)

Tiers 1–3 were measured on a build that **dropped every report header from the
PDF**. Any finding resting on header content would have been asserted against
bytes that could not contain it, so every PDF claim in this document was re-run on
the patched build.

**Result: no finding needs withdrawing, and none is marked UNVERIFIED.** Our own
reports put their identifiers in the report **body**, not the letterhead —
measured on the patched renderer, the TIN `0088776655` appears in the extracted
**PDF text** of all five:

| Report | TIN in PDF text |
|---|---|
| `l10n_et_reports.report_vat_declaration` | **yes** |
| `l10n_et_payroll.report_paye_declaration` | **yes** |
| `l10n_et_payroll.report_pension_schedule` | **yes** |
| `l10n_et_payroll.report_payslip` | **yes** |
| `l10n_et_base.report_et_invoice` | **yes** (both seller and buyer) |

**Two corrections, both narrow:**

1. **Flow (c) quoted an excerpt labelled *"PDF text"* that was taken from
   `_render_qweb_html`.** The substantive claims — taxpayer name, TIN, period,
   every figure, the GL reconciliation block — are all true of the PDF and were
   re-confirmed on the patched build. But the excerpt also contained
   `Africa Avenue (Bole Road)` and the `Odoo Report` page title, and **neither is
   in the PDF** (measured: `Africa Avenue` PDF `False` / HTML `True`). The
   cosmetic note about the `Odoo Report` title already said it does not appear in
   the PDF, so it stands as written.
2. **The core customer-invoice finding was re-proved properly**, and the earlier
   evidence for the *seller* half is superseded rather than merely restored. On
   the patched renderer, same invoice, same tenant:

   | State | PDF size | Seller TIN in PDF | Buyer TIN in PDF |
   |---|---|---|---|
   | `vat` empty (as shipped) | 75,016 B | **no** | **no** |
   | `vat` populated from `l10n_et_tin` | 75,063 B | **yes** | **yes** |

   The company block is present in both, so this is not a rendering gap: with
   `vat` empty the identifier genuinely does not print. **The BLOCKER stands, now
   on evidence that could have failed.**

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

---

### (d) Withholding, on a sale and on a purchase

**The brief's expectation was that none of the three conditions in
`docs/ethiopian-tax-reference.md` §6 exists. That expectation is REFUTED for two
of the three, and confirmed for the third.** This is the flow where reading the
register would have produced the wrong answer and measuring produced the right
one, so the evidence is given in full.

**Role:** accountant, as `admin`.

**Expectations written down before running**, per CLAUDE.md's red-proof rule:
(1) goods 5,000 → no WHT; (2) services 8,000 → no WHT; (3) services 15,000 → 3%;
(4) goods 50,000 from a supplier with no TIN → 30%; (5) and (6) sale to a PLC vs
to an individual → unknown, measure; (7) two sub-threshold bills to one supplier
→ expect nothing to flag the split.

**The configuration the engine actually read:** `WHT 3% from 2025-08-01`,
`threshold_goods=20,000`, `threshold_service=10,000`, `rate_standard=0.03`,
`rate_punitive=0.30`, `punitive_respects_thresholds=True`. Those are the tax
reference §6 figures exactly, and they are effective-dated configuration, not
constants in code — CLAUDE.md rule 4 holds here.

**Measured — purchase side (all four as predicted):**

| # | Bill | WHT tax applied | WHT amount | Bill total |
|---|---|---|---|---|
| 1 | goods 5,000 (under 20,000) | *none* | 0.00 | 5,750.00 |
| 2 | services 8,000 (under 10,000) | *none* | 0.00 | 9,200.00 |
| 3 | services 15,000 (over 10,000) | `3% WHT (Services)` | **450.00** | 16,800.00 |
| 4 | goods 50,000, supplier **no TIN** | `30% WHT (No TIN/Licence)` | **15,000.00** | 42,500.00 |

Row 3 proves the **services threshold is distinct from the goods threshold** —
15,000 is under the goods threshold and over the services one, and it withheld.
Row 4 proves the **supplier-credentials test discriminates**: Yonas Transport has
`l10n_et_tin=False`, `l10n_et_has_valid_licence=False`, `l10n_et_wht_compliant=False`,
and got 30%, while Derba (`tin=0011223344`, `licence_no=AA/5678/2015`,
`has_valid_licence=True`) got 3%. Rows 1 and 2 prove the thresholds are not
decoration: identical suppliers and products, below the line, withheld nothing.

Row 4 also disposes of a worry in register item 8 — *"applies it instead of the
15% VAT"*: 50,000 + 7,500 VAT − 15,000 WHT = **42,500**, so VAT is charged
**alongside** withholding, not replaced by it. On the purchase side the observed
behaviour is right.

**Measured — sale side:**

| # | Invoice | Taxes applied | Untaxed | Tax | Total |
|---|---|---|---|---|---|
| 5 | 60,000 to Mebrat Construction **PLC** (a withholding agent) | `15%` only | 60,000.00 | 9,000.00 | 69,000.00 |
| 6 | 60,000 to a **walk-in individual** (never an agent) | `15%` only | 60,000.00 | 9,000.00 | 69,000.00 |

**Identical.** Nothing on the sale side consults who the customer is.

**Measured — the sale-side tax, applied by hand.** The tax
`3% WHT (Withheld by Customer)` exists and is never applied automatically. Applied
manually alongside 15% VAT on a 100,000 sale it produces:

```
110000 Sales of Goods and Services            cr 100,000.00
300700 VAT Payable                            cr  15,000.00
221300 Withholding Receivable on Sale         dr   3,000.00
221100 Trade Debtors                          dr 112,000.00
```

**112,000.00 — the tax reference §6 worked example, to the birr**, with the 3%
taken on the base and not on the VAT-inclusive total, and posted to a
*receivable* (the buyer withheld it; the seller reclaims it). The machinery is
right. Only the decision to use it is missing.

**Measured — splitting:** two separate 9,000 goods bills to the same supplier on
the same day. Both withheld **nothing**; no warning, no activity, no chatter
message mentioning a split. A search of every model in the database for
`contract`/`agreement` returns only `hr.contract.type` and
`publisher_warranty.contract` — **there is no supply-contract concept in the
product.**

**Outcome, split by condition:**

| Tax reference §6 condition | Status | Evidence |
|---|---|---|
| **1. Buyer is a withholding agent** | **ABSENT** | No `res.partner` field matching `agent`; rows 5 and 6 identical. Moot on purchases (the buyer is always the company, a PLC) — **the gap is entirely on the sale side** |
| **2. Value clears the threshold** — per transaction | **PRESENT and discriminating** | Rows 1–3, and per-kind at that |
| **2b. …judged on the supply contract** | **ABSENT** | Splitting test; no contract model exists |
| **3. Supplier TIN and licence** | **PRESENT and discriminating** | Row 4 at 30% vs row 3 at 3% |

**Purchase side: WORKS.** **Sale side: ABSENT** (the tax exists, the automation
does not). **Attribution: OUR CODE** throughout — `l10n_et_base`, both for what
works and for what is missing.

**Severity.** Purchase side, nothing to fix. Sale side, **SERIOUS, not a
BLOCKER**: the client can issue a correct withheld invoice by selecting a tax
that already computes correctly, so nothing is unfileable and no number is wrong
— but on every PLC or government sale a human must remember, and on a walk-in
sale must remember *not* to. Register item 8's decided design (a company setting
*show the withholding deduction on the invoice*, defaulting ON) is **not built**:
`res.company` has no field matching `wht`/`withhold`, and `res.partner` has no
withholding-agent flag. The one partner field that exists, `l10n_et_wht_compliant`,
describes the partner *as a supplier*, not as a buyer.

**Where the product silently assumes one reading** (this job's rule 5):

1. **Presentation.** Tax reference §6 marks *whether withholding appears on the
   invoice* as **CONTESTED** and resolves it to *permitted, not required → a
   setting*. The product ships **neither** behaviour as a setting; it ships "off",
   by having no automation. That is a defensible default and an undocumented one.
2. **The threshold unit.** §6 is explicit, on accountant 2's stronger answer, that
   *"the key factor is the total agreement value, not the size of each small
   invoice"*. The engine applies the threshold **per transaction**, which is
   accountant 1's rougher reading. The code comment says this deliberately
   (*"the per-transaction thresholds are defined on the original supply"*), so the
   assumption is conscious — but nothing in the product records that a
   contract-level agreement exists, and nothing surfaces the split pattern the
   system cannot decide. §6's *"achievable design"* names surfacing that pattern
   as **the differentiator**. It is the missing piece.
3. **`punitive_respects_thresholds=True`** encodes the register's reading that
   thresholds gate the 30% too. That reading is marked as the confirmed default in
   CLAUDE.md, and it is at least a named, dated, switchable flag — good practice,
   worth keeping.

**Could not test in this flow:** foreign-digital withholding at 15%
(`l10n_et_is_foreign_digital` — no such partner in the demo data); a supplier with
a **valid TIN but an expired licence**, which is the one combination that would
prove the *licence* half of condition 3 independently of the TIN half (Yonas
Transport is missing both, so row 4 cannot separate them); WHT on payment rather
than on bill; the WHT certificate PDF; and the WHT summary report's figures
(the `l10n.et.wht.summary` model exists and was not run — it belongs with flow (c)
and was not reached).

---

### (e) Payroll — hire → wage → run → payslip → payment, with a transport allowance

**Role:** HR/payroll clerk then accountant, as `admin`.

**Steps taken.** Hired a new employee, set a wage, added him to a new August run,
gave him a **transport allowance** — the case register item 10 records as never
having been observed — then added a second employee chosen specifically so that
the *other* limb of the exemption binds. Computed, checked every figure against
hand arithmetic written down first, confirmed the run, read the posted journal
entry, exported the bank file and rendered all three PDFs.

**On "contract":** Odoo 19 Community has no `hr.contract`; the wage lives on
`hr.version` (CLAUDE.md records this). Measured: `emp.version_id` → `hr.version`
id 9, `wage` 9,000.00. So "hire → contract" is really "hire → version wage", and
it worked.

**The allowance rules as seeded** (`l10n.et.allowance.type`), all five, each
carrying its legal source:

| code | rule | cap ETB | cap % of basic |
|---|---|---|---|
| `transport` | **capped** | **2,200.00** | **0.25** |
| `hardship` | exempt | — | — |
| `medical` | exempt | — | — |
| `housing` | taxable | — | — |
| `position` | taxable | — | — |

That is tax reference §4 and CLAUDE.md's allowance list, as configuration with
effective sources rather than constants. **The `min(25% × salary, 2,200)` rule the
register asked for is built.**

**Measured — employee 1, basic 9,000 + transport 2,500** (the **2,200 cap** binds,
since 25% × 9,000 = 2,250 > 2,200). Expected figures written before running:

| Figure | Expected | Measured | |
|---|---|---|---|
| gross | 11,500.00 | 11,500.00 | OK |
| taxable income | 9,300.00 | 9,300.00 | OK |
| PAYE | 1,475.00 | 1,475.00 | OK |
| pension employee (7% of **basic**) | 630.00 | 630.00 | OK |
| pension employer (11%) | 990.00 | 990.00 | OK |
| net pay | 9,395.00 | 9,395.00 | OK |

Exemption 2,200 of the 2,500, taxable excess 300, so taxable income
9,000 + 300 = 9,300; PAYE by the shortcut form 0.25 × 9,300 − 850 = **1,475.00**.

**Measured — employee 2, basic 6,000 + transport 2,000** — chosen because here
**the 25% limb binds** (25% × 6,000 = 1,500 < 2,200). This is the case accountant
1's "flat 2,200" answer gets wrong, and per tax reference §4 getting it that way
round *"under-taxes low earners and leaves the employer liable for the shortfall
plus penalties"*:

| Figure | Expected | Measured | |
|---|---|---|---|
| gross | 8,000.00 | 8,000.00 | OK |
| taxable income | 6,500.00 | 6,500.00 | OK |
| PAYE | 800.00 | 800.00 | OK |
| pension employee | 420.00 | 420.00 | OK |
| net pay | 6,780.00 | 6,780.00 | OK |

**Both limbs of the transport exemption are implemented and both discriminate.**
Register item 10 said the logic could not be observed because no payslip carried a
non-taxable allowance; it can now, and it is correct on the harder of the two
cases. **This is the first observation of that rule working. OUR CODE.**

**Measured — run, journal and artefacts:**

| | Value |
|---|---|
| Run | `Payroll 2026-08`, 2 payslips, gross 19,500.00, PAYE 2,275.00, pension ee 1,050.00, pension er 1,650.00, net 16,175.00 |
| Confirm | state `done`, move `PAY/26-27/08/0001`, state `posted` |
| Journal entry | 611100 Salaries to permanent staff **dr 19,500.00** · 613100 Contribution to permanent staff **dr 1,650.00** · 300900 PAYE Payable **cr 2,275.00** · 300300 Pension contribution payable **cr 2,700.00** · 300400 Salary payable **cr 16,175.00** |
| Entry balances | Σdr − Σcr = **0.0** |
| Pension cross-check | 1,050 employee + 1,650 employer = **2,700** = the single pension payable credit — 18% total, split 7/11, on basic only |
| PAYE declaration PDF | **28,491 bytes**, `%PDF-`; carries employer TIN 0088776655, per-employee TIN, taxable income and PAYE |
| Pension schedule PDF | **29,920 bytes**; carries POESSA ID per employee and the `Employee 7% / Employer 11% / Total 18%` columns |
| Payslip PDF | **30,178 bytes** |
| Bank file | `salary_transfer_2026_08.csv`, 171 bytes, header + 2 employees + TOTAL row reconciling to 16,175.00 |
| Identifier warnings | `[]` — both employees had TIN and POESSA ID set, so the warning path stayed correctly quiet |

**Outcome: WORKS** for calculation, posting and the statutory PDFs. The arithmetic
is exact on both allowance limbs, the entry balances, the pension split
reconciles, and all three PDFs are real files. Three findings follow.

**Finding e-1 — the payslip PDF reports an exempt allowance as fully taxable.**
The rendered payslip for the low earner shows:

```
Earnings   Description                    Amount        Taxable
           Basic Salary                   6,000.00 Br   Yes
           Transport allowance August     2,000.00 Br   Yes
           Gross                          8,000.00 Br
```

Only **500.00** of that 2,000.00 was taxable — the engine knows it, and computed
PAYE on 6,500 accordingly. The word **"exempt" does not appear anywhere in the
payslip** (checked against the rendered text, not the template). So the document
the employee receives contradicts the calculation behind it, and an employee or
labour inspector reconciling the payslip by hand cannot arrive at the PAYE shown.
Tax reference §4 asks explicitly to *"show on the payslip which limit bound"* —
that is unbuilt, and the column that does exist actively states the wrong thing.
**Attribution: OUR CODE.** **Severity: SERIOUS** — no figure in the ledger or the
filing is wrong, but the employee-facing document is, and payslips are the
document staff argue about.

**Finding e-2 — the bank salary file exports with empty account numbers and does
not warn.** Both employees I hired have no bank account, and the export produced:

```
Employee Name,Bank Name,Account Number,Net Pay
Meseret Bekele — መሰረት በቀለ,,,6780.00
Tesfaye Alemu — ተስፋዬ አለሙ,,,9395.00
TOTAL,,,16175.00
```

`_l10n_et_identifier_warnings()` returned `[]`. Reading its source, it checks
**employee TIN** and **POESSA pension ID** and nothing else — there is no bank
check. The six demo employees *do* carry account numbers (`1000200030001`…`6`), so
the field exists and is normally populated; the failure only appears for a
newly-hired employee, which is precisely the routine event. A file that the bank
will reject is produced, named, sized and reported as an export. **This is
register rule 2 exactly** — the success signal survives the work not having
happened. **Attribution: OUR CODE.** **Severity: SERIOUS**, and cheap to fix by
extending the warning function that already exists for the other two identifiers.

**Finding e-3 — WRONG FOR ETHIOPIA: the run has no idea which Ethiopian month it
belongs to.** The run is named `Payroll 2026-08`; every PDF prints
`Period: 08/01/2026 – 08/31/2026`. The complete field list of `l10n.et.payroll.run`
contains **no field matching `ethio`, `ec_` or `filing`** — the search returned
`[]`. `l10n_et_calendar` is uninstalled in the shipped set.

Tax reference §2 is VERIFIED and unambiguous on this point: the declaration for one
Ethiopian month is filed during the *following* Ethiopian month, and the mapping to
the Ethiopian filing month and its window *"is what is mandatory, and it is the
same for both"* payroll cycles. So the Gregorian **cycle** is legitimate —
accountant 2 runs it that way deliberately — and the missing **mapping** is not.
The accountant is left to work out, unaided, that the August 2026 run is filed
during a particular Ethiopian month and that the window closes on a particular
day. **Confirms register item 9 by measurement.** **Attribution: OUR CODE
(absent feature).** **Severity: SERIOUS** — this is the one thing tax reference §2
calls mandatory, and it is also, per register item 13(4), the thing a
Gregorian-first competitor cannot do naturally.

**Finding e-4 — what would actually be filed is not what the module produces.**
Tax reference §2: the monthly filing is **two CSV uploads** — Schedule A
employment income tax per employee, and a separate pension CSV for the 18%. This
module produces **two PDFs and one bank CSV**. The only CSV field on the run is
`bank_export_file`. So the accountant reads figures off a PDF and retypes them
into the MoR upload. **Attribution: OUR CODE (absent feature) — but blocked on
information, not on effort**: the register's "Still owed by Zemichael" list records
that neither accountant has supplied an example of either file, and §2 says
plainly *"everything about the export is guesswork until then."* **Severity:
SERIOUS**, and it is the highest-value item in the product per the reference's own
assessment. **Not a BLOCKER**: a client can file by retyping, as they do today.

**Could not test in this flow:** actually paying the salary (the run posts to
*300400 Salary payable*; settling that against the bank was not run — it is
flow (a)'s mechanics applied to a different account, and the November payment of
PAYE and pension liabilities to MoR/POESSA was likewise not exercised); a
non-citizen or pension-opt-in employee (`l10n_et_pension_opt_in` exists, untested);
overtime as a manual input line; a mid-month joiner or leaver and any proration;
severance; and Amharic payslip rendering (see the font note in the environment
table — the names above did render as Ethiopic text in the extracted PDF text
layer, but glyph *appearance* in the PDF is not established here).

---

### (f) Sales — quotation → confirm → deliver → invoice → paid

**Role:** salesperson then accountant, as `admin`.

**Steps taken.** Quotation to Abyssinia Hardware for 40 × *Rebar 16 mm*; confirmed
it; validated the delivery Odoo created; invoiced from the order; paid the
invoice. Then ran a **control test** the register's item 13(3) asks for: post a
customer invoice for the same product with **no delivery at all** and see whether
stock moves.

**Measured.**

| Step | Value |
|---|---|
| Product | `Rebar 16 mm`, `type=consu`, **`is_storable=True`**, `tracking=none` |
| On-hand before | **0.0** |
| Quotation | `S00008`, draft, untaxed 7,720.00 · tax 1,158.00 · total 8,878.00 |
| Confirm | state `sale`; picking **`WH/OUT/00004`** created automatically, 40 units WH/Stock → Customers |
| Delivery validated | `WH/OUT/00004` state **`done`**, `date_done` set |
| On-hand after delivery | **−40.0** |
| SO status | delivery `full`, invoice `to invoice`, `qty_delivered=40.0`, `qty_invoiced=0.0` |
| Invoice from order | `INV/26-27/0007`, posted, untaxed 7,720.00 · tax 1,158.00 · total 8,878.00 — **matches the order exactly** |
| Payment | `payment_state` **paid**, residual **0.0** |
| On-hand after invoicing | **−40.0** — unchanged, as it should be |
| **Control: invoice 25 units with no delivery** | `INV/26-27/0008` posted; on-hand **−40.0 → −40.0, moved 0.0** |

**Outcome: WORKS** as a sales flow — the chain is intact from quotation to cash,
the picking is created and validated, and the invoice total equals the order total.
**STOCK ODOO** throughout; nothing of ours is involved in this flow.

**The control test confirms register item 13(3) by measurement**, and it is worth
stating plainly because it is the defect the accountants described from two
directions: **posting a customer invoice for 25 units moved stock by exactly
0.00.** A trader who bills over the counter — which is how a building-materials
yard in Addis actually sells — will have inventory that is permanently wrong and
nothing will complain. That is **STOCK ODOO working as designed**, not a bug, and
it is a **BLOCKER for a first client's training and process design, not for the
code**: someone must decide whether counter sales go through a delivery, and the
client must be taught that an invoice is not a goods issue.

**Finding f-1 — the delivery drove on-hand to −40 with nothing to stop it.**
Rebar 16 had **0.0** on hand and 40 were delivered. Odoo permits negative stock by
default; no warning, no block. For a trader this is how the register's *"goods
invoiced but never delivered"* twin — *goods delivered but never received* —
enters the data. **STOCK ODOO (default configuration).** **Severity: SERIOUS**,
and it is a **CONFIGURATION decision for go-live**, not a code fix.

**Finding f-2 — every product in the demo tenant has no product category, so
inventory is unvalued and there is no COGS.** Measured: `categ_id` is `False` on
**12 of 12** products, while three categories (*Goods*, *Expenses*, *Services*)
exist unused. All three are set to `valuation=periodic`, `cost_method=standard`,
and **no stock valuation account**. The `STJ` (Inventory Valuation) journal holds
**0 entries** after a completed receipt and a completed delivery.

Consequences, for a trading company whose largest asset is stock:

- Inventory never reaches the balance sheet automatically.
- No cost of goods sold is posted, so **gross margin cannot be read from the
  accounts** — the P&L shows revenue with no matching cost.
- This is why flow (b)'s bill debited `230100 Goods in Transit` and nothing ever
  cleared it: **finding b-2 is resolved here.** With periodic valuation and no
  category, the purchase lands in whatever account the product resolves to and
  stays there.

**Attribution: two parts, and they should not be merged.** The periodic-valuation
default is **STOCK ODOO** and is a legitimate choice for a small trader who counts
stock physically. The absence of **any product category at all** is **OUR CODE**:
the product ships no default category wired to the `et` chart, so this is not a
client misconfiguration but the state the product arrives in. `sapian_demo_trader`
reproduces it in the demo, but the demo is the symptom, not the cause.

**Severity: BLOCKER** — see register entry 26 and the tier 1 summary for why this
was regraded from SERIOUS. For the demo it is embarrassing: a prospect asking
"what's my gross margin?" gets nothing. For a client it means the accounts cannot
answer the question the business is run on.

**Could not test in this flow:** partial deliveries and backorders; a return;
delivery of a lot/serial-tracked product (`tracking=none` on all demo products);
the delivery-note PDF; multi-warehouse; and — because valuation is periodic — any
COGS or margin figure at all, which is not a gap in the testing but a consequence
of the configuration described above.

---

### (g) Purchase — RFQ → purchase order → receipt → vendor bill

**Role:** buyer then accountant, as `admin`.

**Steps taken.** RFQ to Derba Midroc for 200 × *Cement PPC Derba 50kg* at 880.00
(176,000.00 net). Confirmed to a purchase order, validated the receipt Odoo
created, then generated the vendor bill **from the order** and posted it.

**Measured.**

| Step | Value |
|---|---|
| On-hand before | **0.0** |
| RFQ | `P00003`, draft, untaxed 176,000.00 · tax 26,400.00 · total 202,400.00; line tax `15%` |
| Confirm | state `purchase`; receipt **`WH/IN/00002`** created, state `assigned` |
| Receipt validated | state **`done`**; on-hand **0.0 → 200.0** |
| PO after receipt | `qty_received=200.0`, `qty_invoiced=0.0`, `invoice_status=to invoice` |
| Bill from order, draft | 202,400.00 |
| Bill posted | `BILL/26-27/08/0008`, **197,120.00** |
| Entry | 230100 Goods in Transit **dr 176,000.00** · 221200 VAT Receivable **dr 26,400.00** · 300200 Trade Creditors **cr 197,120.00** · 300600 Withholding Tax Payable **cr 5,280.00** |
| WHT arithmetic | 176,000 × 3% = **5,280.00** — correct, on the VAT-exclusive base |
| Three-way match data | PO `P00003`: received **200.0**, invoiced **200.0**, `invoice_status=invoiced`, bill `invoice_origin='P00003'` and linked back to the order |
| STJ entries after a real receipt | **0** |

**Outcome: WORKS.** The full chain holds, stock rises on the receipt rather than
on the bill, the quantities match across all three documents, and the bill carries
the correct Ethiopian withholding. **STOCK ODOO** for the procurement chain,
**OUR CODE** for the WHT line.

**Register item 13(3) — "invoice against purchase order against delivery note" —
is answered here, positively:** Odoo already holds the three-way match as data
(`qty_received` vs `qty_invoiced` vs `invoice_status`, plus the PO↔bill link). The
manual check accountant 2 performs every month is a *report over data that already
exists*, not a feature that must be built from nothing. That is a cheap
differentiator and it is worth recording as such.

**Finding b-1 reconfirmed:** draft 202,400.00 → posted 197,120.00. Same silent
5,280 appearing only at post.

**Finding b-2 resolved, and it is worse than it looked.** The purchase debits
`230100 Goods in Transit`, an `asset_current` account, and that account now stands
at **453,800.00** across all the tenant's bills, with nothing clearing it.
Traced to source: the product has **no expense account and no income account of
its own, and no product category** (`categ_id` is `False`), so Odoo falls back and
resolves to 230100. This is the same root cause as finding f-2 and it should be
fixed once, in one place.

The consequence for the accountant, stated plainly: **every purchase this company
makes is being capitalised into a transit asset account, so the P&L shows revenue
with no cost of sales, and the balance sheet carries a "Goods in Transit" balance
that only grows.** **Attribution: OUR CODE** — no default product category ships wired to the `et`
chart, with **STOCK ODOO** supplying the fallback account. **Severity: BLOCKER**
(regraded; register entry 26). The client can still invoice, pay and file every
statutory return — which is why an earlier draft graded this SERIOUS — but an
accounting system that cannot show a trading company its cost of sales is not
doing the job it was bought for.

**Related gap, recorded because it decides whether a real client reproduces this:**
`data-templates/`, described in CLAUDE.md as *"spreadsheet import templates for
onboarding"*, contains **only `README.md`**. No import template ships. So there is
no product-import path that could carry a category column and no evidence about
what a real client's product data would look like. **Attribution: OUR CODE
(absent).** **Severity: SERIOUS for onboarding**, and it is what makes f-2/b-2 a
product question rather than a demo-data question.

**Could not test in this flow:** partial receipts, over-receipt and over-billing
(the case a three-way-match report exists to catch), vendor price-list handling,
purchase of a service against a PO, and the RFQ email to the supplier — flow (a)
established that outbound mail leaves as `OdooBot`, so a supplier RFQ would carry
the same `From:` and this was not separately measured.

---

### (h) Administrator — create a user, assign rights, log in as them

**Role:** administrator, then the new user.

**Steps taken.** Created an internal user with **only** `base.group_user` — a plain
employee, no accounting, sales, purchase or HR rights. Probed access two
independent ways: at ORM level with `check_access`, and — because that is the
thing actually asked for — by **logging in over HTTP** and issuing the same RPC
calls the web client issues. The Odoo HTTP server was started for this flow.
(The scratch password is not recorded in this document; it exists only in this
container's throwaway database.)

**Measured — the login itself:**

| | Value |
|---|---|
| Login | `POST /web/login` → **HTTP 200**, redirected to `/odoo`, session cookie set |
| Session | `uid=5`, name *Tigist Haile (plain employee)*, **`is_admin=False`** |
| `GET /odoo` | HTTP 200, 6,755 bytes |
| Groups (explicit + implied) | 6: *Role/User*, *Technical Features*, *Basic Pricelists*, *Multiple UoM*, *Multi Currencies*, *delivery reminder* — stock Odoo's implied set for an internal user |
| Apps visible in the menu | **5**: `SapianERP`, `Discuss`, `Dashboards`, `Employees`, `Apps` |

**Measured — what is blocked.** Every one of these was refused, both at ORM level
and over authenticated RPC:

| Model | Result |
|---|---|
| `l10n.et.payslip` | **AccessError** — *"You are not allowed to access 'Ethiopian Payslip' records"* |
| `l10n.et.payroll.run` | AccessError |
| `hr.version` (where wages live) | AccessError |
| `account.move`, `account.move.line` | AccessError |
| `account.journal` | AccessError |
| `l10n.et.vat.declaration`, `l10n.et.wht.summary` | AccessError |
| `l10n.et.wht.config`, `ir.config_parameter` | AccessError |
| `sale.order`, `purchase.order`, `stock.picking` | AccessError |
| `ir.module.module` **write** (i.e. installing) | AccessError |

**Measured — field-level, on the employee record.** This is the sharpest test,
because `hr.employee` *is* partly readable (the staff directory) and the question
is what comes with it:

| Fields requested | Result |
|---|---|
| `name` | ALLOWED — 9 employees, the directory |
| `name, l10n_et_tin` | **BLOCKED** |
| `name, l10n_et_pension_id` | **BLOCKED** |
| `name, private_street, private_phone` | **BLOCKED** |
| `name, bank_account_ids` | **BLOCKED** |
| `name, birthday, identification_id` | **BLOCKED** |
| `name, version_id` (the route to wage) | **BLOCKED** |

**Outcome: WORKS.** A plain employee cannot reach a single payslip, wage,
journal entry, invoice, order, tax configuration or colleague's private data.
**Our own added fields behave correctly**: `l10n_et_tin` and `l10n_et_pension_id`
on `hr.employee` are group-restricted along with Odoo's own sensitive HR fields,
which is CLAUDE.md rule 8 being honoured rather than asserted. **Attribution:
STOCK ODOO** for the framework, **OUR CODE** for our models' ACLs, both correct.

**A discrepancy in my own method, recorded because it would mislead anyone
repeating this:** ORM `check_access('read')` on `hr.employee` reported denied,
while an authenticated RPC `search_read` returned 9 rows. The **RPC result is the
authoritative one** — it is what a real logged-in user gets. Any access audit on
this project should be done through an actual session, not through `check_access`
alone.

**Finding h-1 — every internal user can read the full module list.**
`ir.module.module search_read` returned **693 modules** (`sale_management`,
`pos_restaurant`, `account`, `crm`, …), and the `Apps` root menu is in a plain
employee's menu. Installing is correctly blocked. **Attribution: STOCK ODOO.**
**Severity: COSMETIC** — it exposes nothing about the business, but it does show
every employee a catalogue of software the company has not bought, which sits
oddly beside the product's own tiered module catalogue.

**Finding h-2 — every internal user can read product cost prices.**
`product.product search_read` with `standard_price` returned all 12 products with
their costs (Binding Wire 200.00, Cement OPC Dangote 1,000.00, Cement PPC Derba
910.00) alongside the selling prices. For a trading company **the buying price is
the margin**, and it is readable by any employee with a login — a storekeeper, a
driver, a new hire. **Attribution: STOCK ODOO default.** **Severity: SERIOUS for
this specific business**, and it is a **CONFIGURATION decision at go-live**
(restrict the cost field or the product form), not a code defect. Flagged because
a first client will not think to ask, and because it is the kind of thing an owner
discovers after it has already gone round the yard.

**Finding h-3 — the SapianERP app opens the Module Catalog for plain employees
too.** `sapian.module.catalog` is readable by every internal user (**38 rows**:
*SapianERP Core*, *Ethiopian Accounting*, *Ethiopian Payroll*, *Ethiopian
Compliance*, …), and `SapianERP` is the first app in their menu. This is register
item 13 — *"the front door of the product is a configuration list"* — seen from
the employee's side, where it is worse: for them it is a configuration list they
have no reason to see and cannot act on. **Attribution: OUR CODE.** **Severity:
COSMETIC** on its own, but it strengthens item 13's case that the landing page
should be a slot with a real default.

**Also measured, and deliberately not raised as a finding:** partner TINs and
business licence numbers are readable by any internal user (7 partners with TINs
returned). That is ordinary ERP behaviour — a salesperson needs partner data and
the TIN is printed on the invoice anyway.

**Could not test in this flow:** a *portal* user as opposed to an internal one
(that is flow (l), untested); multi-company record rules with a second company,
which cannot be exercised on a single-company tenant and is the case CLAUDE.md
rule 3 cares most about; the accountant and salesperson group combinations a real
client would actually use — only the plain-employee floor was tested, so nothing
here says whether an *accountant* role is scoped correctly; and password policy,
2FA and session expiry.

---

## Tier 1 — summary

**All eight flows were run. None was skipped. A ninth, (n) Point of Sale, was
added to tier 1 afterwards** — it belongs there because flow (f) proved an invoice
never moves stock, and a counter-selling yard is exactly that case.

**One BLOCKER was found in tier 1** —
the Goods in Transit defect (finding f-2/b-2/g, register entry 26). Every other
core flow operates and every statutory return can be filed, though two of them by
retyping figures a human read off a PDF.

**A second BLOCKER was found later, in tier 2 flow (m):** the build has no profit
& loss, balance sheet, trial balance or general ledger at all. It was invisible
from tier 1 because every tier 1 flow reads the ledger directly.

**This grading was corrected after review, and the correction is the more useful
half of this summary.** The first draft of this document graded the product-category
finding SERIOUS, reasoning that the client could still operate and still file.
That reasoning **conflated two different axes: how cheap a fix is, and how much it
blocks.** The fix is an afternoon's work; what it blocks is an accounting system's
ability to tell a trading company what it earned. A P&L that shows revenue with no
cost is not something that company can run itself on, whatever it can still submit
to the MoR. Cheapness was allowed to argue down consequence, and it should not
have been.

The attribution was corrected in the same pass, from CONFIGURATION to **OUR CODE**,
for a reason worth stating: the product ships **no default product category wired
to the `et` chart**, so there is nothing for a client to misconfigure. Every client
meets this on their first purchase, by default, having done nothing wrong. A defect
that arrives with the product is ours.

### What works, with the measurement that proves it

| Flow | Proof |
|---|---|
| (a) Invoice → email → payment | Ledger balances to 0.00 over 30 lines; customer balance +37,950.00 then −37,950.00; 36,799-byte PDF attached to a message captured at the SMTP boundary |
| (b) Vendor bill → pay | 90,000 + 13,500 VAT − 2,700 WHT = 100,800 paid; the tax reference §6 worked example exactly |
| (c) VAT for a period | Output 4,950.00 / input 13,500.00 reconciled **twice** independently against the GL, and printed with an `OK` tie-out block on the report itself |
| (d) Withholding, purchases | Four discriminating cases: under-threshold goods and services withheld nothing; over-threshold services withheld 450.00; a no-TIN supplier withheld 30% = 15,000.00 |
| (e) Payroll | Both limbs of the transport exemption exact on 11 hand-computed figures; entry balances; pension 7% + 11% = 2,700 on basic only; three PDFs rendered |
| (f) Sales chain | Quotation → delivery (stock 0 → −40) → invoice → paid, invoice total equal to order total |
| (g) Purchase chain | RFQ → receipt (stock 0 → 200) → bill with WHT 5,280.00; three-way match data present and consistent |
| (h) Access control | A real HTTP session as a plain employee is refused payslips, wages, journal entries, orders, tax config, and every sensitive HR field |
| **(n) Point of Sale** | Added to tier 1 later: a POS sale moved stock **60.0 → 55.0**, its invoice produced the same ledger entry as a back-office invoice, and the session closed with a cash difference of **0.00** |

### The three best things in the product, on this evidence

1. **The VAT report's GL tie-out block.** It answers the exact distrust both
   accountants described, and it already ships.
2. **The withholding engine on purchases.** Effective-dated configuration,
   per-supply-kind thresholds, a punitive path that discriminates, and the 3%
   taken on the VAT-exclusive base. This is the part an Ethiopian accountant
   would recognise as written by someone who knows the rule.
3. **The transport-allowance exemption**, correct on the limb that is easy to get
   wrong, and observed working for the first time here.

### Findings, ordered by severity

| # | Finding | Attribution | Severity |
|---|---|---|---|
| **f-2 / b-2 / g** — register **26** | **No default product category ships wired to the `et` chart**, so purchases capitalise into `230100 Goods in Transit` (now 453,800.00), the `STJ` journal is empty, there is no COGS, the P&L shows revenue with no cost, and inventory never reaches the balance sheet. Every client hits it on their first purchase | **OUR CODE** | **BLOCKER** |
| **c-4 / e-4** | What the client actually files is still unknown — no MoR form or upload example exists, so the VAT CSV layout and the two payroll CSVs are guesswork | Blocked on INFORMATION, already on the register's owed list | **SERIOUS**, highest value |
| **e-3 / c-3** | No Ethiopian filing month anywhere; payroll and VAT periods are Gregorian and the mandatory mapping is absent | OUR CODE (absent) | **SERIOUS** |
| **e-1** | The payslip PDF prints an exempt allowance as `Taxable: Yes`; the word "exempt" never appears | OUR CODE | **SERIOUS** |
| **e-2** | Bank salary file exports with empty account numbers and **does not warn** — a success signal that survives the work not happening (register rule 2) | OUR CODE | **SERIOUS** |
| **d** | Sale-side withholding is entirely manual: no withholding-agent flag, no company setting, PLC and walk-in invoices identical | OUR CODE (absent) | **SERIOUS** |
| **c-1** | The VAT credit carried forward is stated but never carried; September ignored August's 8,550.00 | OUR CODE | **SERIOUS** |
| **c-2** | Two declarations can exist for one month; no `state`, so there is no record of what was filed | OUR CODE | **SERIOUS** |
| **a-1** | Invoice email to the client's customer leaves as `OdooBot <odoobot@example.com>`; onboarding collects no email and no mail server | OUR CODE (onboarding gap) + CONFIGURATION | **SERIOUS** |
| **b-1** | Withholding appears only at posting, so the draft total (103,500) differs from the posted total (100,800) with nothing shown | OUR CODE | **SERIOUS** |
| **g** | `data-templates/` ships only a `README.md` — no import templates exist | OUR CODE (absent) | **SERIOUS** for onboarding |
| **h-2** | Every internal user can read product cost prices, i.e. the margin | STOCK ODOO default | **SERIOUS** for this business; a CONFIGURATION decision |
| **f-1** | Delivery drove on-hand to −40 with no warning or block | STOCK ODOO default | **SERIOUS**; a CONFIGURATION decision |
| **f (control)** | Posting an invoice moves stock by 0.00 — confirmed by measurement | STOCK ODOO by design | Training/process, not code |
| **h-1** | Every internal user can list all 693 modules | STOCK ODOO | **COSMETIC** |
| **h-3** | The SapianERP app opens the Module Catalog for plain employees too | OUR CODE | **COSMETIC** |
| — | Every module README renders as reStructuredText errors during install (register item 6 seen again here) | OUR CODE | **COSMETIC** |

### The one thing to fix first

**Ship a default product category wired to the `et` chart.** One change — a
category carrying income, expense and (if perpetual) valuation accounts, applied
as a product default rather than left to each client — closes b-2, f-2, the
Goods-in-Transit balance and the empty `STJ` journal at once, and it is what
stands between this tenant and a P&L that shows a gross margin.

It is both **the cheapest item on this list and the only BLOCKER on it.** Those
two facts are independent, and the second is the one that decides the queue.

---

## Tier 2 — needed soon

Run after tier 1 was complete. Same rules: measured outcomes, attribution,
severity for a first client, and a named list of what could not be reached.

**One environment event, recorded because register rule 3 exists.** Between
tier 1 and tier 2 the container's Postgres stopped and had to be restarted; it
recovered through WAL redo. Nothing was measured while it was down — the runner
aborted with `connection refused` rather than reporting a failure, which is the
distinction rule 3 is about. The database was then checked before any tier 2
measurement was trusted: **24 posted moves, 2 payroll runs, 8 payslips, ledger
Σdr − Σcr = 0.00 across 83 lines, `INV/26-27/0003` present, Goods in Transit
still 453,800.00.** Intact.

---

### (i) Bank statement import and reconciliation

Accountant 2's **longest monthly job** (register item 13, tax reference §5). The
brief asks for more than pass/fail: how much work is a month, and could the
product make it shorter.

**Role:** accountant, as `admin`.

**Steps taken.** Built a month of bank activity as a real statement — *CBE August
2026*, four lines chosen to be the mix an Addis trader actually gets: two customer
receipts that should match posted payments exactly, one supplier payment, and one
bank service charge that matches nothing. Measured what the system proposes on its
own, then reconciled all four and read the suspense account back.

**Measured — what exists to do the job with:**

| | Value |
|---|---|
| Statement import modules (OFX / QIF / CAMT) | **none exist** — no such module in Odoo 19 Community's addons at all |
| Reconciliation **widget** | **none** — `account_accountant` (Enterprise) is not in the addons path |
| Reconciliation **menu** | **none** — search of `ir.ui.menu` for "reconcil" returns `[]` |
| Only reconciliation action | *"Reconciliation Models"* → `account.reconcile.model`, i.e. configuring rules, not doing the work |
| Reconcile models seeded | 2: *Internal Transfers* and *Bank Fees* (`match_label=contains`, param `'Bank Fees'`), **both `trigger=manual`** |
| What a statement line posts | `211001 Bank` **dr** / `211002 Bank Suspense` **cr** — the suspense line is what a human must repoint |

**Measured — what the system can already work out for itself.** Odoo's own
candidate domain (`_get_default_amls_matching_domain`, which *is* in Community)
was run against each line:

| Statement line | Amount | Candidates | Exact-amount matches | Match found |
|---|---|---|---|---|
| MEBRAT CONSTRUCTION PLC TRF | 37,950.00 | 23 | **1** | `PBNK1/26-27/0001` |
| ABYSSINIA HARDWARE RTGS | 8,878.00 | 23 | **1** | `PBNK1/26-27/0003` |
| DERBA MIDROC PAYMENT | −100,800.00 | 23 | **1** | `PBNK1/26-27/0002` |
| SERVICE CHARGE AUG | −350.00 | 23 | 0 | — needs a human |

**3 of 4 lines have exactly one unambiguous counterpart, and Community already
finds it.** No partner was guessed on any line (`partner_id` empty on all four).

**Measured — the reconciliation itself, done the only way Community allows:**

| | Value |
|---|---|
| Path per matchable line | repoint the suspense line's `account_id` (and partner) to the counterpart account → save → select the pair in the ledger → reconcile |
| Result, line 1 | statement line `is_reconciled=True`, payment line `reconciled=True` |
| `211003 Outstanding Receipts` | 46,828.00 → **8,878.00** (−37,950.00, exactly the matched payment) |
| All four lines | **0 of 4 unreconciled** |
| `211002 Bank Suspense` at the end | **0.00** |
| Whole ledger | Σdr − Σcr = **0.00** across 91 lines |

**Outcome: WORKS, but by hand.** The suspense account reaching **exactly 0.00** is
the discriminating measure here — a partly-done reconciliation leaves a residue,
so this is a result that cannot be produced by doing nothing.

#### How much work is a month?

**Measured operations**, not guessed: **2 distinct edit operations** for each of
the three matchable lines (repoint the account and partner; reconcile the pair)
and **3** for the bank charge (choose an expense account, which is a decision, not
a lookup). **7 operations for a 4-line statement.**

Translating to the UI — **this part is a derived estimate, not a measurement**,
and is labelled as such because I drove the ORM rather than a browser. Each
operation costs several interactions in the Community list/form UI: open the
entry (1), click into the account cell and pick an account (2–3), set the partner
(2), save (1), then navigate to the ledger, filter, select both lines and
reconcile (4–5). That is **roughly 10–12 clicks per statement line**.

A small Addis trader's bank statement runs to perhaps 60–200 lines a month. At
that rate the job is **on the order of 600–2,400 interactions per month**, and it
is done by the person who told us it is already her longest job.

#### Could the product make that job shorter? Yes, and cheaply — this is a reason to buy

This is the strongest product opportunity found in the whole assessment, and the
reason is the gap between two measured facts:

1. **The hard part is already solved in Community.** Finding the counterpart is
   the difficult, error-prone half, and `_get_default_amls_matching_domain`
   narrowed 23 candidates to exactly 1 on 3 of 4 lines with no help.
2. **The easy part is missing.** What Enterprise sells in `account_accountant` is
   the *screen* that shows that suggestion and lets you accept it with one click.
   That screen is absent, so a Community client does by hand a job the engine
   underneath has already done.

A one-click accept-the-suggestion screen over machinery that already exists would
take this from ~10–12 interactions per line to ~1, which on a 200-line month is
the difference between a day's work and twenty minutes. Two further cheap wins
sit beside it: the seeded **`Bank Fees` reconcile model is set to `trigger=manual`
and could be `auto_reconcile`** with Ethiopian bank-charge labels (CBE, Awash,
Dashen wording) so recurring charges never reach a human; and **no statement
importer exists at all**, so an Ethiopian-bank CSV/XLSX importer with a saved
column mapping removes the typing that precedes all of the above.

**Attribution: STOCK ODOO (Community/Enterprise split), not a defect in our
code.** Nothing here is broken; the capability is simply on the other side of
Odoo's paywall, and our product currently inherits the gap silently.
**Severity: SERIOUS** for a first client — the work is real and monthly — and it
is the item on this list most likely to be worth building rather than fixing.

**Could not test in this flow:** an actual CSV/XLSX import through `base_import`
into `account.bank.statement.line` (the generic importer exists and was not
exercised — so "import works" is **untested**, only "no bank-format importer
exists" is measured); partial and multi-invoice matches, which are where a widget
earns most of its keep; foreign-currency statement lines; the statement's
`balance_end_real` check against a real closing balance, since this scratch
statement opened and closed at 0.00; and the click counts themselves, which are
derived from measured operations rather than observed in a browser.

---

### (j) Inventory adjustment and a valuation report

**Role:** storekeeper then accountant, as `admin`.

**Steps taken.** Took the product flow (f) had driven negative and counted it, the
way a yard does a physical count: set a counted quantity, applied the adjustment,
then looked for the valuation report and for the inventory figure in the accounts.

**Measured.**

| | Value |
|---|---|
| `Rebar 16 mm` on-hand before | **−40.0** (from flow (f)) |
| Adjustment line | counted **100.0**, current −40.0, **difference 140.0** — computed correctly off a negative base |
| After applying | on-hand **100.0** |
| Stock move created | 1 inventory move, 140.0, state `done` |
| `STJ` (Inventory Valuation) journal entries afterwards | **0** |
| Inventory value by hand (Σ qty × `standard_price`) | **452,000.00 ETB** |
| Inventory value **in the accounts** (`235100 Stock`) | **0.00** |
| Valuation report | exists as client action `stock_valuation_report` ("Inventory Valuation"), and **no menu points to it** (`ir.ui.menu` search → NONE) |

**Outcome: the adjustment WORKS; the valuation report is ABSENT in the shipped
configuration.**

The adjustment half is clean — the difference is right, it handles a negative
starting quantity, and it posts a real `done` move. **STOCK ODOO.**

**Finding j-1 — the company holds 452,000.00 of stock and the balance sheet says
0.00.** This is finding f-2 / register entry 26 measured on the asset side rather
than argued, and it is the number to put in front of an accountant: after a
physical count, `235100 Stock` still reads **0.00** and the `STJ` journal is still
empty. Nothing about the count reaches the ledger.

**Finding j-2 — the valuation report cannot be opened.** Odoo's Inventory
Valuation report is a client action that exists in this database, but no menu
references it, because that menu is conditional on automated (perpetual)
valuation. With every category on `periodic` and no product carrying a category at
all, the report is unreachable through the UI. So the answer to *"can she produce
a valuation report?"* is **no — not because it is broken, but because the
configuration hides it.**

**Attribution for both: OUR CODE**, by the same root cause as entry 26 — no
default product category ships wired to the `et` chart — with **STOCK ODOO**
supplying the periodic default and the conditional menu. **Severity: consequences
of the BLOCKER**, not separate items; both disappear when entry 26 is fixed, which
is itself useful evidence that entry 26 is correctly identified as the root.

**Could not test in this flow:** the valuation report's contents (unreachable, and
forcing it open would measure a configuration this product does not ship); FIFO or
average costing, since `cost_method` is `standard` everywhere; landed costs; a
count sheet PDF (`stock.report_inventory` exists and was not rendered); and
inventory at a second location or warehouse.

---

### (k) Employee self-service — portal login, time-off, expense claim, own payslip

**Role:** an employee with a login.

**Steps taken.** Checked what is installed, linked an employee record to a real
user account (the plain-employee user from flow (h)) the way an employer enabling
self-service would, and then asked whether that employee can reach their own
payslip.

**Measured.**

| Capability | Result |
|---|---|
| `hr_holidays` (time off) | **uninstalled** — `hr.leave` model does not exist |
| `hr_expense` (expense claims) | **uninstalled** — `hr.expense` model does not exist |
| `hr_attendance` | **uninstalled** |
| `portal` | installed |
| Employee linked to a user | done: *Meseret Bekele* → `tigist@selam.test` |
| That employee reading **their own payslip** | **AccessError** — *"You are not allowed to access 'Ethiopian Payslip' records"* |
| `l10n.et.payslip` inheritance | `['base']` — **no `portal.mixin`**, no mail thread |
| Portal controllers in our addons (`/my/…`) | **none found** across all of `addons/` |

**Outcome: ABSENT**, in all four parts. There is no time-off request, no expense
claim, no portal route to a payslip, and an employee linked to their own employee
record **cannot read their own payslip even over ORM** — the model carries no
owner-scoped rule, only the HR-group ACL that correctly blocked flow (h)'s plain
employee.

**Attribution, split, because it matters for what to do about it:**

- Time off and expenses: **CONFIGURATION** of the shipped set, not missing
  capability. Both modules are present in the addons path and merely uninstalled;
  they are stock Odoo and free. A client who wants them gets them by installing
  them.
- Own payslip: **OUR CODE.** `l10n.et.payslip` is our model, and it was written
  as an HR-only back-office record — no portal mixin, no controller, no
  own-record rule. There is nothing to switch on.

**Severity: NOT NEEDED YET** for a first Ethiopian trading client with seven
employees, who will hand out printed payslips and keep leave on paper — which is
also what makes it a safe thing to leave undone. It is recorded here so that the
absence is a decision on the record rather than a surprise: the moment a client
with fifty staff asks for self-service, the payslip half is a build, not a
setting.

**Could not test in this flow:** an actual portal login as an employee (there is
no portal route to reach, so there was nothing to log in *to* — this is an
absence, not an untested pass); whether payslips can be **emailed** to employees,
which is the realistic substitute for self-service and was not exercised; and
time-off or expense behaviour after installing those modules, which would measure
a configuration this product does not currently ship.

---

### (l) Customer portal — view an invoice, pay it

**Role:** the client's customer.

**Steps taken.** Created a portal user against Mebrat Construction PLC, logged in
over HTTP, walked `/my` → `/my/invoices` → an invoice page, downloaded the PDF,
tried to pay, and checked what the page says about who sent it.

**Measured — viewing:**

| | Value |
|---|---|
| Portal login | HTTP 200, lands on `/my`, `share=True` |
| `/my` | 200, 20,425 bytes; offers **Invoices** and **Quotations** |
| `/my/invoices` | 200; lists **4** invoices — ids 1, 10, 18, 22, **all of them Mebrat's own** |
| An invoice page | 200; `INV/26-27/0003`, 37,950.00 Br, marked **Paid** |
| **PDF download** | **217,264 bytes**, magic `%PDF-` |
| **Access scoping** | requesting invoice **26** (another customer's) **redirects to `/my`** — correctly refused |
| Footer | `Copyright © Selam General Trading PLC` · **`Powered by SapianERP`** |

**Measured — paying:**

| | Value |
|---|---|
| Payment providers present | 24 (`Wire Transfer`, `Demo`, `Adyen`, `Stripe`, …) |
| Payment providers **enabled** | **0** — every one is `state=disabled` |
| Ethiopian providers (Telebirr / CBE Birr / Chapa / Amole) | **none exist** in Odoo at all |
| Unpaid invoice `INV/26-27/0004` (69,000.00) | page renders, **no payment section at all** |
| Unpaid invoice `INV/26-27/0006` (112,000.00) | same |
| Paid invoice | shows a *"Pay Invoice"* heading reading *"There is no amount to be paid"* |

**Outcome: viewing WORKS; paying is ABSENT.** A customer can log in, see only their
own invoices, read them and download a real PDF. They cannot pay, and on an unpaid
invoice they are not even told that paying is unavailable — the section simply is
not rendered. **Attribution: STOCK ODOO** (providers ship disabled by design) plus
a genuine market gap: **no Ethiopian payment provider exists in Odoo**, so this is
a build, not a configuration, and CLAUDE.md already has payments in the DEFERRED
list. **Severity: NOT NEEDED YET** for a first client whose customers pay by bank
transfer and cheque — but the portal is a real, working sales asset today, which
is worth knowing.

**Finding l-1 — the customer-facing portal page's `<title>` is `Odoo`.**
Measured on the invoice page a client's customer sees. The footer is correct
(`Powered by SapianERP`, client copyright), so the theme reaches the body and not
the title tag. This is the branding rule on an outward-facing surface, and it is a
**new instance** not covered by register items 3, 4 or 5, which concern mail
templates and Discuss. **Attribution: OUR CODE** (theme scope gap).
**Severity: COSMETIC**, but it is on the client's customer's browser tab.

**Finding l-2 — the bot is still `OdooBot`, and it renders on that same page.**
Measured: `res.users` uid 1 is `name='OdooBot'`, login `__system__`, and the string
**`SapianBot` does not appear anywhere in `addons/`**. The register's branding rule
states the bot is `SapianBot`, a constant in `vendor.py`; that is a *decision*, and
on current master it is **not built** — consistent with item 5 recording #49 as
red and unmerged. The portal invoice page shows `-- OdooBot --` in the chatter
signature, so this reaches the client's customer exactly as the register's
"accepted consequence" paragraph anticipated — except with Odoo's name rather than
ours. **Attribution: OUR CODE (unbuilt).** **Severity: COSMETIC**; recorded to
confirm by measurement that #49 is still outstanding, not as a new entry.

**A correction to guard against, about my own method:** the portal page also shows
`Salesperson: OdooBot`. **That is an artefact of this assessment, not a product
defect** — every document here was created through a script running as
`SUPERUSER_ID` (uid 1), so uid 1 became the salesperson. An invoice created by a
real user in the UI would name that user. The product fact in the paragraph above
is the uid-1 *name*, not its appearance in the salesperson field.

**Could not test in this flow:** an actual online payment (no provider can be
enabled without credentials, and enabling `Demo` would measure a configuration no
client ships); portal signup and the invitation email (which would leave as
`OdooBot <odoobot@example.com>` per register entry 25); `/my/quotes` and sales
order acceptance; and whether the portal PDF is the same document as the emailed
one — both rendered, neither was compared byte-for-byte.

---

### (m) P&L and balance sheet — do they render, and do they balance

**Role:** accountant, as `admin`. Run before and after categorising one product,
as asked, so the BLOCKER's blast radius is measured rather than asserted.

#### First result: the reports do not exist

| | Result |
|---|---|
| `account.report` records in the database | **4, all tax reports** — *Tax Report*, *Generic Tax report*, and two groupings |
| Actions named Profit / Loss / Balance Sheet / Income Statement / Trial Balance / General Ledger | **NONE** |
| Menus for any of the above | **NONE** |
| `account_reports` (the Enterprise module carrying them) | **NOT FOUND** in the addons path |

**Outcome: ABSENT.** A client on this build **cannot produce a profit & loss
account, a balance sheet, a trial balance or a general ledger** from any menu.
This is the same Community/Enterprise split as flow (i)'s missing reconciliation
widget. CLAUDE.md's Epic B says of statements: *"Skip: … IFRS statement engine
(use Odoo/OCA reports)"* — the plan assumed something would supply them. Nothing
does: no OCA financial-report module is vendored (`vendor/` holds only
`oca_web`), and Odoo Community ships none.

**Attribution: STOCK ODOO (Community/Enterprise split) + OUR CODE (a planning
assumption that was never closed).** **Severity: BLOCKER for a first client** —
an Ethiopian PLC needs a P&L and balance sheet for its annual profit-tax return
and for its bank, and no amount of correct VAT and payroll substitutes. It is the
second BLOCKER in this assessment and it was not visible from tier 1.

#### Second result: computed from the ledger, they do balance

Because the product ships no statements, the following are **my arithmetic over
posted `account.move.line` grouped by `account_type`** — clearly not the
product's output:

| | BEFORE | AFTER |
|---|---|---|
| Revenue | 380,845.00 | 380,845.00 |
| Expenses | 85,993.00 | **139,993.00** |
| **Net profit** | **294,852.00** | **240,852.00** |
| Assets | 858,691.75 | 866,791.75 |
| Liabilities | 563,839.75 | 625,939.75 |
| Equity | 0.00 | 0.00 |
| `assets − (liabilities + equity + profit)` | **0.00 OK** | **0.00 OK** |
| `230100 Goods in Transit` | 453,800.00 | 453,800.00 |
| `511100 Cost of Goods and Services` | 350.00 | **54,350.00** |
| `235100 Stock` | 0.00 | 0.00 |
| Cost of sales as % of revenue | **22.6%** | **36.8%** |

**The books balance in both states**, which is worth saying plainly: the ledger is
internally consistent. What is wrong is *classification*, and a balanced ledger
cannot detect that — the same blind spot as flow (c)'s tie-out, which reconciles a
correct total against a wrongly-sliced period.

**Before the change the P&L reported 380,845.00 of revenue against 350.00 of cost
of goods** — the 85,993.00 of "expenses" is payroll and a bank charge, not the
cement and rebar sold. The company's purchases sat in an asset account.

#### The blast radius, from changing exactly one product

Categorising **one** product and posting **one** 54,000.00 bill for it moved that
purchase from `230100` to `511100`, and:

- **reported profit fell by exactly 54,000.00** (294,852.00 → 240,852.00);
- cost of sales as a share of revenue went from **22.6% to 36.8%**;
- `230100` **still holds 453,800.00**, because the correction is not retroactive.

So the exposure is not theoretical and it is not small: one product, one invoice,
54,000 birr of overstated profit. The 453,800.00 still in `230100` is the
untouched remainder — part of it is genuinely unsold stock and part is cost of
goods sold, and **the product currently offers no way to tell those apart**, since
`235100 Stock` is 0.00 and the valuation report is unreachable (flow (j)).

#### Root cause, and it revises my own earlier attribution

Chasing this to the bottom produced a different answer from the one I gave when
tier 1 was reported, and the earlier one was wrong in a way worth stating.

I said *"no default product category ships wired to the `et` chart"*. **Measured,
that is false.** A default IS wired — to the wrong account:

- `odoo/addons/l10n_et/models/template_et.py`, lines 32–33:
  `'expense_account_id': 'l10n_et2301'` and `'income_account_id': 'l10n_et1100'`.
- `l10n_et2301` resolves to **`230100 Goods in Transit`, `account_type =
  asset_current`.**
- Odoo's generic `chart_template.py` then propagates `company.expense_account_id`
  into `ir.default` for `product.category.property_account_expense_categ_id` —
  measured on this tenant as **id 18 = 230100**.
- Proof that the missing category was not the operative cause: the existing
  *Goods* category, before I touched it, already read
  `property_account_expense_categ_id = 230100`. Categorising a product without
  fixing the account would have changed nothing.

**So the defect is in Odoo's own Ethiopian localisation: core `l10n_et`
designates a current-asset transit account as the default expense account for
every Ethiopian company.** Products having no category made it *look* like our
demo data's fault; it is not, and a client who categorised everything correctly
would still land in `230100`.

**Revised attribution: STOCK ODOO (core `l10n_et`) as the source, OUR CODE for
not overriding it** — `l10n_et_base` exists precisely to extend that chart, and
this is the kind of thing it is for. **Severity unchanged: BLOCKER.** The fix
shape changes completely, though: it is not "assign categories", it is **override
`expense_account_id` in our chart extension** so every Ethiopian company gets a
real expense account, with category assignment as a secondary tidy-up. Register
entry 26 is corrected accordingly.

**Could not test in this flow:** the reports themselves (they do not exist);
whether an OCA financial-report module would install cleanly against the `et`
chart, which is the obvious remedy and was not attempted; the year-end closing
entry that periodic valuation requires; and how much of the 453,800.00 is closing
stock versus cost of goods sold — that needs a physical count valued at cost,
which flow (j) showed the product cannot currently produce.

#### Addendum — what OCA actually covers, measured from the 19.0 branches

Requested before deciding between vendoring and building. **Nothing was vendored.**
Both repositories were cloned read-only into the container's scratch space and
read; neither was installed.

**Coverage against the four reports we lack — the expectation is CONFIRMED:**

| Report we lack | `account_financial_report` | `mis_builder` |
|---|---|---|
| **General ledger** | **YES** | via KPI expressions |
| **Trial balance** | **YES** | via KPI expressions |
| **Profit & loss** | **NO** | **engine only — no template ships** |
| **Balance sheet** | **NO** | **engine only — no template ships** |

`account_financial_report` (OCA/account-financial-reporting, branch `19.0`)
provides exactly seven reports, read from its wizards, report models and menu
entries: **Aged Partner Balance, General Ledger, Journal Ledger, Open Items, Open
Items Partner, Trial Balance, VAT Report**. A case-insensitive search of the whole
module for `profit and loss` / `profit_loss` / `balance sheet` / `balance_sheet` /
`income statement` returns **nothing**. So: GL, trial balance, open items and aged
partner balance — exactly as expected — and **no P&L and no balance sheet.**

`mis_builder` (OCA/mis-builder, branch `19.0`) is a **report engine, not a set of
statements**. The core module ships **no `data/` report templates at all**; the
only `mis.report` record in the repository is `mis_report_expenses` ("Demo
Expenses") in `mis_builder_demo`. Its KPIs are expressions over account codes —
`balp[600%]`, `balp[211000,212100,212300]`. **Vendoring it would not hand us a
P&L; it would hand us a framework in which we must author one against the `et`
chart.** That authoring is ours either way.

**Maintenance — both look genuinely maintained, not merely present:**

| | account-financial-reporting | mis-builder |
|---|---|---|
| Branch `19.0` exists | yes | yes |
| Branch HEAD | `7e6f489`, **2026-08-17** (today; a Weblate translation) | `58a237a`, **2026-08-03** |
| Last substantive code commit | **2026-07-29** — *"[FIX] account_financial_report: Define the appropriate group in the menu"*; a 27 Jul fix to decimal analytic percentages in XLSX exports | **2026-08-03** merge of PR #823; 29 Jul menu-group fix |
| Non-translation commits, last 90 days | **34** | **35** |
| Distinct non-bot authors, last 90 days | **17** | **6** |
| Manifest declares 19.0 | `account_financial_report` **19.0.0.0.19**, `partner_statement` 19.0.1.1.0, `account_tax_balance` 19.0.1.0.3 | `mis_builder` **19.0.1.2.0**, `mis_builder_budget` 19.0.1.0.1 |
| Licence | AGPL-3 | AGPL-3 |

The `19.0.0.0.19` patch level on `account_financial_report` is itself a signal: the
port has been iterated nineteen times on the 19.0 branch rather than tagged once
and abandoned.

**A cost neither of us had counted: this is not two repos, it is four.** Both
modules depend on **`date_range`** and **`report_xlsx`**, and neither is in Odoo
core (verified: `board` is core, those two are not). `date_range` comes from
OCA/server-ux and `report_xlsx` from OCA/reporting-engine. So:

- vendoring **AFR alone** → 3 repos pinned and hash-checked;
- vendoring **mis_builder alone** → 3 repos;
- vendoring **both** → **4 repos**, against the one (`vendor/oca_web`) the project
  carries today, each needing a `check_vendor.sh` pin and a refresh procedure.

**Licence note, flagged not resolved:** both are **AGPL-3**, where `web_responsive`
is LGPL-3. That is a different obligation for a product sold to clients and it
should be looked at by someone qualified before either is shipped, not decided
here.

**The argument for building, stated as fairly as I can put it.** The one thing
this assessment found that no competitor does is flow (c)'s **GL tie-out block** —
the VAT report printing its total, the ledger's total and `OK` beside them, aimed
squarely at two accountants who told us they re-add computed numbers by hand. A
P&L and balance sheet in that shape would be the same idea applied to the
statements a bank and the MoR actually ask for, and neither Odoo, nor OCA, nor
GraceERP prints a statement that proves it reconciles. Set against that: OCA gives
GL and trial balance today for the cost of pinning repos, and those two are pure
plumbing with no Ethiopian character worth owning. **The split those facts suggest
— take GL and trial balance from OCA, build P&L and balance sheet ourselves in the
tie-out shape — is a recommendation, not a decision, and the decision is
Zemichael's.**

---

## DECISION — build our own financial statements

**Taken by Zemichael, 17 August 2026, on the coverage facts above.** It went
further than the recommendation: **build all of them.** Recorded here because the
reasoning matters more than the verdict, and because the reversal point is part of
the decision.

**Not vendoring OCA. Not installing `base_accounting_kit`. We build the
statements.**

### Why

1. **The P&L and balance sheet are ours in every scenario anyway.** `mis_builder`
   ships **zero** report templates — its only `mis.report` record in the entire
   repository is `mis_report_expenses`, in the demo module. Vendoring it buys a
   framework to author inside, not a statement. Since the authoring against the
   `et` chart is ours either way, the only question left was whether to carry a
   dependency while doing it.
2. **Licence.** OCA's modules are **AGPL-3**; `web_responsive`, the one thing
   already vendored, is **LGPL-3**. For a product sold to clients those are
   different obligations. The best outcome is not a favourable legal opinion — it
   is **not needing one.**
3. **Two classes of report is worse than either extreme.** If the VAT report
   proves it ties to the ledger and the P&L does not, the product teaches the
   accountant that some of its numbers are checkable and some are not — worse than
   a product where none are, because it makes the tie-out look like a quirk of one
   screen rather than a promise. Uniformity is the feature.
4. **"Every statement proves it ties to the ledger" is the product thesis**, and
   it is already half-built: flow (c)'s VAT declaration prints its total, the GL's
   total, and `OK` beside them. Both accountants said they re-add computed numbers
   by hand. Extending that across the statements is the differentiator; importing
   someone else's statements would forfeit it.

### The reversal point, stated in advance

**If our general ledger proves hard at real volumes** — a client with hundreds of
thousands of move lines, where pagination, multi-currency and performance are the
actual work rather than the arithmetic — **`account_financial_report` stays
maintained** (34 non-translation commits in 90 days, 17 non-bot authors, manifest
`19.0.0.0.19`). Vendoring **one** repo for **one** report is a far smaller
decision than the four-repo commitment weighed above, and taking it later costs
nothing already spent. **The GL is the piece to watch. The P&L and balance sheet
are not the risky part.**

### The competitive fact this sits against

Measured from **GraceERP's own Reporting menu**: they run **`base_accounting_kit`
(Cybrosys)** — *Day Book*, *Cash Book*, *Bank Book* and *Assets* together are that
module's signature, and their presence identifies it.

The honest position, without flattering ourselves:

- **They have a P&L and a balance sheet today. We do not** (entry 27).
- **It cost them a free install.** Parity here is an afternoon's work for anyone,
  us included.
- **What they do not have is any Ethiopian character in those reports, or any
  proof the numbers tie to the ledger.** `base_accounting_kit` is a generic
  accounting pack: it knows nothing of the Ethiopian filing month, the `et`
  chart's peculiarities, or the 3% withholding.

**We are not building to catch up. We are building to pass them.** And if a sale
ever needs parity *tomorrow*, that same free module is the escape hatch — worth
knowing precisely so that the schedule never becomes the reason to abandon the
thesis.

---

### (n) Point of Sale — the counter sale, added to tier 1

**Added to tier 1 after the fact, not left in tier 3**, because flow (f) proved
the thing that makes it a tier 1 concern: **posting a customer invoice moves stock
by exactly 0.00.** A building-materials yard in Addis sells over the counter, so
the question of whether POS moves stock is not a "needed soon" question — it
decides whether the client's inventory is right at all.

**Run after job 1**, so that where cost of sales posts had already been corrected
(register entry 26). Confirmed on this tenant before starting:
`company.expense_account_id = 511100 Cost of Goods and Services`, type `expense`.

**Role:** counter cashier, then shop supervisor, then accountant.

#### What installing POS actually gives a trader

| | Value |
|---|---|
| `pos.config` records after install | **0** — no shop exists |
| `pos.payment.method` records after install | **0** — no cash method exists |
| Cash journal | **none existed**; one had to be created |
| Products flagged `available_in_pos` | **0 of 14** |

So a trader who installs POS opens it onto nothing: no counter, no payment
method, no cash journal, and an empty product list. All of it is ordinary
configuration and none of it is hard, but **it is a setup job, not a switch**, and
the product ships no POS preset. **Attribution: CONFIGURATION** (the modules are
stock Odoo and behave normally with demo data; our build installs
`--without-demo=all` deliberately, per `build_demo.sh`). **Severity: SERIOUS for
onboarding** — it belongs with entry 34, the missing `data-templates/`.

Setting up a counter (*Selam Counter*, cash method, cash journal `CSH1`, 10
storable products flagged) took one script. POS also **refused to open a session
as superuser** — *"You do not have permission to open a POS session"* — so the
session was opened as the admin user carrying `group_pos_manager`, which is what a
shop supervisor actually is.

#### Measured — the counter sale

| Step | Value |
|---|---|
| Session opened | `Selam Counter`, opening cash **0.00** |
| Cash sale | 5 × *Cement OPC Dangote 50kg* @ 1,100.00 → untaxed **5,500.00** · VAT **825.00** · total **6,325.00** |
| VAT arithmetic | 5,500 × 15% = 825.00 exactly |
| Order state | `paid` |
| **On-hand before → after** | **60.0 → 55.0** |

**Stock moves on a POS sale.** That is the finding this flow exists for, and it is
the answer to the counter-selling problem flow (f) exposed: an invoice moves
nothing, a POS sale moves five bags. **STOCK ODOO, works.**

#### Measured — the sale to a registered customer, invoiced

| | Value |
|---|---|
| Order | 10 × cement to Mebrat Construction PLC → untaxed 11,000.00 · tax **1,650.00** · total 12,650.00 |
| Invoice raised from the order | `INV/26-27/0009`, **posted** |
| Journal entry | 110000 Sales of Goods and Services **cr 11,000.00** · 300700 VAT Payable **cr 1,650.00** · 221100 Trade Debtors **dr 12,650.00** |
| VAT check | 11,000 × 15% = 1,650.00 — **the same accounts and the same figure a normal invoice produces** (compare flow (a)) |

**WORKS.** A POS invoice is indistinguishable from a back-office invoice in the
ledger, which is what an accountant reconciling the two channels needs.

Note, consistent with flow (d): **no withholding is applied on the POS sale
either.** Sale-side WHT remains manual everywhere.

#### Measured — closing the session and counting the cash

| | Value |
|---|---|
| Orders in session | 2, totalling **18,975.00** |
| Cash payments taken | 6,325.00 + 12,650.00 = **18,975.00** |
| Counted cash entered | 18,975.00 |
| **Session difference** | **0.00** |
| Session state | `closed` |
| Session journal entry | `POSS/26-27/08/0002`, posted, balances to **0.00** |
| Entry | 300700 VAT Payable **cr 825.00** · 110000 Sales **cr 5,500.00** · 221500 Trade Debtors (PoS) **dr 18,975.00** / **cr 12,650.00** |
| Cash journal `CSH1` account 211005 | **18,975.00** |
| 221500 Trade Debtors (PoS) | **0.00 over 4 lines** — the clearing account fully cleared |
| Whole ledger | Σdr − Σcr = **0.00** over 106 lines |

**WORKS, and it reconciles end to end**: the drawer, the clearing account and the
cash account all agree, and the invoiced order is correctly credited out of the
POS receivable so it is not counted twice. *(A correction to my own first reading:
I initially took the `221500` debit to mean the cash had not reached a cash
account. It had — the clearing account nets to zero and 211005 holds the
18,975.00. The intermediate line is the clearing step, not a resting place.)*

#### Finding n-1 — cost of sales does NOT post on a POS sale

`511100 Cost of Goods and Services` reads **54,350.00 over 2 lines** after the POS
sales — unchanged, both lines from job 1's own test purchase. `STJ` (Inventory
Valuation) holds **0 entries**.

**Job 1 fixed where purchases go. It did not, and could not, make a sale
recognise cost**, because valuation is still `periodic` (finding f-2). Under
periodic valuation Odoo posts no per-sale COGS at all: cost reaches the P&L as
*purchases*, and the year-end stock count adjusts it. That is a legitimate method
and it is **STOCK ODOO** behaving correctly.

What it means for the client, stated plainly: **there is no gross margin per sale,
per product or per day**, which is the number a counter-selling trader most wants,
and the P&L's cost line is "what we bought" rather than "what we sold" until
somebody counts the stock. **Severity: SERIOUS** — and it is a **decision to take
at go-live**, not a defect: periodic with a disciplined physical count, or
perpetual with categories, valuation accounts and a costing method configured.

#### Finding n-2 — the POS receipt carries no TIN

`pos.order` has **no `ir.actions.report` at all** — the receipt is a client-side
OWL template
(`point_of_sale/static/src/app/screens/receipt_screen/receipt/order_receipt.xml`),
not a server-rendered PDF, so it **could not be rendered server-side here**. What
follows is read from the template, and is labelled as a template read rather than
a rendered artefact.

The receipt renders: company name, street, city, state, ZIP, phone, email,
website; the POS config name; the lines; price excluding tax; a tax-group block
(name, label, base amount, tax amount); total including tax; payment method and
amount; change; total discount; a portal URL; the ticket code; and a configurable
receipt footer.

**The tax identifier is guarded by `t-if="company.vat"`.** On this tenant
`company.vat` is `False` — our localisation stores the TIN in **`l10n_et_tin`**
(measured: `0088776655`). So **the receipt prints no TIN.**

This generalises beyond POS and is the more useful half of the finding: **any core
Odoo template that prints `company.vat` prints nothing on a SapianERP tenant.**
Our own documents are unaffected — flow (a)'s invoice PDF and flow (c)'s VAT
declaration both carry the TIN, because they are our templates reading
`l10n_et_tin`.

**Attribution: OUR CODE** — storing the TIN outside `vat` is our design decision,
and nothing bridges it. **Severity: SERIOUS**, and possibly moot; see the open
question below.

#### Finding n-3 — VAT is added on top of the shelf price

The cement is priced 1,100.00 and the counter total came to 1,265.00 a bag
(5 → 6,325.00). Ethiopian retail shelf prices are normally **VAT-inclusive**, so a
customer handed a 6,325.00 total for goods marked 1,100.00 will dispute it.
This is a pricelist/tax configuration choice (`price_include`), not a defect —
**STOCK ODOO**, **CONFIGURATION** — but it is a go-live decision that must be made
deliberately, and the demo data currently implies the exclusive convention.

#### THE OPEN QUESTION THAT MAY MOOT MOST OF THIS

**Ethiopia may require VAT-registered traders to issue receipts from a certified
sales register machine (an EFD/fiscal device).** `docs/ethiopian-tax-reference.md`
§5 records that Regulation **570/2025** brings real-time EFD and QR invoices for
VAT-registered traders, and CLAUDE.md flags fiscal-device integration as high
priority for retail — **but neither states whether an ERP-generated receipt is
legally sufficient on its own.** Zemichael is asking his accountants. **Nothing
here should be built on either answer.**

**If the answer is YES — a certified device is required:**

- An Odoo POS receipt **is not a legal receipt**, and POS becomes an
  **integration with a certified device**, not a configuration. That is a
  completely different size of job: device certification, a driver or middleware,
  offline behaviour, and a supplier relationship with an accredited vendor.
- **Findings n-2 and n-3 become moot**, because the legal receipt would be printed
  by the device, not by Odoo — the TIN and the price convention would be the
  device's problem.
- The parts that **stay true regardless** are the ones that matter most: **stock
  moves on a POS sale** (60 → 55), the invoice path produces an identical ledger
  entry to a back-office invoice, the session reconciles to 0.00, and **cost of
  sales still does not post** (n-1). None of those depend on who prints the paper.

**If the answer is NO**, n-2 and n-3 are ordinary defects to fix and POS is close
to usable for a first client after the setup work described above.

**Outcome: WORKS for stock, VAT and cash reconciliation; ABSENT for cost of sales
and for any fiscal-device compliance.**

**Could not test in this flow:** the POS user interface itself (everything here
was driven through the backend ORM, so no screen was exercised and no touch
workflow, offline mode, or receipt printer was tested); refunds and returns;
partial and split payments; a second cashier or concurrent sessions; the customer
display; barcode scanning (`stock_barcode` is `uninstallable` here); and the
receipt as a rendered artefact, for the reason given in n-2.

## Tier 2 — summary

All five flows were run. **A second BLOCKER was found in (m)**, and it was not
visible from tier 1.

| Flow | Outcome | Attribution | Severity |
|---|---|---|---|
| **(m)** P&L / balance sheet | **ABSENT** — no P&L, balance sheet, trial balance or general ledger exists in the build; `account_reports` is Enterprise | STOCK ODOO split + OUR CODE (planning assumption never closed) | **BLOCKER** |
| (i) Bank reconciliation | **WORKS, entirely by hand** — no widget, no menu, no bank-format importer; suspense cleared to exactly 0.00 | STOCK ODOO (Community/Enterprise split) | **SERIOUS** — and the biggest build opportunity found |
| (j) Inventory adjustment | **WORKS**; valuation report **unreachable**, 452,000.00 of stock shows as 0.00 in the accounts | consequence of entry 26 | consequence of the BLOCKER |
| (l) Customer portal — view | **WORKS**: own invoices only, 217,264-byte PDF, correct access scoping | STOCK ODOO | — |
| (l) Customer portal — pay | **ABSENT**: 0 of 24 providers enabled, no Ethiopian provider exists in Odoo at all | STOCK ODOO + market gap | **NOT NEEDED YET** |
| (k) Employee self-service | **ABSENT**: `hr_holidays`/`hr_expense` uninstalled; an employee cannot read their own payslip | CONFIGURATION (time off, expenses) + OUR CODE (payslip has no portal route) | **NOT NEEDED YET** |

**Two Community/Enterprise gaps, one conclusion.** Flows (i) and (m) are the same
shape: the capability sits in `account_accountant` and `account_reports`, both
Enterprise, and the product inherits the gap silently. Bank reconciliation is the
opportunity — the matching engine is already in Community and only the screen is
missing. Financial statements are the obligation — a client cannot file an annual
return without them, and the plan's *"use Odoo/OCA reports"* was never closed.

---

## Tier 3 — the honest boundary: installed but untested, and absent

**Nothing in this section was tested.** It is here so that a flow that was skipped
and a flow that passed cannot be confused.

### Installed in the shipped set, not covered by tiers 1 or 2

| Module | Untested — would a first Ethiopian trading client need it? |
|---|---|
| `spreadsheet`, `spreadsheet_dashboard*` (5 modules) | The "Dashboards" app a plain employee sees in flow (h). **Possibly** — it is the nearest thing the build has to register item 13's compliance dashboard, and it was never opened |
| `sale_pdf_quote_builder` | Quotation PDF composition. Marginal |
| `sale_edi_ubl`, `purchase_edi_ubl_bis3`, `account_edi_ubl_cii`, `account_add_gln` | European e-invoicing formats. **No** — Ethiopia's EFD/QR regime (Reg 570/2025) is unrelated, and these are dead weight a prospect may notice |
| `sms`, `sale_sms`, `stock_sms` | SMS notifications. **Yes eventually** — CLAUDE.md defers payments/SMS until a client signs; no gateway is configured |
| `snailmail`, `snailmail_account` | Postal letter service. **No** — not available in Ethiopia |
| `auth_totp`, `auth_totp_mail`, `auth_totp_portal`, `auth_passkey`, `auth_passkey_portal` | 2FA and passkeys. **Yes before an internet-facing client**, and untested here |
| `partner_autocomplete`, `iap`, `iap_mail` | Odoo online services requiring IAP credits. **No** — and they may attempt outbound calls |
| `google_gmail`, `microsoft_outlook` | OAuth mail transports. **Relevant to register entry 25** — one of these may be the practical fix for outbound mail, untested |
| `digest` | Periodic KPI emails to users. Would currently send as `OdooBot` (entry 25) |
| `hr_skills`, `hr_org_chart`, `hr_homeworking` | HR extras pulled in by `hr`. **No** for seven employees |
| `privacy_lookup` | GDPR data lookup. **No** |
| `barcodes`, `barcodes_gs1_nomenclature` | Barcode nomenclature only; `stock_barcode` (the scanning app) is `uninstallable` here. **Yes eventually** for a yard |
| `web_responsive` (vendored), `sapian_theme`, `sapian_theme_mail`, `sapian_theme_auth_signup` | Navigation and branding. Exercised incidentally, never tested as a flow |
| `base_import`, `base_import_module`, `base_install_request`, `rpc`, `api_doc`, `web_tour`, `web_unsplash`, `onboarding`, `mail_bot`, `mail_bot_hr`, `utm`, `phone_validation`, `analytic`, `resource*`, `uom`, `product`, `sales_team`, `http_routing`, `bus`, `web`, `web_hierarchy`, `html_editor`, `base`, `base_setup`, `portal`, `payment`, `account_payment` | Infrastructure and dependencies, not user-facing apps in their own right |

### Named in the brief, and NOT installed in this build

All are present in the addons path and merely uninstalled unless marked
otherwise, so "not installed" is a packaging choice, not a missing capability.

| App | Untested — would a first Ethiopian trading client need it? |
|---|---|
| **Point of Sale** (`point_of_sale`) | **Probably yes, and sooner than the plan assumes** — flow (f) showed an invoice never moves stock, and a counter-selling yard is exactly the POS case. The strongest candidate on this list |
| **Website / eCommerce** (`website`, `website_sale`) | **No** for a first client; and register item 11 records that `website_sale` breaks customer self-registration |
| **Manufacturing** (`mrp`) | **No** — a trader buys and resells |
| **Projects** (`project`), `hr_timesheet` | **No** for a trader; relevant only if they do contracting work |
| **Recruitment** (`hr_recruitment`) | **No** at seven employees |
| **Marketing** (`mass_mailing`), **Events**, **Surveys**, **eLearning** (`website_slides`) | **No** |
| **Maintenance**, **Repairs** (`repair`) | **No** |
| **Fleet** (`fleet`) | **Maybe** — a building-materials trader with delivery trucks has a real fleet, but it is not a go-live need |
| **CRM** (`crm`) | **Maybe** — the sales pipeline is a plausible second-phase sell |
| `hr_holidays`, `hr_expense`, `hr_attendance` | See flow (k). Leave tracking is the likeliest early request |
| `purchase_requisition`, `lunch` | **No** |
| `helpdesk`, `hr_appraisal`, `sign`, `planning`, `timesheet_grid`, `sale_subscription`, `stock_barcode` | **`uninstallable`** in this build — Enterprise modules whose dependencies are absent |
| `documents`, `quality`, `account_asset`, `account_budget` | **NOT PRESENT** in the addons path at all — Enterprise. `account_asset` matters eventually: a trader with vehicles and a warehouse needs depreciation, and there is none |

### Our own modules not installed in the shipped set

| Module | Note |
|---|---|
| `l10n_et_calendar`, `l10n_et_calendar_account`, `l10n_et_calendar_purchase` | Ethiopian calendar. **Directly relevant to findings c-3 and e-3** — the Ethiopian filing month has no representation anywhere partly because this is deferred. Untested |
| `vertical_pharma`, `sapian_demo_pharma` | The pharma vertical and its pitch tenant. Out of scope for a trading client |
| `sapian_dress_rehearsal` | Untested; not part of the shipped default set |
| `sapian_sentry` | Error reporting. Untested; worth enabling before a client goes live |
| `sapian_theme_website` | Bridge for `website`, which is not installed |

---

## New register entries this assessment owes

Written at the owner's direction so far: **23** (payslip prints an exempt
allowance as taxable), **24** (bank salary file exports empty account numbers
without warning), **25** (onboarding collects no company email or mail server),
and **26** (the Goods in Transit BLOCKER, root cause corrected in flow (m)).

**All twelve now written**, as entries **27–38**, on 17 Aug. The list below said
ten; it became twelve because the reconciliation item split into a missing UI (28)
and a missing importer (29), and the payments absence (30) was added — both at the
owner's direction, both commercial rather than defects. The original ten:

1. **No profit & loss, balance sheet, trial balance or general ledger exists in
   the build.** BLOCKER. Flow (m). The plan's *"use Odoo/OCA reports"* was never
   closed and nothing supplies them.
2. **Bank reconciliation has no widget, no menu and no importer** — and
   Community already finds the matching candidates, so the missing piece is a
   screen. Flow (i). This is a build opportunity as much as a defect.
3. **The VAT credit carried forward is stated but never carried**, and a VAT
   declaration has no state, so two can exist for one month and there is no record
   of what was filed. Flow (c), findings c-1 and c-2.
4. **Withholding appears only at posting**, so a draft bill's total differs from
   what posts, with nothing shown. Flow (b), finding b-1.
5. **No Ethiopian filing month exists anywhere** in payroll or VAT. Flow (e)
   finding e-3 and flow (c) finding c-3. Partly overlaps register item 9, which
   should be updated rather than duplicated — item 9 says the mapping is missing;
   this assessment measured that it is missing in the VAT report too.
6. **`data-templates/` ships only a `README.md`** — no onboarding import
   templates exist. Flow (g).
7. **Every internal user can read product cost prices**, i.e. the margin. Flow
   (h) finding h-2. A go-live configuration decision more than a defect.
8. **The customer-facing portal page's `<title>` is `Odoo`**, and the bot is still
   `OdooBot` on a page the client's customer sees. Flow (l), findings l-1 and l-2.
   l-2 confirms #49 is still outstanding rather than being new.
9. **Delivery drives stock negative with no warning or block.** Flow (f) finding
   f-1. Configuration decision for go-live.
10. **An employee cannot read their own payslip** — `l10n.et.payslip` has no
    portal route and no owner-scoped rule. Flow (k). NOT NEEDED YET, recorded so
    the absence is a decision rather than a surprise.
