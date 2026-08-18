# Upstream issue — FILED

**Filed as [odoo/odoo#282865](https://github.com/odoo/odoo/issues/282865)** —
*"[l10n_et] Default expense account is a current asset (230100 Goods in Transit),
so purchases never reach the P&L"*, opened by **ZemichaelX** against **19.0**,
17 Aug 2026.

**Our override is not a stopgap — it is the only mechanism that ever moves an
existing database.** A chart template is read once, at chart load, and is not
re-read on upgrade. A merged upstream fix therefore corrects the *next* Ethiopian
deployment and touches **no existing tenant at all**;
`_l10n_et_base_fix_default_expense_account` is the only thing that rewrites
`company.expense_account_id` and the `ir.default` behind it on a database already
in production.

*(Historical note, kept because it explains why this file exists: the session that
drafted this could not post it. GitHub write access there was scoped to
`zemichaelx/odooerp`, and attaching `odoo/odoo` was refused —
"cross-tier adds are not supported". Read access worked, so the duplicate search
below was genuinely run.)*

The text below is what was filed.

**Duplicate check, run 17 Aug 2026:** searched `odoo/odoo` issues for the
Ethiopian chart's default expense account; 25 loosely-matching results, **none of
them this defect**. The closest in shape is
[#260030](https://github.com/odoo/odoo/issues/260030) —
*"[19.0] l10n_ca: Exchange difference accounts default to Cash Discount Gain/Loss
in fresh Canadian database"* — which is a useful precedent for both the title
format and the fact that localisation-default bugs are accepted as issues.

**Why file it at all, when we have already overridden it:** the mapping is in
Odoo's own localisation, so **every Odoo-based Ethiopian deployment has this
defect**, competitors included. A one-line upstream change fixes it for all of
them. Our override in `l10n_et_base` is the interim measure, not the destination.
See defect register entry 26.

---

## Title

**As filed:**

```
[l10n_et] Default expense account is a current asset (230100 Goods in Transit), so purchases never reach the P&L
```

*(The draft below the title was filed as written. The title itself was shortened
on filing from the drafted version — `[19.0] l10n_et: company default expense
account is 2301 Goods in Transit (asset_current), so purchases never reach the
P&L` — noted so this file does not misreport what is on the issue.)*

## Body

## Impact

`l10n_et` sets the Ethiopian company's default **expense** account to an
`asset_current` account. Every product that carries no account of its own — which
is every product a typical client imports — books its purchases into a current
asset. The result on a fresh Ethiopian database:

- the **profit & loss shows revenue with no cost of sales**;
- the **balance sheet carries a transit balance that only grows**;
- **nothing raises a warning**, because the books still balance — a balanced
  ledger cannot distinguish a misclassified debit from a correct one.

Measured on a demo Ethiopian company: `230100 Goods in Transit` accumulated
**453,800.00 ETB** of purchases, and a single 54,000.00 purchase overstated
reported profit by exactly **54,000.00**.

## Cause

`odoo/addons/l10n_et/models/template_et.py`, in `_get_et_res_company`:

```python
'expense_account_id': 'l10n_et2301',
'income_account_id': 'l10n_et1100',
```

`l10n_et2301` is `2301 Goods in Transit`, declared `asset_current` in
`data/template/account.account-et.csv`:

```
"l10n_et2301","2301","Goods in Transit","asset_current",""
```

That value then reaches products two ways, both wrong:

1. `account/models/chart_template.py` `_post_load_data` copies
   `company.expense_account_id` into `ir.default` for
   `product.category.property_account_expense_categ_id`, so the default product
   category resolves to it.
2. `product.template._get_product_accounts` falls back to
   `(self.company_id or self.env.company).expense_account_id` when neither the
   product nor its category carries one.

So both surviving links of the resolution chain point at the same asset account.

## Steps to reproduce

1. Create a database with `l10n_et` installed and a company on chart `et`.
2. Create a product with no accounts set (`name` and `type` only).
3. Create a vendor bill for that product and post it.

**Expected:** the product line debits an `expense` account.
**Actual:** it debits `230100 Goods in Transit`, `account_type = asset_current`.

Checking the company directly:

```python
env.company.expense_account_id                # -> 230100 Goods in Transit
env.company.expense_account_id.account_type   # -> 'asset_current'
```

## Suggested fix

The chart already ships a suitable account — `l10n_et5111`,
`5111 Cost of Goods and Services`, declared `expense`:

```
"l10n_et5111","5111","Cost of Goods and Services","expense",""
```

so the change is one line in `_get_et_res_company`:

```diff
-                'expense_account_id': 'l10n_et2301',
+                'expense_account_id': 'l10n_et5111',
```

`income_account_id` (`l10n_et1100`, *Sales of Goods and Services*, `income`) is
already correct and needs no change.

Databases that already loaded the chart will keep the old value, since the
template is not re-read on upgrade, so a migration moving companies still on
`l10n_et2301` would be needed to complete the fix for existing deployments.

## Version

19.0 (reproduced at `ccce9fc`). The same mapping is present on earlier branches
carrying this template and is worth checking there too.
