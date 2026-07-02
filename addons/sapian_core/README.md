# sapian_core

The always-installed product base for SapianERP.

## Provides
- `sapian.module.catalog` — per-company registry of product modules with on/off toggles
  (the no-code "add/remove modules" lever; see docs/06_CUSTOMIZATION_GUIDE.md, Layer 1).
- `res.company` extensions — `sapian_enabled`, `sapian_default_lang` (Ethiopian/branding hooks).

## Depends
`base`, `web`.

## Security
Catalog is read-only for internal users; write/create/unlink restricted to system admins.

## Next (per build spec S1-1/S1-2)
- Onboarding wizard that reads the catalog and installs the chosen Odoo modules.
- Branding/theme settings (Layer 2).
