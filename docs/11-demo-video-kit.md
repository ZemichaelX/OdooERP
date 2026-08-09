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

**Why it is three phases, and why not `-i sapian_demo_trader --with-demo`:**
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

### Verify before recording

```bash
# exactly one company, on the Ethiopian chart
docker compose -f docker/docker-compose.yml exec -T db \
  psql -U odoo -d demo_materials -c "SELECT name, chart_template FROM res_company;"
```
Expected — and nothing else:
```
           name            | chart_template
---------------------------+----------------
 Selam General Trading PLC | et
```

Log in with `admin` / `admin` (deliberate for a local demo).

### CHECK THE PRICES FIRST

Every price lives in **`addons/sapian_demo_trader/models/demo_catalogue.py`**,
in one marked block. Materials prices move weekly and a wrong one is the single
thing a materials trader will catch instantly.

Entries are tagged `[RANGE]` (inside a supplied range), `[DERIVED]` (computed
from one), or **`[UNVERIFIED]`** — nobody has checked those. Set them, then
rebuild with the command above.

## 2. What the tenant contains

**Ten products in the units of the trade** — three cements (bag), three rebars
and binding wire (kg), corrugated sheet and HCB (piece), sand (m³).

**The unit moment.** Cement is bought by the **quintal** and sold by the
**bag**: 1 quintal = 2 bags of 50 kg. The July purchase is 30 quintals and
stock shows **60 bags**. Cement has no opening stock, so that 60 is the
conversion and nothing else. (Odoo 19 has no UoM categories — the quintal is a
related unit worth two bags, and the product offers both on order lines.)

**One real month, July 2026** — every figure ties out:

| Flow | Detail | Result |
|---|---|---|
| Sale → Mebrat Construction | 40 sheets G32 @ 800 | 32,000 + 4,800 VAT |
| Sale → Abyssinia Hardware | 100 kg rebar 12 @ 170 + 500 HCB @ 14 | 24,000 + 3,600 VAT |
| Purchase ← Derba Midroc Depot (TIN + licence) | 30 quintals cement + 50 kg rebar 8 | 52,000, **3% WHT = 1,560** |
| Bill ← Yonas Transport (**NO TIN**) | delivery & loading | 15,000, **30% WHT = 4,500** |
| Bill ← BuildSoft Cloud (foreign digital) | software | 8,000, **15% WHT = 1,200** |

Output VAT 8,400 · input VAT 11,250 · net VAT −2,850 credit · WHT total 7,260.
Payroll: gross 23,800, PAYE 3,900, net 18,374, one employee missing a POESSA ID
so the fix-before-filing banner shows.

## 3. Suggested beats

1. **Company switcher** — one Ethiopian company. Nothing foreign, nothing fake.
2. **Product list** — cement in bags, rebar in kg, sand in m³. His trade.
3. **The quintal→bag conversion** — open the July purchase order: 30 quintals
   ordered, 60 bags received. This is the thirty-second credibility test.
4. **The withholding moment** — the Derba bill withholds 3%; the Yonas bill,
   from a supplier with no TIN, withholds **30%**. Show the WHT summary with
   the red MISSING row. This is the strongest moment in the video.
5. **VAT declaration and WHT summary** — live from posted entries, tied to the
   general ledger.
6. **Payroll** — PAYE and pension computed from effective-dated bands.

## 4. Rebuilding mid-session

The build is idempotent and non-destructive to your other databases; it drops
and recreates only the database you name. If you change a price, rerun the same
one command — never edit the running database, or the next rebuild loses it.
