# SapianERP — defect register (moved)

**This register is no longer kept in the public repository.** It lives in the
private `sapianerp-internal` repository, under the same path.

It was moved on 18 August 2026, when this repository was opened. The register
records unfixed defects, their reproductions, and the reasoning behind decisions
that were taken and sometimes reversed. That is exactly the material a reader
should not be handed about a product being sold, and it is the only reason it
moved — nothing in it was wrong.

Other documents in `docs/` cite it by entry number ("register item 13", "rule
5"). Those citations still resolve, in the private repository. The five rules it
carries are restated in `CLAUDE.md`, which is public, so the parts that govern
how work is done here are not lost.

Ask the owner for access if you need the register itself.

---

# Open questions recorded here, and why here

Three entries follow. They are kept in the **public** file deliberately, and
that is a departure from the paragraph above, so the reasoning is stated rather
than assumed.

The register moved because it records defects in the product. These three are
not that. They are open questions about **published Ethiopian tax law** that
nobody on this project has yet answered, and the product's behaviour where an
answer is missing is to say so — on the page, and in
`addons/sapian_landing/data/filing_period_data.xml`, which a client can read.
Hiding the question while shipping the disclaimer would be the worse of the two.

Each names the evidence that would close it. None of them may be closed by
reasoning across from another: the reference is explicit that where its two
accountants disagreed, the more specific answer was right each time, and the
question below has not been put to either of them.

## Open 1 — Is the VAT filing period an Ethiopian month or a Gregorian one?

**Status: OPEN. Product behaviour: Gregorian, labelled UNVERIFIED.**

`docs/ethiopian-tax-reference.md` §5 is headed "VAT — VERIFIED", and that
verification covers the 15% rate, the 2,000,000 registration threshold, the
proclamation numbers and the credit-invoice method. It says nothing at all about
the tax period, the calendar it is counted in, or the return deadline.

The landing page therefore shows VAT for the previous Gregorian month, which is
what the product has always done, and the seeded rule carries the word
UNVERIFIED so nobody mistakes "unchanged" for "confirmed".

**Evidence that would close it, cheapest first:**

1. One screenshot of the **VAT declaration screen on etax.mor.gov.et**, showing
   the period selector: does it offer Ethiopian months or Gregorian ones?
2. The **article of Proclamation 1341/2024 or Regulation 570/2025** that sets
   the VAT tax period and the return deadline.
3. Either accountant, asked directly: *"For VAT, is the declaration period an
   Ethiopian month or a Gregorian month, and by when is it due?"*

Item 1 also answers Open 2, and the reference already records that we hold
neither of the two payroll CSV files and calls getting them the highest-value
outstanding item in the project — the period selector is on the same screens.

**What changes when it closes:** one row in `sapian.filing.period`, and one row
in `sapian.filing.deadline` if the window is not 30 days. No code.

## Open 2 — Is the withholding remittance period an Ethiopian month or a Gregorian one?

**Status: OPEN. Product behaviour: Gregorian, labelled UNVERIFIED.**

`docs/ethiopian-tax-reference.md` §6 is headed "VERIFIED rate, PRACTITIONER
practice". It covers the 3% rate and its 7 August 2025 effective date, the
20,000 / 10,000 thresholds, the punitive 30%, VAT-exclusive computation, whether
the deduction appears on the invoice (CONTESTED), and the three conditions under
which withholding applies at all. It says nothing about when withholding is
remitted or over what period it is summarised.

**Evidence that would close it:**

1. The **withholding declaration screen on etax.mor.gov.et** and its period
   selector.
2. The **article of Proclamation 979/2016 as amended by 1395/2025** that sets
   the remittance period and deadline.
3. Either accountant, asked directly, in the same message as Open 1.

**What changes when it closes:** one row in `sapian.filing.period`, plus a
deadline row if 30 days is wrong. No code.

## Open 3 — Does the pension declaration share the employment income tax window?

**Status: OPEN, and the reference marks this exact question open. Product
behaviour: Gregorian, labelled UNVERIFIED.**

`docs/ethiopian-tax-reference.md` §3 is headed "Pension — VERIFIED by both
practitioners", and that verification is the 7% / 11% split and the basic-salary
base. On the window it says, in as many words:

> **UNVERIFIED:** whether the pension CSV shares the income-tax window.
> Accountant 2 implies it does — both go up in the same 1st-to-30th period — but
> she was not asked directly.

An implication from one practitioner is not evidence, and §3 also records
accountant 1 saying the pension file is *"totally different from income tax"*.

**This one has a consequence the other two do not.** Employment income tax is now
counted in Ethiopian months and pension in Gregorian ones, and a company runs
payroll once. So on any tenant **at most one of the two figures can be stated**:
an Ethiopian-cycle payroll produces the PAYE figure and no pension figure, and a
Gregorian-cycle one produces neither, because the mapping in Open 4 is also
unsettled. The page says which and why rather than showing a number. That is not
a reason to guess the answer — it is a reason this question is worth an hour of
somebody's time.

**Evidence that would close it:**

1. Either accountant, asked directly: *"Does the POESSA pension declaration
   cover the same Ethiopian month as the Schedule A income-tax file, or a
   different period?"* — §3 records that accountant 2 was never asked this.
2. The **article of Proclamation 1268/2022** that sets the remittance period,
   and whether "within 30 days" is a day count or the end of a following month.
3. One filed POESSA declaration with the names removed, showing its period.

**What changes when it closes:** one row in `sapian.filing.period`, and the demo
tenant's company-scoped override in
`sapian_demo_trader/models/sapian_demo_trader.py::_record_filing_period_overrides`
can go. No code.

## Open 4 — Which filing month does a GREGORIAN-cycle payroll run belong to?

**Status: OPEN. Product behaviour: refuses to place the run, and says so.**

Recorded because it was found while fixing Open 1–3 and is the reason the
employment income tax figure is unavailable on a tenant that runs Gregorian
payroll — which is one of the two cycles the reference says are both correct.

`docs/ethiopian-tax-reference.md` §2 records the cycle as a business choice:

| | Payroll cycle | Filing |
|---|---|---|
| Accountant 1 | Ethiopian month | Ethiopian month on the form, Gregorian dates |
| Accountant 2 | **Gregorian** month | 1st–30th of the following Ethiopian month |

> **So make the payroll period configurable. The mapping to the Ethiopian filing
> month and its window is what is mandatory, and it is the same for both.**

For accountant 1 the mapping is the identity and the product implements it. For
accountant 2 the reference gives the **window** and never states **which
Ethiopian month goes on the form**. "The month the run ends in" and "the month
with the greatest overlap" happen to agree for most Gregorian months, and both
are inferences from a sentence about the window — which is exactly the kind of
reasoning §2's own resolution table warns against.

So the page places a run whose period IS the filing month, and for any other run
states that it cannot place it and why. It does not pick.

**Evidence that would close it:**

1. Either accountant, asked directly: *"You run payroll on Gregorian months. On
   the Schedule A form you file in Hamle, which month is written as the period?"*
2. One filed Schedule A CSV from a Gregorian-cycle employer, names removed, with
   its period field visible.

**What changes when it closes:** the mapping in
`sapian_landing/wizard/sapian_landing.py::_payroll_run_domain`, which is the one
of these four that is code rather than data — deliberately, because a mapping
between two calendars is arithmetic and arithmetic does not belong in a
configuration row.
