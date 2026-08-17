# Ethiopian tax reference for SapianERP

Every figure here carries its evidence and its confidence. **Do not build logic
off a line marked UNVERIFIED or CONTESTED.**

Last updated: 17 August 2026.

Confidence words used below:

- **VERIFIED** — two or more independent published sources agree, and where
  possible the figure has been reconciled against real data in the product.
- **PRACTITIONER** — one working Ethiopian accountant answered it in writing.
  Strong evidence of practice; not proof of the rule.
- **CONTESTED** — the practitioner and the published sources disagree.
- **UNVERIFIED** — asserted somewhere, not confirmed. Treat as a question.

---

## 1. Employment income tax — VERIFIED

Income Tax (Amendment) Proclamation **No. 1395/2025**, approved 17 July 2025,
in force from FY 2025/26. Replaced Proclamation 979/2016, which exempted only the
first 600 birr and had a 10% band. **Any Ethiopian payroll still running the old
brackets over-taxes every employee.**

Monthly, marginal, progressive:

| Monthly ETB | Rate |
|---|---|
| 0 – 2,000 | exempt |
| 2,000 – 4,000 | 15% |
| 4,000 – 7,000 | 20% |
| 7,000 – 10,000 | 25% |
| 10,000 – 14,000 | 30% |
| above 14,000 | 35% |

Equivalent shortcut, `tax = rate × income − constant`:

| Rate | Constant |
|---|---|
| 15% | 300 |
| 20% | 500 |
| 25% | 850 |
| 30% | 1,350 |
| 35% | 2,050 |

Both forms agree at every band edge: 4,000 → 300, 7,000 → 900, 10,000 → 1,650,
14,000 → 2,850.

**Reconciled against the product**, 17 Aug, on all six payslips of
`build_demo.sh`'s run — exact on both forms. See defect register item 20.

Sources: PwC Worldwide Tax Summaries (Ethiopia, individual — taxes on personal
income, reviewed 15 July 2026); Chambers and Partners on Proclamation 1395/2025;
TaxDev; KPMG.

Employees with **only** employment income do not file returns. The monthly
obligation is entirely the employer's.

---

## 2. Filing the monthly employment income tax — VERIFIED

**It is a window, not a deadline date.** The declaration for one Ethiopian month
is filed at any time during the *following* Ethiopian month.

The accountant's own example: *"Sene taxes must be reported from Hamle 01 to
Hamle 30."* PwC states the same rule from the other direction: *"by the end of
the month following the month the income was earned."*

Two independent confirmations. An earlier answer of "the 7th or 8th of the
subsequent Gregorian month" is **wrong** — those are the dates Ethiopian months
begin, not a deadline.

**Tax year: 8 July to 7 July** = Hamle 1 to Sene 30.

**What is filed — TWO CSV files**, per accountant 2:

1. **Schedule A employment income tax** per employee. Accountant 1 lists the
   columns as: name, date of employment, basic salary, all allowances, income tax.
2. **A separate CSV for pension** — the 18% total, being the 11% employer share
   and the 7% employee share.

**We have neither file.** Getting one example of each — an old month with the
names removed is fine — is the highest-value outstanding item in the project.
Everything about the export is guesswork until then.

**Which month the salary belongs to — the cycle is a business choice.** The two
accountants run it differently and both are correct:

| | Payroll cycle | Filing |
|---|---|---|
| Accountant 1 | Ethiopian month | Ethiopian month on the form, Gregorian dates |
| Accountant 2 | **Gregorian** month, *"to align with bank statements and simplify reconciliation"* | 1st–30th of the following Ethiopian month |

> **So make the payroll period configurable. The mapping to the Ethiopian filing
> month and its window is what is mandatory, and it is the same for both.**

---

## 3. Pension — VERIFIED by both practitioners

- Employee **7%**, employer **11%**, **18%** total.
- Base: **basic salary only**, not allowances. Both accountants, unprompted.
- **Filed on its own CSV**, separate from the income-tax file. Accountant 1:
  *"totally different from income tax."*

**Reconciled against the product**: payslip 5 of the demo run has basic 10,000
and gross 12,000, and pension is 700 — 7% of basic, not 840 of gross. The only
row in the data that can tell the difference, and it agrees.

**UNVERIFIED:** whether the pension CSV shares the income-tax window. Accountant
2 implies it does — both go up in the same 1st-to-30th period — but she was not
asked directly.

---

## 4. Transport allowance — RESOLVED

**The exemption is the lower of 2,200 birr and a quarter of the salary.**

Accountant 2, asked how much is free from tax: *"Below 2200 or quarter of the
salary."* Asked directly whether the lower-of rule is still correct: *"That is
exactly correct."* This agrees with 2merkato's account of the directive history —
the 2008 directive capped the exemption at 1,000 with a 25%-of-salary limit, and
the cap was later raised to 2,200.

Accountant 1 answered "flat 2,200". That is the limit that **always binds above
roughly 8,800 birr salary**, where a quarter exceeds 2,200 — so her answer was
incomplete rather than wrong, and it would only mis-state the exemption for
lower-paid staff.

**Build `min(25% × salary, 2,200)`.** Keep the cap and the percentage as settings
so a directive change is a settings edit, and show on the payslip which limit
bound. Getting this the other way round **under-taxes low earners and leaves the
employer liable for the shortfall plus penalties.**

PwC's deductions page is silent on transport allowance and does not bear on this
either way.

---

## 5. VAT — VERIFIED

- Standard rate **15%**, zero-rated **0%**.
- Registration threshold: taxable supplies expected to exceed **2,000,000 birr**
  in 12 months.
- Proclamation **No. 1341/2024**, in force June 2024; Regulation **No. 570/2025**,
  in force November 2025.
- Credit-invoice method: an invoice including VAT must be issued for all sales.

**Neither accountant's longest job is payroll, and neither trusts the tax
figures.** Accountant 1: longest is *"VAT"*; always checks *"Excel summations"* by
hand. Accountant 2: longest is **bank reconciliation**, then reconciling AP, AR and
the VAT and 3% WHT balances; always checks vouchers by hand, including *"that 15%
VAT and 3% WHT amounts are accurate"* and that invoice, receipt, purchase order and
delivery note match.

The common thread is **reconciliation, and distrust of computed tax.** See defect
register item 13 for what that means for the dashboard.

---

## 6. Withholding tax on domestic payments — VERIFIED rate, PRACTITIONER practice

**3%**, effective **7 August 2025** under the 1395/2025 amendment — raised from
2%, with the thresholds raised at the same time:

| Supply | Threshold |
|---|---|
| Goods | above **20,000** birr per transaction or supply contract |
| Services | above **10,000** birr per transaction or supply contract |

**30%** if the supplier does not present a TIN and business licence at payment,
and that becomes a final tax.

Note for anyone reading older material: **2% with 10,000 / 5,000 thresholds is
stale.** Several Ethiopian sites still publish it.

**Computed on the VAT-exclusive amount** — three independent confirmations
including the accountant. Worked example on 100,000 of goods:

```
subtotal            100,000
VAT 15%            + 15,000
withholding 3%      − 3,000     (3% of 100,000, not of 115,000)
paid to supplier    112,000
```

### Whether it appears on the invoice — CONTESTED, and permitted either way

| | Answer |
|---|---|
| Accountant 1 | *"No, it shows Before VAT, VAT and Total Price."* The 3% is deducted by the buyer at payment and evidenced by a withholding receipt |
| Accountant 2 | *"Yes. Under Ethiopian tax rules, a single commercial tax invoice can display both the 15% VAT added and the 3% Withholding Tax deducted to clearly show the net amount due from the buyer."* |

Accountant 2 gives the structure:

```
base amount (goods or services)
+ VAT 15%                          → gross bill
− withholding 3% of the BASE only  → never of the VAT-inclusive total
= net payable by the buyer
```

**Reading: showing it is permitted, not required.** Accountant 1 is describing her
own house practice. So this is a company setting — *show the withholding deduction
on the invoice* — and the default should be ON, because it tells the customer what
to pay.

### The three conditions — accountant 2, and this is the most useful answer received

Withholding applies only when **all three** hold. None of them is implemented.

**1. The buyer must be a withholding agent.**

- Applies: a government body, a legal entity (PLC, Share Company), or an
  organisation registered for WHT.
- Does **not** apply: an ordinary individual buying for personal use.

This is a dimension nobody had identified. It needs a flag on the partner, and it
means a retail sale to a walk-in customer is never withheld regardless of value.

**2. The value must clear the threshold, judged on the agreement.**

Accountant 2 is explicit and overrides accountant 1's rougher answer:

> *"The key factor is the total agreement value, not the size of each small
> invoice. If the agreement totals over ETB 10,000 (services) or ETB 20,000
> (goods): Yes, 3% WHT applies to every invoice, even if an individual invoice is
> for a tiny amount like ETB 1,000. Tax law looks at the entire contract to stop
> people from splitting one big order into many small invoices to avoid tax."*

Accountant 1 had said the aggregation window is *the month* — a practical proxy
her firm uses. **The contract is the unit.** Odoo has no supply-contract field, so
this needs one: a flag on the customer or the sales order meaning "this sits under
an agreement above the threshold — withhold on every invoice."

**3. The supplier must have valid credentials.** Valid TIN and business licence →
3%. Missing either → the buyer must withhold **30%**, and it is a final tax.

### Achievable design, stated honestly

The threshold cannot be decided from a single invoice, so full automation is not
possible and pretending otherwise would build something that quietly gets it
wrong. What is achievable:

- test the buyer flag and the TIN first — those are deterministic;
- apply the threshold per transaction by default;
- let an agreement be flagged on the customer or the order, forcing withholding on
  every invoice under it;
- and **surface the pattern the system cannot decide** — several sub-threshold
  invoices to one partner over a short period — on the compliance dashboard, so
  the accountant sees it.

That last item is the differentiator. It is the shape of the rule an Ethiopian
accountant would recognise immediately as written by someone who knows it.

---

## 7. Things in the 1395/2025 amendment we have not accounted for — UNVERIFIED

All from PwC's significant-developments page. **None of this is confirmed enough
to design against.** The first is the one that could change the product's market.

**Category A and Category B.** Three taxpayer categories became two, split at
**2,000,000 birr** turnover. PwC reports Category B pays a **gross sales tax of
2–9%** — a turnover tax, not a profit tax.

A large share of small Addis traders will sit below 2 million, so this is a
different tax regime from the one SapianERP currently models. **Verify before it
becomes a design assumption either way.**

**A 15% tax on undistributed profits.** New. Any PLC retaining earnings is
exposed — including Selam General Trading PLC. Few have adjusted for it, which
makes it a strong thing for the product to surface.

**A 2.5% minimum alternative tax.** A floor on business income tax, so a
loss-making year still owes something.

**Quarterly advance tax payments for large taxpayers.** New deadlines.

**Rental and business income** now progressive 0–35% for individuals; entities
stay at a flat 30%.

**Capital gains** unified at 15% on shares, bonds and buildings; a private home
held two years or more is exempt.

**Withholding on dividends rose to 15%** (from 10%), interest to 10%, royalties
to 5–10%.

---

## Sources

- PwC Worldwide Tax Summaries — Ethiopia: individual (taxes on personal income,
  deductions, tax administration, significant developments) and corporate
  (withholding taxes, significant developments). Reviewed 15 July 2026. Use this
  as the standing reference and re-check it each tax year.
- Chambers and Partners — *What's Changed under Ethiopia's New Income Tax
  (Amendment) Proclamation No. 1395/2025*
- KPMG — *Income Tax (Amendment) Proclamation*
- TaxDev — *Ethiopia's revised income tax explained*
- Haymanot & Advocates — *Ethiopia's New VAT Framework: Proclamation No.
  1341/2024 and Regulation No. 570/2025*
- 2merkato — *Non Taxable Transportation Allowance and Per Diem Amount Raised*.
  Note: 2merkato's withholding page still publishes the stale 2% figures.
- **Two practising Ethiopian accountants**, written answers, 17 August 2026, asked
  the same ten questions independently. They agree on the brackets, the filing
  window being an Ethiopian month, pension at 7% / 11% on basic salary only,
  withholding computed before VAT, and the thresholds.

  They disagree on three things, and the disagreements were informative:

  | | Accountant 1 | Accountant 2 | Resolution |
  |---|---|---|---|
  | Transport allowance | flat 2,200 | lower of 2,200 or a quarter of salary | **2** — matches the directive history; **1** is the case above ~8,800 salary |
  | Withholding on the invoice | no | yes, with a full structure | Permitted, not required → a setting |
  | Aggregation unit | the month | the agreement | **2** — and it matches the published anti-splitting rule |

  Where they disagreed, the more specific answer was the correct one each time.
  Worth remembering before treating any single practitioner's answer as the rule.
