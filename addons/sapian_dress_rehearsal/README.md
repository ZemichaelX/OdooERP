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
The script drops and recreates the database, installs the module, provisions
the month, prints the reconciliation table, and **keeps the tenant** for manual
click-through.

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
