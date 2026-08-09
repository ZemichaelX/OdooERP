# sapian_sentry

Error monitoring for SapianERP via Sentry.

## What it does

Initialises the Sentry SDK at server start so unhandled exceptions and
ERROR-level logs from any tenant reach Sentry instead of dying in a log file.

## How it loads

This is a **server-wide module**, not an app. It is listed in
`server_wide_modules` in `odoo.conf` so it initialises before any database and
catches start-up failures too. It is never installed per database.

## Configuration

All settings come from the environment, never from committed files:

| Variable | Purpose |
|---|---|
| `SENTRY_DSN` | Sentry project DSN. **If unset, this module does nothing at all.** |
| `SENTRY_ENVIRONMENT` | `dev`, `staging`, or the client name in production |
| `SENTRY_RELEASE` | Optional. Git SHA or version tag. |

## Deliberate choices

- **Dormant without a DSN.** Monitoring must never be able to stop a tenant
  from starting.
- **Business exceptions are dropped** in `before_send`: `UserError`,
  `ValidationError`, `AccessError`, `AccessDenied`, `MissingError`,
  `RedirectWarning`, `CacheMiss`, `NotFound`. These are normal application
  behaviour, not defects; without the filter Sentry fills with correct
  behaviour within a day and stops being read.
- **`send_default_pii=False`** and tracing disabled. Client payroll and tax
  figures must not leave their instance inside an error payload.