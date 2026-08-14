# l10n_et_calendar — the Ethiopian (Ge'ez) calendar

A calendar that is wrong by one day is worse than no calendar, because it will
be trusted. Everything below is arranged around that.

The module is two layers:

| layer | where | needs Odoo? | tested by |
|---|---|---|---|
| the conversion arithmetic | `reference/et_calendar.py` | no | `tests_fast/test_et_calendar.py` — 125 goldens |
| the ORM mirror | `models/l10n_et_date_mixin.py` | yes | `tests/test_et_date_mixin.py` — 27 tests |

CLAUDE.md rule 10: the arithmetic is pure Python in `reference/`, importable
without a running Odoo, and the Odoo layer only calls it.

## The arithmetic

**Leap rule.** A year is a leap year iff `year % 4 == 3`, with **no century
exception** — the Ethiopian calendar never adopted the Gregorian reform. Every
fourth year Pagume has 6 days instead of 5. Sourced from the calendar's own
definition (it is the Julian rule offset by the epoch), not inferred from
worked examples.

**Epoch.** Meskerem 1, 1 EC = 29 August 8 CE (Julian) = **JDN 1,724,221**.
Everything else is arithmetic around that pivot: Ethiopian → JDN → Gregorian
and back, using Fliegel & Van Flandern (CACM 11:10, 1968) for the Gregorian
side.

**Structure.** 12 months of exactly 30 days, then Pagume of 5 or 6.

**Validated against three authorities**, none of them this code's own output:

1. the project's own anchors, quoted from proclamations —
   8 Jul 2025 = Hamle 1, 2017 · 8 Jul 2014 = Hamle 1, 2006 · 7 Aug 2025 = Nehase 1, 2017;
2. an independent integer Julian-calendar implementation (Richards' algorithm),
   asserting the epoch identity from the other direction;
3. a one-off recorded cross-check against the `ethiopian-date` PyPI package.
   It is *not* a test dependency and is not imported — the comparison was run
   once and its results were written into the goldens.

Two traps are tested rather than assumed:

* **Hamle 1 is not always 8 July.** It steps to 7 July for part of each
  four-year cycle. The test records the measured step function; an earlier
  claim in this repo that it is "always 8 July" was wrong and the test that
  proved it wrong is still there.
* **The Gregorian-year offset flips.** EC + 7 before the Ethiopian new year in
  September, EC + 8 after it.

## The mirror

`l10n.et.date.mixin` gives any model a stored, searchable Ethiopian twin for
any Gregorian date field.

### How a model opts in

Three lines per date, and nothing else:

```python
class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.et.date.mixin"]

    _l10n_et_date_map = {
        "invoice_date": "l10n_et_invoice_date",
        "invoice_date_due": "l10n_et_invoice_date_due",
    }

    l10n_et_invoice_date = l10n_et_mirror_field("Invoice Date (ET)")
    l10n_et_invoice_date_due = l10n_et_mirror_field("Due Date (ET)")
```

`l10n_et_mirror_field` is a factory: `compute`, `store`, `index`, `readonly`,
`copy` and the `depends` all live in the mixin, so a declaration cannot get
them subtly wrong.

The fields are **declared, not injected**. Odoo can add fields to a class
programmatically (`odoo.orm.model_classes.add_field`), which would remove even
those two lines — but that function is ORM internals: it was
`BaseModel._add_field` before Odoo 19 and moved in it. CLAUDE.md rule 1 says
extend through inheritance. Two declarative lines is a small price for a module
that still imports on Odoo 20.

### A model with two dates

Invoice date plus due date is the ordinary case, not the edge one, so the map
is a dict rather than a single pair from the start:

* **one compute, one `depends`.** `@api.depends` is a lambda over
  `_l10n_et_date_map`, so both sources trigger it and adding a third date later
  needs no decorator edit;
* **the dates stay independent.** The compute writes each target from its own
  source, so moving the due date does not touch the invoice date — asserted in
  `test_a_model_with_two_dates_keeps_them_independent`;
* **each empty source gives an empty mirror.** An invoice with no due date must
  not grow one in Ethiopian;
* the cost is one column and one index **per date** — see the measurement
  below.

### Date sources and Datetime sources

An invoice date is a `Date`. A purchase order's deadline and expected arrival
are `Datetime`s. The mixin reads the source field's own type and handles the
difference itself, so a bridge never has to:

```
2025-07-07 22:00 UTC  =  2025-07-08 01:00 in Addis Ababa
                      =  Hamle 1, 2017 EC     (what is stored)
                      =  Sene 30, 2017 EC     (what a naive .date() would store)
```

Odoo stores Datetimes as naive UTC and Ethiopia is UTC+3, so every order
entered after 21:00 UTC would be filed a day early. The conversion runs through
`ETHIOPIAN_TZ`, which is **fixed** rather than read from a setting: "what
Ethiopian date was this?" is a question about the day in Ethiopia, Ethiopia has
one timezone and has never observed daylight saving, and a per-user timezone
would make a stored value depend on who saved the record while a per-company one
would silently invalidate every stored mirror the day somebody edited it.

Both sides of the midnight boundary are tested (20:59:59 and 21:00:00 UTC), and
setting `ETHIOPIAN_TZ` to UTC turns three tests red — proven, not assumed.

### What is stored, and why it is not the pretty string

The stored value is canonical and format-independent: `2017-11-01`. Not
"Hamle 1, 2017".

1. **The display format must not be able to invalidate a million rows.** If the
   formatted string were stored, `depends` would have to include the company
   setting, and a consultant flipping Latin to Amharic mid-demo would queue a
   recompute of every mirrored date in the database. Canonical storage makes
   that setting a pure display concern — no write at all. Asserted in
   `test_changing_the_display_format_rewrites_nothing`, against raw SQL.
2. **It sorts.** "Meskerem 1, 2018" sorts before "Hamle 1, 2017"
   alphabetically, which is wrong by eight months.
3. **It filters like a period filter should.** `2017-11-…` is all of Hamle
   2017 — one Ethiopian month, which is *not* expressible as a Gregorian one
   (Hamle 2017 runs 8 July – 6 August 2025).

The human-readable form is produced at display time by `l10n_et_display()`, so
a mirrored date costs exactly one column.

### Read-only, and why there is no two-way editing

The mirror is `readonly`, with no inverse. Two-way editing was considered and
rejected:

* the Gregorian field is the source of truth for every other part of the system
  — a due date drives payment terms, ageing and reminders — so an Ethiopian
  write would have to round-trip through it anyway;
* an inverse turns one number into two writable representations of the same
  fact, and any parse failure (a typo'd `2017-13-07`, which is Pagume 7 in a
  non-leap year and does not exist) becomes a validation error on a field the
  user did not think they were editing;
* the demand is to *read* Ethiopian dates on documents and to *filter* by
  Ethiopian months. Neither needs a writable field.

Date **entry** in Ethiopian is a date-picker question, and pickers are out of
scope for this module.

### What it costs on a million rows

Measured, not estimated: PostgreSQL 16, four tables of exactly 1,000,000 rows,
`ANALYZE`d, sizes from `pg_relation_size` / `pg_indexes_size`.

| table | heap | indexes | total |
|---|---|---|---|
| one date, no mirror | 35 MB | 0 | 35 MB |
| one date **+ mirror** | 50 MB | 6.8 MB | **57 MB** |
| two dates, no mirrors | 43 MB | 0 | 43 MB |
| two dates **+ two mirrors** | 66 MB | 14 MB | **79 MB** |

So **one mirrored date costs ≈ 22 MB per million rows** (≈ 15 MB heap +
≈ 7 MB index), and **two cost ≈ 36 MB** — slightly less than double, because
the row header is already paid for. The value itself is 11 bytes on disk
(`'2017-11-01'`, 10 characters plus a 1-byte varlena header); the rest is
alignment and page overhead.

For scale: a million invoices is a very large Ethiopian SME. At 100,000
invoices with both dates mirrored the cost is under 4 MB.

The index earns its keep — same table, same query, three plans:

```
month filter, index available     Bitmap Index Scan   7.9 ms
same filter, index disabled       Parallel Seq Scan  30.2 ms
exact date, index available       Bitmap Index Scan   0.28 ms
```

One caveat, stated because it is a property of the *client's* database and not
of this code: the measurement ran on a `C`-collation database, where PostgreSQL
can serve a `LIKE '2017-11-%'` prefix from a plain btree index. On a database
created with a non-`C` collation it cannot, and the prefix filter degrades to a
sequential scan. The range form is index-safe under every collation, so prefer
it in domains:

```python
[("l10n_et_invoice_date", ">=", "2017-11-01"),
 ("l10n_et_invoice_date", "<=", "2017-11-30")]
```

## Company settings

Both per company (CLAUDE.md rule 3): a group can hold an Ethiopian trading
company and an export arm that invoices in Gregorian.

| setting | values | default |
|---|---|---|
| `l10n_et_date_format` | Latin (`Hamle 1, 2017`) · Amharic (`ሐምሌ 1 ቀን 2017 ዓ.ም.`) · numeric (`01/11/2017`) | Latin |
| `l10n_et_report_calendar` | Gregorian only · Ethiopian only · both | both |

Month names ship from the reference library as **data**, in Amharic and Latin
transliteration and in no English, and are wrapped in `_()` at the Odoo layer.
A hardcoded English month inside a localisation library is a translation nobody
can ever correct.

## Dependencies

`base` and `base_setup` — nothing else, and the whole transitive closure
(`base`, `base_setup`, `web`) is asserted in
`test_nothing_of_ours_is_pulled_in_transitively`. This is the calendar, not a
tax feature: a client who wants Ethiopian dates on a purchase order must not be
handed a chart of accounts along with them.

`base_setup` is there because the two settings live on the Settings page, whose
view this module inherits. Referencing another module's XML id without
depending on it works only for as long as somebody else happens to install it.

## Where the dates actually appear

Nowhere, on their own — this module ships the mixin, not the documents. Two
auto-installing bridges put the dates on records, each depending on the
calendar and on one Odoo app:

| bridge | model | dates |
|---|---|---|
| `l10n_et_calendar_account` | `account.move` | invoice date, due date |
| `l10n_et_calendar_purchase` | `purchase.order` | order deadline, expected arrival |

`auto_install: True` means a bridge appears by itself exactly when both its
sides are installed, and stays away otherwise — which is what keeps this module
standing alone. Each bridge is two field declarations and two view
inheritances, with **no logic**: if a bridge appears to need a method, that is
the mixin missing something, because a rule implemented twice in two bridges is
a rule that will diverge.

## Running the tests

```bash
pytest addons/l10n_et_calendar/reference/ tests_fast/     # no Odoo needed
docker compose -f docker/docker-compose.yml run --rm odoo \
  odoo -d scratch_cal -i l10n_et_calendar \
       --test-enable --test-tags /l10n_et_calendar --stop-after-init
```

The Odoo tests build their two-date host model at setup with
`add_to_registry` — the same call Odoo's own `test_orm` suite uses — and remove
it again afterwards. It carries `_module = None` so it can never be collected
into a real database, and the table it creates disappears with the test
transaction. Shipping a probe model instead would put two real columns on a
real table in every client database for the sake of a test.
