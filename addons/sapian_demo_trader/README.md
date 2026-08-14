# sapian_demo_trader — Demo Trader Tenant (SapianERP)

The sales-demo tenant: **Selam General Trading PLC**, a fictional Addis Ababa
building-materials trader, provisioned through the real
`sapian.onboarding.wizard` and populated with one July-2026 month of trading
data through the real business flows. Demo and sales use only.

> **This file was rewritten in the pipeline/payroll/logo change.** It previously
> described a *different* tenant — Fasika Supermarket, teff, Awash Agro, a VAT
> credit of −2,850 — none of which has existed in the code for some time. A
> README that describes data the module does not create is worse than no README:
> it is what a salesperson reads the night before a demo. The figures below are
> the ones `tests/test_demo_trader_e2e.py` asserts.

## How it is built, and why not on install

Provisioning is **not** triggered by installing the module. There is no `demo/`
or `data/` entry: `sapian.demo.trader._provision_demo_tenant` is a plain model
method that `scripts/build_demo.sh` calls once the install has finished.

```bash
./scripts/build_demo.sh <db_name>          # drops, rebuilds, provisions, verifies
```

The build installs **`sapian_theme` alongside the demo module**, and the
verification step reads the COMPILED stylesheet to prove it took:
`--primary`, the navbar background and the login button must all be the brand,
and the app rail's CSS must be in the bundle. That is deliberately not "is the
theme in the install list" — a config line saying `-i sapian_theme` is exactly
what a purple demo would also have. Measured on a build without it, all five
checks go red.

The theme is a build decision, not a manifest dependency: a client may or may
not buy it, and the demo module must not force it into every database that
installs the demo.

Two earlier arrangements failed and the reasons are worth keeping: loading from
`demo/` meant the tenant only appeared with Odoo demo data on, which also
dragged in US placeholder companies; loading from `data/` ran mid-install, and
the chart the wizard had just loaded collided with `account`'s end-of-load
auto-install hook. So the demo data cannot load outside the demo context,
because it does not load automatically at all.

## What the demo shows

### The month that is on the books (posted, and tied out)

| | |
|---|---|
| **Quotation → delivery → VAT invoice (15%)** | Mebrat Construction, 40 corrugated sheets = 35,200; Abyssinia Hardware, rebar + 800 blocks = 80,100. Output VAT **17,295** on **115,300**. |
| **PO → receipt → vendor bill, 3% WHT** | Derba Midroc Cement Depot (TIN + licence): 30 quintals of cement + rebar = 68,800, withheld **2,064**. Cement is **ordered in quintals and lands in stock as bags**, 30 → 60. |
| **30% punitive WHT** | Yonas Transport, domestic with **no TIN**, 15,000 → **4,500** withheld, red MISSING row on the WHT summary. |
| **15% foreign digital WHT** | BuildSoft Cloud Ltd., 8,000 → **1,200**, "N/A (foreign)" in the TIN column. |
| **VAT declaration** | output 17,295 − input 13,770 = **+3,525 PAYABLE**. A materials retailer turns stock within weeks, so a normal month is payable; a credit only happens in a heavy stocking-up month. |
| **WHT summary** | 2,064 + 4,500 + 1,200 = **7,764**, GL tie-out green. |

### The sales pipeline (nothing posted)

Three **draft** quotations, one **sent**, and one **confirmed and delivered but
deliberately not invoiced** — so there is a real order to press *Create Invoice*
on, live, in front of the prospect.

None of it reaches the general ledger, which is the property to preserve if the
list grows: **add drafts freely, invoice nothing**, and every figure in the
table above stays where it is by construction rather than by luck. The set lives
in `demo_catalogue.QUOTATIONS`.

Every quotation is under **50,000 including VAT**, so a presenter improvising a
cash receipt on one is never blocked by our own cash-cap validator on camera.
The invoiced July flow is not held to that — the 92,115 Abyssinia credit sale is
exactly the transaction the cap exists to keep out of cash.

**Every order is assigned to the demo login as salesperson, and that is
load-bearing.** Odoo's Sales app opens on
`sale.action_quotations_with_onboarding`, whose context is
`{'search_default_my_quotation': 1}` — a default filter of `user_id = uid`.
Provisioning runs through `odoo shell` as OdooBot, so orders that took the
default salesperson were invisible to the demo login, and **Odoo filled the
empty list with its onboarding sample data**: ghosted quotations for Henry
Campbell and Thomas Passot, priced in dollars, under a "Beat competitors with
stunning quotations!" video. American names and USD in software sold as
Ethiopian — the same fault the US placeholder companies are archived to
prevent, and it survived because "there are orders in the database" was true.
`_demo_salesperson()` sets it explicitly; a test asserts it through the same
filter the app applies.

### The payroll run — one employee per PAYE band

This is the part that most differentiates the product, so it is built to be
readable at a glance rather than described. Proclamation 1395/2025 has six
monthly bands and the roster puts exactly one person in each:

| Band | Rate | Who | Basic | Taxable | PAYE |
|---|---|---|---|---|---|
| 0 – 2,000 | 0% | Cleaner | 1,800 | 1,800 | 0 |
| 2,000 – 4,000 | 15% | Office Assistant | 3,500 | 3,500 | 225 |
| 4,000 – 7,000 | 20% | Storekeeper | 6,000 | 6,000 | 700 |
| 7,000 – 10,000 | 25% | Sales Officer | 10,000 | 10,000 | 1,650 |
| 10,000 – 14,000 | 30% | Driver & Loader | 10,000 | **12,000** | 2,250 |
| above 14,000 | 35% | General Manager | 25,000 | 25,000 | 6,700 |

Totals: gross **58,300**, PAYE **11,525**, pension **3,941** employee /
**6,193** employer, net **42,834**, posted journal **64,493** balanced, plus the
bank transfer CSV.

Two things are deliberate and should survive any edit:

- **The driver reaches band 5 through taxable overtime, not through his basic
  wage.** Two employees on the same 10,000 basic landing in different bands is
  the clearest available statement that an input line moves the tax and that the
  pension base does not follow it — pension is 7%/11% of the **basic** wage, so
  it is computed on 56,300, not on 58,300.
- **Chaltu Deme has no POESSA pension ID**, which fires the fix-before-filing
  banner on the pension schedule. Do not "fix" it.

Every payslip figure is computed by the real engine from
`demo_catalogue.EMPLOYEES`; nothing writes an amount. A hand-written payslip is
a number nobody can defend, and it would eventually get quoted at a prospect.

### The dates on screen

Odoo's Quotations list shows **Creation Date**, not the order date —
`sale.view_quotation_tree` (`sale/views/sale_order_views.xml:216`) explicitly
replaces `date_order` with `create_date`, and this repo ships no `sale.order`
view of its own. For a real client the two are minutes apart. For a scripted
demo `create_date` is the build timestamp on every row, so the list read
"seven orders all placed at 15:51 today" — a fixture, not a month of trading.

Two changes, both scoped to the demo:

- `views/sale_order_views.xml` puts the **order date** back in the Quotations
  list. It lives in this module, which never reaches a client database, so
  Odoo's default is untouched for everyone else.
- Every order is **dated inside July** and stays there. Odoo rewrites
  `date_order` to `now()` on confirmation
  (`sale.order._prepare_confirmation_values`), so the provisioner writes the
  intended date back afterwards — otherwise even an order created with a July
  date comes out stamped today.

Still on build-time dates and **not** fixed: stock transfers
(`stock.picking.date_done`). Visible in Inventory, not in the Sales list this
was about.

### The tenant's own logo

`static/img/selam_logo.png` — a generated geometric mark (a rounded tile in the
tenant's own primary colour carrying a stack of blocks, beside a plain sans
wordmark). **Deliberately not the Sapian logo**, and deliberately not Odoo's
default.

It is the demo *client's* letterhead. Putting our logo on it would teach a
prospect that documents printed out of the system carry the vendor's brand, in
the same session where we claim the product is white-labelled; leaving Odoo's
default contradicts the branding claim on screen while it is being made. It is
demo furniture with no brand status — replace it freely. The real brand assets
live in `brand/`.

## Dates

Every date is pinned inside **July 2026**, so each statutory report has one
clean period window with exact GL tie-outs, independent of the wall clock. July
2026 is also the most recent closed month at the time this data was built; the
pin is what makes goldens possible at all, so it is not computed from the
calendar.

## Amounts and our own validators

The demo must never display data our own rules would reject.

- **ETB 50,000 cash cap** (Art. 81, Proc 1395/2025) — `l10n_et_base` validates
  `account.payment` and nothing else. The demo creates **no payments**, so the
  cap cannot be tripped at all. Beyond that, every OPEN quotation is under the
  cap so a cash receipt improvised on camera is never blocked; the invoiced
  flow is not, because a 92,115 credit sale to a wholesaler is precisely what
  the cap exists to keep out of cash.
- **WHT thresholds** — the two service bills are above the 10,000-birr services
  threshold on purpose. Lowering the 15,000 delivery figure deletes the punitive
  30% moment from the demo.

## Verification

`tests/test_demo_trader_e2e.py` re-runs the exact provisioning code on a test
company and asserts every hand-computed total above, the report renders and the
tie-outs. Beyond the goldens it asserts three invariants rather than counts:

- every PAYE band in the company's own effective-dated table is occupied by at
  least one payslip (a seventh band in a future proclamation makes this fail,
  which is the correct outcome);
- the pipeline has drafts, a sent quotation and a confirmed order, and none of
  the uninvoiced ones carries an invoice;
- `company.uses_default_logo` is **False** — not merely that `logo` is
  non-empty, which is always true (`res.company.logo` has `default=_get_logo`)
  and would pass on a tenant showing Odoo's stock wordmark;
- every sale order is assigned to the demo login, asserted through the same
  `user_id = uid` filter the Sales app applies, so "there are orders" cannot
  again be true while the app shows US sample data.
