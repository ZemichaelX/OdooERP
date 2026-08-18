# l10n_et_base — Ethiopia Accounting Base (SapianERP)

Extends the **core `l10n_et`** chart template (code `'et'`, auto-installed for
Ethiopian companies) with the SapianERP Ethiopian accounting localization.
Epic 3 of `docs/plan-2026/10-claude-code-roadmap.md`; functional spec
`docs/plan-2026/07-ethiopian-localization.md` §1.

## What it adds

### Chart of accounts (template merge — core files untouched)
- New accounts: `3009` PAYE (Employment Income Tax) Payable,
  `2302` Customs Duty Clearing.
- Account-type corrections for mistyped core accounts (shipped by core as
  assets/liabilities on the wrong side): `2212` VAT Receivable → asset,
  `2213`/`2214` WHT receivables → asset, `3006` → *Withholding Tax Payable*
  (liability, name typo fixed), `3007` VAT Payable → liability,
  `3008` Federal Income Tax → liability.
- Core already provides 15% VAT (sale + purchase), 0% and exempt codes;
  this module adds the **Zero-Rated** and **VAT Exempt** fiscal positions and
  maps the core taxes onto them (Proc 1341/2024).
- **Default expense account: `5111` Cost of Goods and Services, replacing core's
  `2301` Goods in Transit.** Core `l10n_et` names a current *asset* as the
  company's default expense account, and Odoo's chart loader copies that into the
  product-category default. Since `_get_product_accounts` resolves
  product → category → company, every product without an account of its own booked
  its purchases into an asset: the P&L showed revenue with no cost of sales and the
  balance sheet carried a transit balance that only grew. **The books still
  balanced**, which is why nothing complained — a balanced ledger cannot tell a
  misclassified debit from a correct one.

  Fresh chart loads take the corrected value from the template merge; companies
  that loaded the chart earlier are moved by
  `_l10n_et_base_fix_default_expense_account`, called from the post-init hook and
  from the `19.0.1.5.0` migration. That repair moves **only** a company still
  sitting on the core default, so a client who chose their own expense account is
  left alone.

  **This is core Odoo's defect, not ours, and it affects every Odoo-based
  Ethiopian deployment** — `odoo/addons/l10n_et/models/template_et.py`, the
  `expense_account_id` key of `_get_et_res_company`. Filed upstream as
  **[odoo/odoo#282865](https://github.com/odoo/odoo/issues/282865)**; the override
  here stays the interim measure regardless of what upstream does, because a
  merged fix would not touch a database that has already loaded the chart. See
  defect register entry 26.

### Withholding tax automation (Aug 2025 rules)
- New effective-dated config model `l10n.et.wht.config` (rates, thresholds,
  `punitive_respects_thresholds` flag, mandatory `source_note`), seeded at chart
  load with 3% / 30% / 15%, thresholds 20,000 / 10,000, effective 2025-08-01.
- On posting a **vendor bill**, the engine groups lines by supply kind
  (product type `service` → services, otherwise goods; a partner flagged
  *Foreign Digital Service Provider* makes the whole bill foreign-digital),
  computes applicability via the reference calculator, and links the matching
  negative purchase tax (credits *Withholding Tax Payable*). Idempotent on
  re-post; decision logged in the chatter with the source note.
- Printable **WHT Certificate** (`Print` menu on the bill).
- A 3% sale-side WHT code is included for sales where the customer withholds.

### Cash payment cap (Proc 1395/2025)
- Effective-dated `l10n.et.cash.cap.config` (default cap ETB 30,000/party/day,
  enforcement `warn`, seeded effective 2025-07-01). Outbound **cash** payments
  breaching the daily per-party total either warn (audit message on the payment)
  or block (`ValidationError`) — configurable, no code release needed.

### Social welfare levy on imports (Reg. 519/2022)
**3% of the aggregate CIF value of imported goods**, effective **6 August 2022**
(gazetted 22 August 2022), Council of Ministers Regulation No. 519/2022.
Effective-dated `l10n.et.social.welfare.levy.config` (rate + mandatory
`source_note`), seeded per company at chart load; a rate change is a NEW record.

Three things about it, all easy to get backwards, all enforced rather than
merely documented:

| property | how it is held |
|---|---|
| **in addition** to duty, excise, VAT, surtax | its own tax record; the posted total is CIF + levy |
| **a cost, NOT creditable** against income tax | the tax posts to `5931` *Social Welfare Levy on Imports* (**expense**), and `_check_tax_posts_to_a_cost_account` refuses a configuration whose tax posts to a receivable |
| **enters nobody else's base** | `include_base_amount = False` **and** `is_base_affected = False`, asserted against posted amounts on a real bill, not against the checkboxes |
| **no threshold** | stated explicitly in the reference calculator and pinned by `test_there_is_no_threshold` — the neighbouring WHT rules do have thresholds, which is the invitation to invent one here |

Exempt (no levy, reason recorded): diplomatic privilege · goods already subject
to import surtax under Regulation 133/2007 · goods excluded by a Ministry of
Finance directive.

> **A published competitor guide describes this as an "Import Advance Income
> Tax, 3% of CIF, offset against income tax".** No authority for such a tax was
> found — it is absent from PwC's Ethiopian import-tax page and from the Art. 92
> withholding categories. That reading would capitalise 3% of every consignment
> as a receivable that is never recovered. It is refused by a constraint, and
> the attempt is exercised by a test.

### The tax identifier on documents
`l10n_et_tin` is the **system of record** — validated, indexed, propagated to
contacts — and core `vat` is **populated from it** so the framework has something
to print. Every core template guards its tax-ID line on `vat`: the shared external
layout in **17 places**, plus the invoice, the quotation and the POS receipt. With
`vat` empty a tenant sent invoices carrying **no tax identifier at all** — measured
on the bytes of the PDF a customer received.

One-way mirror, never a merge: `l10n_et_vat_reg_no` stays separate (Ethiopia has a
TIN *and* a VAT registration number, which one core field cannot hold), and a `vat`
somebody typed is **never** overwritten. Existing databases are filled by
`_l10n_et_backfill_vat_from_tin` (post-init hook + `19.0.1.6.0` migration).

`res.country` ET gets `vat_label = TIN`, so documents say **TIN** and not "Tax ID".
Applied in **code**, not XML: `ir_model_data` for `base.et` is `noupdate = true`,
so a data record targeting it is skipped **in silence** — the file loads, nothing
is written, nothing is logged.

`base_vat` is deliberately **NOT** installed: `stdnum` has no Ethiopian module and
`base_vat` has no `check_vat_et`, so it accepts anything for ET (measured: it
accepted `nonsense-xyz`) while switching on strict validation for every other
country. See `docs/design-tin-identifier.md`.

### Partner compliance fields
TIN (10-digit format-validated + normalized via the reference calculator), VAT
registration no., business licence no. + expiry (expired ⇒ punitive WHT),
foreign-digital flag, Amharic name. TIN/licence propagate from the commercial
entity to its contacts (`_commercial_fields`). Shown on a finance-only partner
tab.

## Design decisions
- **WHT on the bill, not at payment.** Odoo 19 ships a payment-time framework
  (`l10n_account_withholding_tax`); spec 07 §1 and the epic DoD require the WHT
  line and certificate at bill level, and the core `l10n_et` module models ET
  withholding the same way (negative-percent taxes). Revisit if MoR practice
  moves to payment-time withholding.
- **All math in `reference/et_tax_calc.py`** (pure Python, golden-tested in
  `tests_fast/`); the Odoo layer never re-implements it (CLAUDE.md rule #10).
- **Interpretation defaults pending accountant sign-off** (record in the client
  manifest before go-live): punitive rate fires when either TIN *or* licence is
  missing; punitive gated by thresholds (config-flippable); foreign digital 15%
  has no threshold and ignores compliance flags; TIN validation is format-only
  (no public MoR checksum); thresholds/cap are strictly exclusive.

## Tests
- Fast (no Odoo): `pytest tests_fast/` — reference calculator golden values.
- Integration: `--test-enable -i l10n_et_base` on a scratch DB — WHT postings,
  cash cap, partner compliance, effective dating, trial balance, and the default
  expense account (`test_expense_account_default.py`).
- The expense-account guard was **proved red before the fix**: 4 of 4 failed on
  the pre-fix tree, reporting *"a posted vendor bill for 54,000.00 of goods landed
  in 230100 (Goods in Transit), typed 'asset_current'"* and *"posting a 54000.00
  purchase moved the derived profit & loss by 0.00"*. After the fix, 71 tests pass
  with 0 skipped on **both** paths that matter — a fresh `-i` install and a `-u`
  upgrade — because a template change applies at install and is skipped at
  upgrade.

## Follow-ups (out of this epic)
Withholding on dividends, interest, royalties, management and technical fees —
rates are known, effective dates are not, and no rule enters the code without
one · MAT 2.5% informational computation · VAT registration-threshold (2M) warning ·
NBE FX reference-rate import · WHT remittance-30-day reminder · tax-report tags
for the new WHT codes (Epic 5 `l10n_et_reports`) · Amharic `.po`.

**Re-verify every rate/threshold against the Ministry of Revenue before each
client go-live.**
