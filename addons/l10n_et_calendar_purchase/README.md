# l10n_et_calendar_purchase — Ethiopian dates on purchase orders

A bridge, same shape and same reasoning as `l10n_et_calendar_account`:
`auto_install: True`, two field declarations, two view inheritances, no logic.

## What it adds

| where | what |
|---|---|
| `purchase.order` | `l10n_et_date_order`, `l10n_et_date_planned` — stored, indexed, read-only |
| purchase order form | each Ethiopian date beside the Gregorian one it mirrors |
| printed order / RFQ | both dates, gated by the company's **Calendar on Documents** setting |

## The one real difference: these are Datetimes

`date_order` (Order Deadline) and `date_planned` (Expected Arrival) are
**Datetime** fields, where an invoice date is a Date. Odoo stores Datetimes as
naive UTC and Ethiopia is UTC+3, so taking `.date()` off the stored value is
wrong by a day for every order entered after 21:00 UTC:

```
2025-07-07 22:00 UTC  =  2025-07-08 01:00 in Addis Ababa
                      =  Hamle 1, 2017 EC        (correct)
                      =  Sene 30, 2017 EC        (what a naive .date() gives)
```

That conversion lives in `l10n.et.date.mixin`, which reads the source field's
own type — **not here**. A bridge is a declaration; putting a timezone
conversion in one would be putting a one-day error in a file nobody reads.
Both sides of the boundary are tested, here and in the mixin's own suite.

## One documented gap, not an omission

Odoo prints the **Order Deadline** only while the order is a request for
quotation. Once it is confirmed, the same block prints the Confirmation Date
(`date_approve`) instead — and `date_approve` is not one of the two fields in
scope for this work, so no Ethiopian date appears beside it. **Expected
Arrival prints in both states.** There is a test that confirms an order and
asserts the Ethiopian expected arrival is still on the PDF, so the boundary is
recorded rather than discovered during a demo.

## Tests

17 tests, including the evening-order boundary in both directions, a
one-domain Ethiopian month filter, the form arch, the report gate both ways,
and a real PDF (an `HttpCase` — see the invoice bridge's README for why).

```bash
docker compose -f docker/docker-compose.yml run --rm odoo \
  odoo -d scratch_bridge -u l10n_et_calendar_purchase \
       --test-enable --test-tags /l10n_et_calendar_purchase \
       --workers=0 --stop-after-init
```
