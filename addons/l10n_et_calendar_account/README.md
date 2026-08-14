# l10n_et_calendar_account — Ethiopian dates on invoices

A bridge. It exists so that `l10n_et_calendar` never has to depend on
`account`: the calendar is the calendar, and a client who wants Ethiopian dates
on a purchase order must not be handed a chart of accounts with them — a claim
`l10n_et_calendar`'s own CI job asserts against the database.

`auto_install: True`, so it appears by itself exactly when both sides are
already installed, and stays away when either is not. CI walks that: Accounting
alone → no bridge; add the calendar → this bridge appears on its own.

## What it adds

| where | what |
|---|---|
| `account.move` | `l10n_et_invoice_date`, `l10n_et_invoice_date_due` — stored, indexed, read-only |
| invoice form | each Ethiopian date beside the Gregorian one it mirrors |
| customer invoice list | Ethiopian invoice date as an optional column (it sorts, because the stored form is canonical) |
| printed invoice | both dates, gated by the company's **Calendar on Documents** setting |

## No logic

The whole module is two field declarations and two view inheritances. Every
rule a mirrored date obeys — the compute, the storage, the index, read-only,
and the Date-versus-Datetime handling — lives in `l10n.et.date.mixin`.

If this bridge ever appears to need a method, that is a signal the mixin is
missing something. A rule implemented twice in two bridges is a rule that will
diverge, and the two will diverge on a date.

## The report gate

The template replaces each date's output with a pair of lines, each gated by
`l10n_et_report_shows()`:

* **Both** (default) — the Gregorian date, and the Ethiopian one beneath it.
* **Ethiopian only** — the Gregorian line is *gone*, not merely joined. A
  setting that only ever adds a line is not a choice of calendar, and the test
  asserts the disappearance in both directions.
* **Gregorian only** — as Odoo ships it.

## Tests

15 tests. The interesting ones assert against **rendered output**, not against
the template source — a template that silently stopped inheriting still looks
correct in a diff:

* the fields are in the arch `get_view` returns, so a moved element in a future
  Odoo version fails here rather than in a demo;
* the setting really flips which calendar prints, both ways;
* `test_the_pdf_really_is_a_pdf` renders an actual PDF and checks the magic
  bytes and a minimum size. It lives in its own file as an `HttpCase`, because
  under `--test-enable` Odoo short-circuits PDF rendering to HTML
  (`ir_actions_report.py:1027`) and forcing the real render without a live
  server makes wkhtmltopdf hang.

```bash
docker compose -f docker/docker-compose.yml run --rm odoo \
  odoo -d scratch_bridge -u l10n_et_calendar_account \
       --test-enable --test-tags /l10n_et_calendar_account \
       --workers=0 --stop-after-init
```
