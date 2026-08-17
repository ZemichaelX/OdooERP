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
