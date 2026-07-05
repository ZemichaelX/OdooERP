# vertical_pharma — Pharma Vertical (SapianERP)

Pharmaceutical distribution compliance, generalized from the DAT International
proposal (docs/01-proposal-extraction.md §8.1 — the client's own requirements).
Session 1 delivers the compliance core, import dossiers and the recall report;
EFDA export remains a stub pending official specs.

## What it does (session 1)
- **Batch discipline**: flagging a product `is_pharma` forces lot tracking +
  expiration dates and moves it onto the FEFO "Pharmaceuticals" category —
  earliest-expiry stock always leaves first. Receipts without an expiration
  date on a pharma batch cannot validate.
- **Expiry alerts**: per-company horizon (default 90 days = the proposal's
  "3 months"); lots escalate fresh → nearing expiry → expired (states computed
  live via `reference/pharma_calc.py`); a daily cron posts ONE digest activity
  per company, anchored on the most urgent batch (assigned to an inventory
  manager, e-mail per their notification settings), listing every batch
  entering the horizon — each batch reported exactly once.
- **Expired-lot delivery policy**: block (default) or warn+audit-log,
  per company.
- **GS1 DataMatrix capture**: scan field on receipt lines parses AIs
  01 (GTIN) / 17 (expiry, day-00 = month end) / 10 (batch) / 21 (serial) and
  fills the lot + expiry; mis-scans warn loudly. Parser lives in
  `reference/pharma_calc.py` with golden tests in `tests_fast/`.
- **Import shipment dossiers** (`IMP/...`): supplier, ETA, clearance paperwork
  (chatter attachments) and landed costs, linked to receipts — every batch
  traces back to its import file (Inventory ▸ Import Dossiers).
- **Batch recall report** (button on the lot, branded `web.external_layout`):
  every customer delivery of the batch with date, quantity AND the customer's
  phone + city — a recall report's purpose is calling people. Import-dossier
  traceability is printed on it.

## Documented conventions
- 'Nearing expiry' starts exactly `expiry − horizon` (inclusive): 2026-09-25
  with 90 days → alerts from 2026-06-27.
- The expiry date is the last usable day; 'expired' starts the day after.
- Serial numbers (AI 21) are parsed but not persisted in v1 (lot = batch).

## Pending EFDA specifications
The EFDA traceability EXPORT (API/XML per the eRIS mandate) is deliberately a
stub until EFDA publishes/confirms transport specs — the GS1 capture side is
ready, so batches are traceable from day one and the export becomes an
adapter, not a rework.

## Session 2 (planned)
Medicine-request portal, delivery run management, partner directory, SMS
notifications, EFDA live API — deliberately skipped in session 1.

## Demo tenant
`sapian_demo_pharma` provisions "Tena Pharma Import PLC" with six medicines,
batches at all three expiry stages, a fired digest, one import dossier and the
recall-ready B-123 flow.
