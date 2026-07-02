# 08 — Security & Compliance

Extends the DAT proposal's commitments (RBAC, 2FA, backups, hardening, GDPR-inspired privacy) into a standard product posture applied to every tenant.

## 1. Access control

- Role templates with least privilege (06 §7); no shared accounts; admin accounts named and minimal.
- **2FA mandatory** for admin/finance/HR roles; available to all users (Odoo TOTP).
- Session policy: timeout for sensitive roles; IP allowlist option for admin endpoints; portal users isolated by record rules.
- Segregation of duties presets: quote ≠ invoice validation; PO creation ≠ receipt validation ≠ payment; payroll prepare ≠ approve.
- Joiner/mover/leaver: HR departure auto-flags user deactivation (the DAT integration example — implement as standard).

## 2. Platform hardening (per node, scripted — not manual)

- HTTPS only (nginx + Let's Encrypt, HSTS); Odoo behind proxy, `proxy_mode = True`.
- `list_db = False`; master password strong + vaulted; database manager blocked at proxy.
- Firewall: only 80/443/22 (22 key-only, fail2ban); Postgres not exposed publicly.
- OS auto security updates; Docker images rebuilt monthly (patch window).
- Secrets: per-tenant credentials (SMTP, payment, SMS, EFDA) in env/vault — never in code or DB plaintext.
- Webhooks: signature verification, replay protection, rate limiting.
- Custom-code review gate: every module PR checked for injection, access bypass (`sudo()` audits), unsafe eval, data leaks in logs — part of CI checklist + `security-review` pass before release.

## 3. Backups & disaster recovery

- Per tenant: nightly DB dump + filestore snapshot; encrypted; shipped **off-node** (object storage, different provider/region); 30-day retention (longer by contract).
- **Monthly restore drill** — a backup that hasn't been restored doesn't exist. Restore runbook + measured RTO/RPO per tier (target: RPO ≤ 24h, RTO ≤ 4h standard, ≤ 1h enterprise).
- Uptime monitoring + alerting on all tenants; incident log; status communication template.

## 4. Auditability

- Odoo chatter/audit trail on critical models (stock moves, invoices, payments, payroll runs); OCA `auditlog` on high-risk models (bank accounts, salary, taxes, access rights).
- Immutable numbering for fiscal documents; posted-entry lock dates; period closing checklist.
- Auditor role: read-only everything + logs — sells well with regulated clients.

## 5. Data privacy

- Personal data inventory per module (employees, customers, portal users); access restricted by role.
- Ethiopia's Personal Data Protection Proclamation (1321/2024) awareness: consent basis for portal/marketing data, breach-response runbook, data export/deletion capability per subject request. ⚠ Verify current directives during implementation.
- Data residency option: local hosting or client-owned cloud for clients who require in-country data.

## 6. Sector compliance hooks

- Pharma: EFDA traceability + batch recall reporting (07 §8); good-distribution-practice audit trail (who moved what batch when).
- Finance: WHT/VAT/PAYE reports reconcile to GL by construction; cash-cap rule warnings (ETB 30,000).
- Tender/NGO clients: document retention settings and donor audit exports.

## 7. Client-facing security deliverables (productized trust)

Every implementation ships: security configuration summary (from the manifest), backup/DR statement with tested restore date, RBAC matrix signed by the client, and an annual security review offer in the AMC. These artifacts close enterprise deals.
