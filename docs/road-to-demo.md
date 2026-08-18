# Road to a public demo

What has to be true before SapianERP can be shown to a client the way GraceERP
shows theirs at `system.grace-erp-consultancy.com`.

Written 17 August 2026. Plain language on purpose — this one is for reading, not
for implementing. The implementable version is `docs/work-queue.md`; the evidence
behind every claim is in `docs/defect-register.md` and
`docs/product-readiness.md`.

**Owner column:** *Code* means Claude Code can do it. *Zemichael* means it needs a
person — money, a domain, a phone call, or an accountant's answer.

---

## Stage 1 — Make the numbers legal and complete

These are the things that would embarrass us in front of an accountant. **GraceERP
already has all four.** This is the floor, not the differentiator.

| # | What | Owner | State |
|---|---|---|---|
| 1 | **Invoices must show the TIN.** Today they do not — `company.vat` is empty, so 17 layout blocks print nothing | Code | In progress |
| 2 | **Purchases must land in an expense account.** They were landing in `230100 Goods in Transit`, a current asset | Code | **Done 17 Aug**, plus upstream issue odoo/odoo#282865 |
| 3 | **Profit and Loss.** Does not exist. Odoo Community ships none | Code | Designed, not built |
| 4 | **Balance Sheet.** Same | Code | Designed, not built |

After these four the system is *accounting-correct*. A client can file an annual
return and face a bank.

---

## Stage 2 — Make it look like our product, not Odoo's

| # | What | Owner | State |
|---|---|---|---|
| 5 | **SapianBot, not OdooBot.** The bot authors every system message in every chatter | Code | PR #49, half built, has an order-dependent bug |
| 6 | **Four outgoing emails still say "Powered by Odoo"** — one of them goes to the client's own customer | Code | Queued |
| 7 | **Colour leaks on the login page** — one link and the focus rings still render the client's palette | Code | Queued |
| 8 | **A landing page, and a grid button that goes both ways.** Today it opens an admin list | Code | Queued, needs a decision on which page |

After this, nobody looking at it can tell what it is built on.

---

## Stage 3 — Make the demo believable

Nobody has started this, and it is what a client actually judges. They will click
around, and the numbers have to hold up.

| # | What | Owner |
|---|---|---|
| 9 | **Demo data that tells one coherent story.** Today: products with no category, one payroll run, a shop with no shops configured, stock that never moved | Code |
| 10 | **A landing page with real figures on it** — the first thing anyone sees on logging in | Code |

The story a trading company demo has to tell, end to end: buy → receive → sell →
deliver → invoice → get paid → pay staff → file. Every number consistent with every
other number, because someone *will* add them up.

---

## Stage 4 — Put it online

Mostly not code. This is the stage that turns a laptop into a demo.

| # | What | Owner |
|---|---|---|
| 11 | **Renew sapiantech.com.** It expired. `support@sapiantech.com` is dead mail on every page of the product, and every "Powered by SapianERP" link points at nothing | Zemichael |
| 12 | **Host it publicly** — a server, a domain, HTTPS. GraceERP's equivalent is `system.grace-erp-consultancy.com` | Zemichael |
| 13 | **Working email from that domain**, so invoices stop leaving as `odoobot@example.com` | Both |

**Stages 1 to 4 and the demo exists.**

---

## Stage 5 — The reasons to buy, not just to look

Stages 1–4 get us level with GraceERP. This stage is what beats them.

| # | What | Why it wins | Owner |
|---|---|---|---|
| 14 | **Every report proves its own numbers.** Already true of the VAT report — extend it to the P&L and balance sheet | Both accountants said, unprompted, that they do not trust computed figures. One re-adds in Excel; the other checks vouchers by hand. Odoo does not do this. OCA does not. Enterprise does not. GraceERP cannot | Code |
| 15 | **The compliance dashboard** — what is due, what does not reconcile, what looks wrong | The front door of the product. Needs the two e-Tax CSVs first | Both |
| 16 | **A bank reconciliation screen** | Both accountants' longest monthly job. Odoo's matching engine is already in Community and narrowed 23 candidates to 1 on 3 of 4 lines unaided — only the screen is missing. Measured at 600–2,400 interactions a month that a one-click screen would remove | Code |
| 17 | **Withholding done properly** — is the buyer an agent, contract totals, invoice-splitting detection | The rate and thresholds already work. What is missing is the part an Ethiopian accountant would immediately recognise as written by someone who knows the rule | Code |

---

## What GraceERP has, and what it cost them

Measured from their own Reporting menu on 17 August: they run
**`base_accounting_kit`** by Cybrosys — the free Odoo Apps Store module. Day Book,
Cash Book, Bank Book and Assets together are its signature.

So they have a P&L and a balance sheet, and it cost them a free install. **Parity is
an afternoon for anyone**, and that same module is our escape hatch if a sale ever
needs parity tomorrow.

What they do not have: anything Ethiopian in those reports, and no proof that any
number ties to the ledger.

**We are not building to catch up. We are building to pass them.**

---

## Waiting on other people

Nothing in stages 1–3 is blocked by these, but stage 5 is.

- **The two e-Tax CSV files** — one for Schedule A employment income tax, one for the
  18% pension. Both accountants confirm they exist; neither has sent an example. We
  cannot build the export from a description, and generating those two files is the
  single highest-value thing this product could do for either of them.
- **Four questions** — does a shop receipt need a certified cash register machine; do
  shelf prices include VAT; must an invoice show the TIN, the VAT registration
  number, or both; and what is account `592100 "Other"`.
- **Sample bank statement exports** from CBE, Awash, Dashen or Abyssinia. No upstream
  author will ever have those files, which is exactly why an importer for them is
  worth building.

---

## Rough shape

| When | What |
|---|---|
| Today and tomorrow | Stage 1 — the numbers become legal and complete |
| The following days | Stages 2 and 3 — it looks like ours and the demo holds up |
| Depends on Zemichael | Stage 4 — domain, host, email |
| The month after | Stage 5 — the part that wins deals |

Stage 5 is the only stage a competitor cannot copy in an afternoon.
