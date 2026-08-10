# Demo video kit — building-materials pitch

For recording the SapianERP sales demo for a building-materials and hardware
shop in Addis Ababa (2–5 staff). Everything the tenant contains is in the
module, so every rebuild is identical — no database is ever hand-edited.

## 1. Data prep

### Build the demo database from nothing

```bash
./scripts/build_demo.sh demo_materials
```

That is the whole command. It takes a second argument for the demo module, so a
pharma pitch is one flag away once `sapian_demo_pharma` is converted to the same
pattern:

```bash
./scripts/build_demo.sh demo_pharma sapian_demo_pharma   # not yet converted
```

**Why it is phased, and why not `-i sapian_demo_trader --with-demo`:**
Odoo's own demo data ships US placeholder companies (`My Company (San
Francisco)`, `My US Company`, `My Company (Chicago)`) and a website bound to the
wrong company. A prospect must never see a US company list in software sold as
Ethiopian. So Odoo demo data stays **off**, and the tenant is provisioned by the
build script once the install has finished — never during it, because module
data loads mid-install and collides with Odoo's end-of-load chart auto-install.
But with demo off the single company is created on `generic_coa`
with country US, and Odoo does not allow switching charts afterwards — so the
country is set to Ethiopia *before* the accounting modules install. That is the
same two-phase dance `scripts/provision_client.sh` performs for a real client,
which means recording the demo is a rehearsal of the actual deployment.

### Verification is part of the build

The last phase asserts the three things that have to be true before you point a
camera at it, and exits non-zero if any fails:

```
CHECK companies=1
CHECK charts=et
CHECK group_uom=True
```

Exactly one company, on the Ethiopian chart, with **Units of Measure &
Packagings** switched on. That last one is not cosmetic: Odoo hides every unit
field unless it is enabled, so with it off the product form shows no unit and
the purchase order has no unit column — the quintal→bag conversion below is
data nobody can see. If the build says FAILED, do not record it.

Log in with `admin` / `admin` (deliberate for a local demo).

### CHECK THE PRICES FIRST

Every price lives in **`addons/sapian_demo_trader/models/demo_catalogue.py`**,
in one marked block. Materials prices move weekly and a wrong one is the single
thing a materials trader will catch instantly.

Every entry is sourced as of 10 August 2026 — nothing is a placeholder:

- `[LIST]` — Con Proxy / @MaterialProxy_Bot daily Addis construction price
  list, 23 July 2026, before VAT, aggregated across suppliers.
- `[OWNER]` — Zemichael, 10 August 2026.
- `[DERIVED]` — a cost computed from a sourced sale price at the ≈9% margin the
  sourced cement pair implies, or a per-bag figure from a per-quintal one.
- `[DEMO]` — the two services only. Not market prices: figures chosen to drive
  the withholding paths, each saying which one.

**If you change a price, the July invoice totals change with it** — every order
line reads its price from this file. The numbers in §2 below are computed from
it, not fixed. Rebuild and re-read this page before recording.

## 2. What the tenant contains

**Ten products in the units of the trade** — three cements (bag), three rebars
and binding wire (kg), corrugated sheet and HCB (piece), sand (m³).

**Cement is priced by type, not one price for all three.** OPC (Dangote) sells
at **1,100 per bag** / 2,200 per quintal; PPC (Habesha, Derba) at **1,000 per
bag** / 2,000 per quintal. Three cements at an identical price is exactly what
a materials trader notices.

**The unit moment.** Cement is bought by the **quintal** and sold by the
**bag**: 1 quintal = 2 bags of 50 kg. The July purchase is 30 quintals and
stock shows **60 bags**. Cement has no opening stock, so that 60 is the
conversion and nothing else. (Odoo 19 has no UoM categories — the quintal is a
related unit worth two bags, and the product offers both on order lines.)

**One real month, July 2026** — every figure ties out:

| Flow | Detail | Result |
|---|---|---|
| Sale → Mebrat Construction | 40 sheets G32 @ 880 | 35,200 + 5,280 VAT |
| Sale → Abyssinia Hardware | 100 kg rebar 12 @ 193 + 800 HCB @ 76 | 80,100 + 12,015 VAT |
| Purchase ← Derba Midroc Depot (TIN + licence) | 30 quintals cement OPC @ 2,000 + 50 kg rebar 8 @ 176 | 68,800, **3% WHT = 2,064** |
| Bill ← Yonas Transport (**NO TIN**) | delivery & loading | 15,000, **30% WHT = 4,500** |
| Bill ← BuildSoft Cloud (foreign digital) | software | 8,000, **15% WHT = 1,200** |

Output VAT 17,295 · input VAT 13,770 · **net VAT 3,525 PAYABLE** · WHT total
7,764. Payroll: gross 23,800, PAYE 3,900, net 18,374, one employee missing a
POESSA ID so the fix-before-filing banner shows.

**Say "payable", not "credit".** July ends owing 3,525 to the MoR, and that is
deliberate: a materials retailer buys stock and turns it within weeks, so a
normal month has output VAT above input. A VAT credit is what a stocking-up
month looks like, not a trading one. If a prospect asks, that is the answer.

## 3. Suggested beats

1. **Company switcher** — one Ethiopian company. Nothing foreign, nothing fake.
   Note what is *not* in the menu bar: no Manufacturing, Fleet, Repair, Project
   or Website. The tenant installs only what it demonstrates.
2. **Product list** — cement in bags, rebar in kg, sand in m³. His trade. OPC
   at 1,100 a bag and PPC at 1,000 — priced by type, not one price for all.
3. **The quintal→bag conversion** — open the July purchase order: 30 quintals
   ordered at 2,000, 60 bags received. The thirty-second credibility test.
4. **The withholding moment** — the Derba bill withholds 3% (**2,064** on
   68,800); the Yonas bill, from a supplier with no TIN, withholds **30%**
   (**4,500** on 15,000). Show the WHT summary with the red MISSING row, and
   the 7,764 total. This is the strongest moment in the video.
5. **VAT declaration and WHT summary** — live from posted entries, tied to the
   general ledger. Output 17,295, input 13,770, **3,525 payable**.
6. **Payroll** — PAYE and pension computed from effective-dated bands.
7. **The Module Catalog** — 7 enabled, 8 available. Use it when someone asks
   "so it does manufacturing?": yes, and it is off because you are not paying
   for it today. Better than the apps being absent, and better than them
   cluttering the menu bar of a hardware shop.

## 4. Rebuilding mid-session

The build is idempotent and non-destructive to your other databases; it drops
and recreates only the database you name. If you change a price, rerun the same
one command — never edit the running database, or the next rebuild loses it.
