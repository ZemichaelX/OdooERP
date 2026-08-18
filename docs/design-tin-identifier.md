# Design note — the tax identifier on customer documents

**Status: DESIGN, measured 18 Aug 2026. No code written.** Blocker ahead of the
P&L (defect register entry 27); see `docs/product-readiness.md` flow (n) and the
TIN findings for how it surfaced.

**The decision taken:** fix the field the framework reads, not the one report.
Flipping `is_invoice_report` on our ET invoice would fix one document and leave
17 external-layout blocks still guarded on an empty `company.vat`.

---

## A correction to the evidence, before anything else

My earlier report said *"the customer invoice PDF has no TIN"* on the strength of
reading the PDF bytes. **Half of that evidence is invalid, and the half that
survives is the important half.**

Odoo splits a report into `bodies, res_ids, header, footer, …`
(`ir_actions_report._prepare_html`) and passes the header to wkhtmltopdf via
`--header-html`. Measured on the rendered invoice:

| Identifier | Which split part | Renders in this container? |
|---|---|---|
| **Buyer** TIN (`partner_id.vat`) | **bodies** | **yes** |
| **Seller** TIN (`company.vat`) | **header** | **no** |

This container's wkhtmltopdf is **0.12.6 without `(with patched qt)`**, so
`is_patched_qt = False` and `--header-html` content is dropped. **The seller block
would be missing from the PDF here whatever `company.vat` contained.**

So:

- **Container-independent and proven:** with `vat` empty the buyer TIN is absent
  from the invoice body; populating `vat` puts it there. Measured before/after on
  the bytes — `0022334455` absent → present.
- **Confounded, and withdrawn:** my claim that the *seller* TIN is missing from
  the PDF. The underlying defect is still real — the `t-if="company.vat"` guard
  fails on an empty field, confirmed in the HTML — but the PDF evidence for the
  seller half was measured on a build that drops that block regardless.

**Re-run the seller half on the documented Docker stack (patched wkhtmltopdf)
before quoting it.** This is defect register rule 5 in a new costume: the
environment that verified is not the environment that runs.

---

## 1. Populating `company.vat`, and `vat_label` on ET — what breaks

**Measured: it works, and the label works.** Setting the company partner's `vat`
to `0088776655` and `res.country` ET `vat_label` to `TIN` produced, in the
rendered invoice HTML:

```
Africa Avenue (Bole Road) Addis Ababa Ethiopia TIN: 0088776655
```

and in the PDF **body**, for the customer: `TIN: 0022334455`. The label is read
from `country_id.vat_label` with a fallback of `"Tax ID"`, so setting it is what
stops every document saying **VAT** where Ethiopia says **TIN**.

**What breaks — named before doing it:**

| Risk | Measured finding |
|---|---|
| Validation rejecting Ethiopian TINs | **Does not happen** — see §2 |
| UBL / e-invoicing XML changes | `account_edi_ubl_cii` (**installed**) reads `.vat` in **13 files** and emits it as `cbc:CompanyID`. It only fires when an EDI format is active on the journal or customer; Ethiopia has no UBL mandate and none is configured. **Low risk, must be re-checked before enabling any EDI format.** |
| `sale_edi_ubl`, `purchase_edi_ubl_bis3`, `snailmail_account`, `partner_autocomplete` | 1–2 files each reference `.vat`. `snailmail` and `partner_autocomplete` are IAP services that are not in use |
| Uniqueness / duplicate-partner warnings | None found; `vat` carries no unique constraint |
| Existing tenants | `vat_label` is a change to a **core data record** (`base.et`), not core code. Like the expense-account fix, it must be applied to databases that already exist — the same install-vs-upgrade trap |

**Nothing measured breaks.** The material risk is EDI, and it is dormant.

## 2. `base_vat` — measured, not assumed: it SKIPS, it does not reject

**Do not install it.** Measured by installing it on the readiness tenant and
writing values to an ET partner:

| Value written to `vat` | Result |
|---|---|
| `0088776655` (real TIN) | **ACCEPTED** |
| `0022334455` | **ACCEPTED** |
| `12345` | **ACCEPTED** |
| `ET0088776655` | **ACCEPTED** |
| `nonsense-xyz` | **ACCEPTED** |

Cause, confirmed in source and by direct call:
`_check_vat_number('ET', …)` returns **`True`** — because
`base_vat/models/res_partner.py:350` is
`return check_func(vat_number) if check_func else True`, and there is **no
`check_vat_et`**. **`stdnum` 1.19 ships 87 country packages and Ethiopia is not
one of them** (`eg`, `gh`, `ke`, `za` are; `et` is not).

So the feared outcome — a validator rejecting a valid Ethiopian TIN — **does not
occur**. But the useful outcome does not occur either: `base_vat` adds **zero**
validation for ET while switching on strict validation for every *other* country's
partners, which can start rejecting foreign suppliers' identifiers on data entry.

**`vat` exists without `base_vat`.** We get the field for free and keep our own
10-digit format check in `et_tax_calc.validate_tin`, which is stricter than
anything `base_vat` would give us here.

## 3. What happens to `l10n_et_tin`

**It stays, and `vat` becomes a mirror of it — not the other way round.**

The reason is that Ethiopia genuinely has two identifiers and the module already
models both: `l10n_et_tin` **and** `l10n_et_vat_reg_no` ("VAT registration
certificate number (distinct from the TIN)"). Core `vat` is one field and cannot
hold two. Retiring `l10n_et_tin` would also break things that are correct today:
the withholding engine's `has_tin` test, the 10-digit format constraint, the
`_commercial_fields` propagation to contacts, and our own two reports.

**Proposed shape:**

- `l10n_et_tin` remains the **system of record** — validated, indexed, propagated.
- `vat` is **populated from it** so the framework has something to print.
  Implemented as an inverse/onchange-style sync rather than a `related` field,
  because `related` would make `vat` read-only and fight core's own inverse on
  `vat` (`res.partner.vat` already declares `inverse="_inverse_vat"` under
  `base_vat`, and core writes to `vat` from several places).
- `l10n_et_vat_reg_no` is untouched and keeps its separate meaning.
- **Existing tenants need a backfill**, same shape as
  `_l10n_et_base_fix_default_expense_account`: idempotent, moves only partners
  whose `vat` is empty, never overwrites a value someone typed.

**The open input changes a value, not the mechanism.** When the accountants answer
whether the invoice must show the TIN, the VAT registration number, or both, the
answer selects **which field feeds `vat`** (and, if both, whether the second
prints as an extra line on our ET invoice). It does not change any of the above.

## 4. Does our `report_et_invoice` become redundant?

**No — and this is the honest answer rather than the convenient one.** Measured
side by side with `vat` populated:

| | core `report_invoice_with_payments` | our `report_et_invoice` |
|---|---|---|
| Buyer TIN | **yes** (body) | yes |
| Seller TIN | in the **header** (see the correction above) | **in the body**, as an explicit `Seller … TIN:` block |
| Explicit Seller / Buyer labelling | no — the seller is the letterhead | **yes** |
| Document titled *VAT Invoice* | no — "Invoice" | **yes** |

Two things ours carries that core cannot:

1. **The seller's TIN in the body rather than the letterhead.** That is not a
   styling preference: it is why ours printed the TIN in this container and core's
   did not. A document whose legal identifier lives in a page header is one
   misconfigured paper format away from being non-compliant.
2. **The words "VAT Invoice" and an explicit Seller/Buyer block**, which is the
   layout an Ethiopian VAT invoice is expected to take.

**But the fix is still the field, not the report.** Populating `vat` is what
repairs the other 17 layout blocks, the quotation, the delivery note and the POS
receipt — none of which our ET invoice touches. Once `vat` is populated, whether
we *also* make ours the default sending report is a separate, smaller decision,
and it needs the accountants' answer first.

## The guard, when this is built

**Read the SENT PDF's bytes and assert the identifier is in them** — not the
template, not the field. That is the only assertion that could not have passed
today. Concretely: send the invoice through `account.move.send.wizard`, capture
the attachment at the SMTP boundary as flow (a) did, extract the PDF text, and
assert both TINs are present.

**And it must run on a patched wkhtmltopdf**, or the seller half will pass
vacuously in exactly the way described in the correction above. If CI cannot
provide one, the guard must assert against the **rendered HTML** for the seller
half and say so, rather than quietly proving nothing.
