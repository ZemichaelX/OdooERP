# 02 — Market Research: How ERP Firms Win + The Ethiopian Context

> Researched July 2026. Figures marked ⚠ should be re-verified against gazetted text before go-live.

## Part A — How successful ERP/Odoo firms stand out

### A1. Vertical specialization beats generalism
- Buyer guides now treat "generalist partner" as a red flag; a smaller partner deep in one industry outsells bigger generalists.
- Odoo itself is moving this way: Odoo 19 ships industry templates; Odoo 20 (2026) ships vertical apps. Partners increasingly compete on *industry configuration knowledge*, not raw Odoo skills.
- **Implication:** lead with 1–2 verticals. Pharma/medical distribution is the obvious first (DAT blueprint exists); import/trading and retail/distribution second.

### A2. Fixed-scope, rapid-deployment packages
- QuickStart-style packages (fixed modules, fixed price, 2–4 week go-live) are the dominant productized model; speed itself is marketed (e.g., a construction-tech client live in 2 weeks).
- Pricing spread is wild — one 120-employee firm got $14k/$38k/$72k quotes for the same scope. Structured discovery, documented requirements, formal testing, and signed-off plans are what justify premium pricing.
- Typical component pricing seen: $2k–10k per custom module, $2k–8k per integration, $2k–20k for data migration.

### A3. Demo-led selling
- Winning pattern: spin up a **pre-configured industry demo instance with realistic sample data before the first sales meeting**. Platforms (OEC.sh etc.) productize "deploy demo → win → implement → hand off."
- **Implication:** maintain a permanent pharma-distribution demo tenant (Amharic names, ETB, batch/expiry data) reachable in one click.

### A4. Recurring revenue stack (where the real money is)
| Layer | Economics |
|---|---|
| Implementation fee | One-off, per module/integration/migration |
| **Hosting margin** | Wholesale $10–100/client/mo → retail $50–500/mo; **70–85% gross margin**; published cases: 15 clients ≈ $1,800/mo, 50 clients ≈ $14,500/mo net |
| AMC / support retainer | Tiered SLA packages: monitoring, custom-module maintenance, helpdesk, backups |
| Own modules | Odoo Apps Store pays 70% to developers; module library doubles as pre-sales proof |
| License resale | Gold partners earn ~20% on Enterprise subscriptions (only if you ever sell Enterprise) |

### A5. Why ERP projects fail (and what top firms do)
- 2025 stats: 42% of failures from inadequate change management, 38% poor data migration, 35% inexperienced teams; only 49% go live on schedule; 64% overrun budget. Failures are human/strategic, not technical.
- Countermeasures used by top firms:
  1. Fixed signed-off scope + formal change control (scope creep is overrun driver #2 at 35%).
  2. **Paid, mandatory data-cleanup workstream** before migration — dirty data destroys user trust on day one.
  3. Change management as a core workstream: training environments, super-user programs, phased go-lives.
  4. **Anti-over-customization discipline:** 70–85% of needs met by standard config. Decision ladder: *standardize → configure → extend modularly → custom code only for high-value recurring needs*. Every custom line is an annual upgrade tax (Odoo majors yearly).
  5. Retention operations (QBRs, proactive monitoring) — Odoo's partner tiers require ~80% retention.

### A6. White-labeling & multi-client operations are solved problems
- Debranding/rebranding modules exist off-the-shelf (Webkul Backend Debranding, Softhealer All-in-One, "Odoo White Label"): strip Odoo logos, rename OdooBot, rebrand emails/favicons/login. Trivial cost.
- Standard multi-client pattern: **shared infrastructure, one isolated database per tenant**, central fleet management (bulk updates, impersonation support, per-client backups). "You manage, they own" (per-client cloud account) is a clean exit/compliance story for bigger clients.
- **Odoo.sh vs self-hosted:** Odoo.sh = Git CI/CD + staging but Enterprise-only, ~$72/worker/mo, no root. Self-hosted = Community allowed, full OCA catalog, any region, ~$50/mo total — the margin play for multi-client firms. Verdict: **self-host**.
- **Upgrades:** Community relies on OCA **OpenUpgrade** (v19 path being crowdfunded). Best practice: stable field names/external IDs, migration scripts, minimal custom code, reuse/contribute OCA.

### A7. Odoo platform state (mid-2026)
- **Odoo 19 shipped Sept 2025**; Odoo 20 expected 2026 with vertical apps. Odoo 18 is the safe stable base today; plan an 18→19 path via OpenUpgrade.
- **Community vs Enterprise gap widening.** Enterprise-only: full accounting suite (dynamic reports, bank sync, OCR), payroll, helpdesk, Studio, official mobile app, and all v19 AI features. Community + **OCA (1000+ modules)** remains the classic emerging-market stack — but payroll and local compliance require custom/OCA localization work. **That gap is exactly your product.**

### A8. AI-assisted delivery
- Firms explicitly run AI-first Odoo development (Copilot/Claude/Gemini generating models, ORM methods, views), reporting materially lower cost and faster delivery; Odoo Experience 2025 had a dedicated AI-in-development track.
- Value migrates to discovery, process design, change management, vertical domain expertise. **Your Claude Code workflow is a structural cost advantage over Addis incumbents — price aggressively, deliver faster, keep margin.**

## Part B — Ethiopian regulatory & market facts (the localization spec inputs)

### B1. PAYE — Income Tax (Amendment) Proclamation No. 1395/2025 ✅ verified
Effective 1 July 2025 (FY 2025/26). Monthly brackets:

| Monthly income (ETB) | Rate |
|---|---|
| 0 – 2,000 | 0% |
| 2,001 – 4,000 | 15% |
| 4,001 – 7,000 | 20% |
| 7,001 – 10,000 | 25% |
| 10,001 – 14,000 | 30% |
| > 14,000 | 35% |

Also in 1395/2025: employees with multiple income sources must file annual returns; **cash payment cap ETB 30,000**/person/day (penalty 2× the cash amount); **Minimum Alternative Tax 2.5% of turnover**; digital-services income up to 5%; taxpayer categories reduced to A & B (Category A ≥ ETB 2M turnover); **Turnover Tax (TOT) abolished**.

### B2. VAT — Proclamation 1341/2024 + Regulation 570/2025 ✅ verified
Standard rate **15%**; zero-rating retained; registration threshold **ETB 2M**/12mo (related parties aggregated); **monthly filing**; mandatory tax invoices/credit/debit notes; non-resident digital services & marketplace rules.

### B3. Withholding tax — from Aug 2025 ✅ verified (⚠ confirm thresholds vs gazette)
**3%** withheld on goods > **ETB 20,000** and services > **ETB 10,000** per transaction/contract; remit within 30 days; **30% punitive WHT if supplier lacks TIN + business licence**; 15% WHT on foreign digital service providers. (Old 2% / 10,000 / 3,000 rule obsolete.)

### B4. Pension — Proclamation 1268/2022 ✅ verified
Private organizations: **employee 7%, employer 11%** of basic salary; applies from 45 days of employment; remit within 30 days of month-end via MoR.

### B5. Excise ✅ verified
Proclamation 1186/2020 (amended 1287/2023): ~378 goods, 5%–500%, base = ex-factory price; specific rates adjusted annually by directive.

### B6. E-invoicing & fiscal receipts
- INSA-built **Electronic Invoice Management System** for MoR launched Oct 2024; e-invoicing rolls out through **ITAS**. ⚠ Mandatory phase-in dates per taxpayer segment unconfirmed — track MoR directives.
- **Directive 188/2024:** from 9 Feb 2025, manual receipts without **QR codes** are invalid for deduction/refund; only Berhanena Selam Printing may print them.
- Legacy fiscal-device regime (certified sales register machines / fiscal printers) still in force for POS. ERP POS must integrate a certified fiscal device or the e-invoice/QR flow.

### B7. Labor law — Proclamation 1156/2019 ✅ verified
- Probation: max **60 working days**. Standard week **48h**.
- Annual leave: **16 working days** first year, **+1 day per additional 2 years** of service.
- Overtime: **1.5×** day, **1.75×** night (22:00–06:00), **2×** weekly rest day, **2.5×** public holiday.
- Severance: 30× average daily wage for first year + ⅓ of that per additional year, capped at 12 months' wages.

### B8. Other compliance surfaces
- **EFDA (pharma):** eRIS/i-Register; import requires certificate of competence, product registration, PO approval, port clearance. **GS1 traceability mandate**: 2D DataMatrix (GTIN + serial + batch + expiry) on all pharma items; data exchange with EFDA via web GUI, XML, or **API** — a real ERP integration surface.
- **Customs:** electronic Single Window (eSW) for declarations. ⚠ Data formats for integration unverified.
- **IFRS:** mandated by Proclamation 847/2014 (AABE); full IFRS for public-interest entities, **IFRS for SMEs** for others; real-world adoption lagging — ERP should ship IFRS-compliant CoA and statements.

### B9. Payments & messaging (developer reality)
| Service | Status |
|---|---|
| **Telebirr** | Documented at developer.ethiotelecom.et — H5/web payment, in-app SDK, SuperApp mini-app, USSD/C2B; merchant account required |
| **M-PESA Ethiopia** | developer.safaricom.et — Daraja-style APIs (STK push, C2B, B2C) |
| **Chapa** | Licensed PSO; most developer-friendly aggregator — REST, hosted checkout, webhooks |
| **ArifPay** | Licensed; APIs + physical POS |
| **SantimPay** | Licensed; merchant APIs |
| **CBE Birr** | ⚠ No public developer portal — integrate via aggregators |
| **Ethio Telecom SMS API** | Offered on same developer portal; ⚠ documentation depth unverified |

NBE QR-payment standardization mandate effective Feb 2025.

### B10. Calendar & language
- **OCA/l10n-ethiopia** exists but thin: `l10n_et_base` (Amharic names), `ethiopic_calendar` (pycalcal-based). **No complete Ethiopian fiscal localization exists in Odoo core or OCA** — your moat.
- Andegna (PHP) + multiple JS/Python Ethiopian-calendar libraries available as references.
- Amharic Odoo core translation is partial/crowdsourced.

### B11. Competitive landscape (Ethiopia)
- ~14 certified Odoo partners; named: **ETTA Solutions** (Silver), **Atheer IT** (claims Gold), **Macrofix**, **AditeKit** — Addis-centric, opaque pricing, generalist positioning.
- ERPNext side appears underserved (weak signal).
- **Gaps = opportunities:** complete PAYE 1395/2025 engine, 3% WHT automation, QR/ITAS e-invoice integration, pension filing exports, Ethiopian-calendar-native reporting, EFDA GS1 traceability integration, Amharic-first UX, published transparent pricing.

## Sources
Differentiation/business models: silentinfotech.com (Odoo partner pricing 2026), braincuber.com, pixelmechanics.tech (Odoo 20 verticals), itransition.com (cost components), oec.sh (agency hosting economics, multi-tenant, odoo.sh comparison), godlan.com + elevatiq.com + prosci.com (failure stats), odoo.com/page/editions, moonsun.au + cudio.com (19 Community vs Enterprise), github.com/OCA/OpenUpgrade, webkul.com + softhealer.com (debranding), portcities.net + integscloud.com (AMC/SLA), medium.com/@saniscayacorp + workik.com (AI-assisted Odoo dev), odoo.com/event (AI track).
Ethiopia: taxdev.org + myworkpay.com + payspace.com + chambers.com + ey.com (PAYE 1395/2025), birrmetrics.com (WHT, QR mandate), haymanotbelay.com + hulunem.com (VAT 1341/2024), dmethiolawyers.com + taxsummaries.pwc.com (pension), insa.gov.et + thereporterethiopia.com (e-invoice/ITAS), efda.gov.et + lspedia.com (EFDA GS1), ifrs.org (IFRS status), mywage.org + abyssinialaw.com + mols.gov.et (labor 1156/2019), developer.ethiotelecom.et, developer.safaricom.et, nbe.gov.et, chapa.co, arifpay.net, santimpay.com, github.com/OCA/l10n-ethiopia, andegna.github.io, odoo.com/partners (Ethiopia list).
