# sapian_demo_pharma — Demo Pharma Tenant (SapianERP)

Provisions **"Tena Pharma Import PLC"**, the sales-demo company for the pharma
vertical (the DAT International pitch). Everything is created through the real
warehouse flows — receipts and deliveries, no staged data.

## What the pitch can show
- **Six medicines** (Amharic + English names) flagged pharma, each with a
  realistic **730-day shelf life** — a live receive during the pitch auto-fills
  an expiry two years out, never an instantly-expired lot.
- **Batches at all three stages**: fresh import stock, Coartem `CO-88` nearing
  expiry (+45 days, inside the 90-day horizon), ORS `OR-15` expired (−10 days).
- **The expiry digest already fired**: one activity on the most urgent batch
  listing CO-88 and OR-15 — show the alert itself.
- **Import dossier** `IMP/...` from Global Pharma GmbH with landed costs
  (goods 1,850,000 + freight 210,000 + customs 396,500 + clearance 55,000 =
  **2,511,500 ETB**), linked to the main receipt: every fresh batch traces to
  its import file.
- **Recall-ready flow**: `B-123` went to Hiwot Pharmacy (120) and Kadisco
  Pharmacy (80) on different dates — exhausting the batch, so Bethel Clinic's
  order FEFO-reserved `B-124`. The B-123 recall report lists exactly two
  customers with phone + city; Bethel's absence proves precision by exclusion.

## Notes
- Idempotent by company name; expiry-sensitive dates are relative to the
  provisioning day, so states hold whenever the tenant is rebuilt.
- Demo/sales-demo use only — never install on a client database.
