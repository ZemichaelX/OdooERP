# sapian_dress_rehearsal — Pre-Release Dress Rehearsal

A **rerunnable ritual** that provisions a fresh tenant through the onboarding
wizard, drives one realistic month (August 2026) of business through the real
flows, then runs an **independent exam** that proves the books.

Not for client installs — this is an internal QA harness.

## Run it
```
scripts/dress_rehearsal.sh            # rebuilds scratch_rehearsal, keeps it
scripts/dress_rehearsal.sh my_db      # or a database name of your choice
```
The script drops and recreates the database, installs the module **and
`sapian_theme`**, provisions the month, prints the reconciliation table, and
**keeps the tenant** for manual click-through.

## Where this tenant is, and is not, the same as the demo

`sapian_demo_trader` builds the tenant a prospect SEES; this one builds the
tenant we PROVE the books on. They are different data on purpose — July vs
August, 7 orders vs 25, no payments vs a cash payment near the 50,000 cap, a
roster chosen to span every PAYE band vs one chosen to exercise the transport
allowance cap and a pension-exempt foreigner. Merging them would cost both
jobs their point.

**What must NOT differ is the product surface**, because the tenant you
rehearse on has to be the tenant you show:

| | demo trader | dress rehearsal |
|---|---|---|
| `sapian_theme` (brand + app rail) | installed by `build_demo.sh` | installed by `dress_rehearsal.sh` |
| Sale orders assigned to a real salesperson | yes | yes |
| Catalog entries handed to the wizard | its own dependencies | its own dependencies |
| Company logo | the client's mark | Odoo default — this tenant is not shown to anyone |
| Month, volume, payroll roster | July, small, six bands | August, 25 orders, allowance/foreigner cases |
| Sales list shows the order date | yes (demo-only view) | no — Odoo's default `create_date` |

The last two rows are deliberate divergence; every other row was an accident
that has been closed.

### The regression this file exists to stop repeating

Handing the wizard the WHOLE catalog worked only while the catalog held 15
curated entries. Seeding all 38 turned it into **28 uninstalled modules**, the
wizard tried to install them mid-provision, and `dress_rehearsal.sh` died on
"Odoo is currently processing a scheduled action". **The tests stayed green**,
because `_install_modules` skips installation in test mode — so this module was
only ever exercised in the one mode where the failure cannot happen.
`tests/test_catalog_pick.py` now asserts the mode-independent fact instead:
every entry the provisioner picks is already installed.

## The month (deterministic, all dated in August 2026)
- **25 sales orders** — mixed products, 3 partial deliveries (backorders), 1
  return + credit note. Invoiced on the ORDERED quantity, so VAT is decoupled
  from the physical delivery the stock check verifies.
- **12 purchases** — 10 goods POs (receipts feed stock; a mix above/below the
  20,000 WHT threshold) + 2 direct service bills (a no-TIN domestic supplier →
  30% punitive, a foreign digital provider → 15%).
- **1 payroll run, 5 employees** — incl. a transport allowance above the
  2,200/25%-of-salary cap and a pension-exempt foreign national.
- **Payments** — several bank settlements + one vendor CASH payment near the
  50,000 cap.
- **1 inventory adjustment** — shrinkage on Teff.

## The exam (each check recomputes expected by an INDEPENDENT path)
1. **Trial balance** — every posted move balances; company debits == credits.
2. **VAT** — 15% × untaxed base (from invoices) vs the declaration vs the GL.
3. **WHT** — recomputed per bill from the reference calculator; totals by rate;
   tied to the WHT-payable GL account.
4. **Payroll** — every payslip recomputed from the reference calculator with
   CONFIG-sourced bands/rates; asserts the config records exist (post-A1).
5. **Stock** — on-hand per product = received (PO) − delivered (SO) ±
   inventory adjustment, vs the stock quant.

`sapian.dress.rehearsal.exam.run(company)` returns the structured
reconciliation; `format_report(result)` renders the fixed-width table. The
test suite (`tests/`) provisions in a transaction and asserts every check
passes, plus three role walkthroughs over HTTP (warehouse receive, accountant
bill-with-WHT, HR payroll confirm).
