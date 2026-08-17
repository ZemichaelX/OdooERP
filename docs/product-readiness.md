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
stock physically. The **12 of 12 products with no category at all** is
**DEMO DATA produced by OUR CODE** (`sapian_demo_trader` creates them). **Severity:
SERIOUS.** For the demo it is embarrassing — a prospect asking "what's my gross
margin?" gets nothing. For a first client it is a go-live configuration decision
that must be made deliberately: periodic with a physical count, or perpetual with
categories, accounts and a costing method configured.

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
that only grows.** **Attribution: DEMO DATA produced by OUR CODE** (products
created by `sapian_demo_trader` without a category), with **STOCK ODOO** supplying
the fallback. **Severity: SERIOUS** — judged against the go-live scale it is not a
BLOCKER, because the client can still operate, invoice, pay and file every
statutory return; but it is the most consequential thing found in tier 1, and no
demo should be given with it in place.

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
