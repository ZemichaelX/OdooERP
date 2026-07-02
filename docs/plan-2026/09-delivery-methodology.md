# 09 — Delivery Methodology (the client playbook)

Standardizes what the DAT proposal promised (phase-gated UAT, per-phase training, milestone billing) and adds the failure-prevention practices from research (change management, paid data cleanup, scope control).

## Stage 0 — Sell (days, not weeks)

1. Prospect sees vertical demo tenant (already-branded, Ethiopian sample data).
2. Package picker → auto-generated proposal from the module catalog (reuse the DAT proposal structure: exec summary, client overview, module details, timeline, fixed pricing, security, support plan, next steps — it's a proven document).
3. Contract + NDA; **30% down payment** mobilizes; milestone-billed remainder tied to phase sign-offs.

## Stage 1 — Discover (week 1)

- Kickoff: stakeholders, roles, communication cadence (weekly), success criteria.
- Per-department process mapping against the standard product; every gap classified on the decision ladder (standardize/configure/extend/customize).
- Output: **Configuration Workbook** (becomes the client manifest) + final module list + data-migration inventory + named client super-users per department. Signed.

## Stage 2 — Configure & migrate (weeks 2–4 typical)

- Provision staging tenant from manifest (`provision_client.sh`) — same day.
- Apply branding, roles, policies; build any approved thin extensions.
- **Data workstream (paid, mandatory):** client cleans data in our CSV templates → validation scripts report issues → rehearsal import → review → final import at cutover. (38% of ERP failures are migration-related; this is why it's not optional.)
- Phase order per client urgency — default: Inventory → Sales/CRM → Purchase → Accounting → HR/Payroll → Website/Portal (the DAT lesson: inventory first for traders; payroll first for services firms).

## Stage 3 — Validate (per phase)

- We run functional tests; client super-users run **UAT with our provided scripts**; issues logged/triaged/fixed.
- **UAT sign-off gates the next phase and its invoice.** Test evidence archived (auditable delivery).

## Stage 4 — Train & adopt (change management — 42% of failures happen here)

- Role-based training (not generic demos): warehouse track, finance track, HR track, executive dashboard track; Amharic where needed.
- Super-user program: 1–2 per department trained deeper; they become first-line support and internal champions.
- Generated quick-reference guides + the auto-generated admin manual (from the manifest).
- Training tenant stays available; go-live readiness checklist includes adoption criteria (e.g., every warehouse user has completed 10 real transactions in staging).

## Stage 5 — Go live (1 week)

- End-to-end day-in-the-life test across all modules (DAT promise — keep it).
- Final data cutover; hypercare: daily check-ins for 2 weeks; on-site presence on day 1–2.
- Load test at production sizing; backup + monitoring verified; security deliverables handed over (08 §7).
- Formal acceptance → final invoice → transition to support.

## Stage 6 — Support & grow (recurring)

- AMC tiers (baseline from DAT: 20k ETB/mo, 2 named engineers, SLA: critical immediate / major 1 business day / minor 1–2 days).
- Patch cadence monthly; version upgrade yearly (rehearsed on a staging clone first).
- Quarterly business review: usage stats, new-module recommendations (catalog upsell), tax-law updates applied.
- Change orders via manifest diffs — priced from a standard rate card.

## Standard timeline templates

| Package | Typical duration |
|---|---|
| Payroll+HR standalone | 2 weeks |
| Essential | 3 weeks |
| Business | 6–8 weeks (DAT-class scope was quoted 14 weeks bespoke; productization compresses it) |
| Enterprise + vertical | 10–14 weeks |

## Scope control (the anti-failure system)

- Everything in the signed Configuration Workbook is in scope; anything else is a change order — no exceptions, communicated kindly and early.
- Weekly status includes a scope-watch section; risks raised immediately (DAT proposal promise).
- Internal rule: if custom-code requests exceed ~15% of project effort, escalate to re-scoping conversation — over-customization is the #1 long-term cost driver.
