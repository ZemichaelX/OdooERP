# sapian_demo_trader — Demo Trader Tenant (SapianERP)

The sales-demo tenant (Epic C, final build epic): **Selam General Trading PLC**,
provisioned through the real `sapian.onboarding.wizard` and populated with one
July-2026 month of realistic Ethiopian trading data via the real business flows.
Install with demo data enabled; demo/sales use only.

## What the demo shows (every compliance path firing)
- Quotation → delivery → **VAT invoice (15%)**: Fasika Supermarket (teff,
  36,800) and Zemen Distribution (consulting + coffee, 27,600).
- PO → receipt → vendor bill with **3% WHT** (Awash Agro, compliant supplier,
  52,000 → 1,560 withheld).
- Direct bills: **30% punitive WHT** (Habesha General Services — domestic, NO
  TIN → red MISSING row on the WHT summary) and **15% foreign digital WHT**
  (CloudServe Digital Inc. → "N/A (foreign)" TIN column).
- **Payroll run** (3 employees, Amharic+English names): both golden cases
  (10,000 basic; 10,000 + 2,000 taxable overtime) + below-threshold 1,800;
  posted 26,198 journal, bank transfer CSV. Chaltu Deme deliberately has **no
  POESSA pension ID** → fix-before-filing banner on the pension schedule.
- July **VAT declaration** (output 8,400 / input 11,250 / net −2,850 credit)
  and **WHT summary** (7,260) pre-created, all GL tie-outs green.

All dates pinned inside July 2026 → single clean period per statutory report,
wall-clock independent.

## Where the demo lives
Local scratch databases carrying the Selam tenant: **`scratch_final`** (primary,
used for manual UI testing) and `scratch_epicC3` / `scratch_bugfix` (regression
copies). Provisioning archives the Odoo core demo companies ("My US Company",
"My Company (Chicago)") so the company switcher shows only real companies.

## Verification
`tests/test_demo_trader_e2e.py` re-runs the exact provisioning code on a test
company and asserts every hand-computed total above plus report renders and
tie-outs. This is the epic's golden verification — the demo numbers can never
drift from the tested ones.
