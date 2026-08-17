# SapianERP — product readiness assessment

**What this document is:** coverage, not defects. It asks what a small Ethiopian
trading company actually does, walks those flows end to end on a live database,
and records what happened. `docs/defect-register.md` remains the register of
defects; this file cross-references it by entry number and, at the end, lists the
new register entries this assessment owes.

**No fixes were made.** Where a fix was obvious it was written down instead.

Started: 17 August 2026.

---

## Where this was measured, and where it was not

This matters more than usual here, because defect register rule 5 —
*the environment that verifies is not always the environment that runs* — has
fired five times on this project, and its corollary is *a substitute for the
thing asked about is not a measurement of it.*

**Measured on:** a database called `scratch_readiness`, built from nothing inside
this session's own container on 17 Aug 2026.

**NOT measured on:** Zemichael's `demo_allapps`, `sapian_prod`, or any client
database. Nothing in this assessment touched them. Where a finding depends on
tenant state rather than on code, it is marked as such and is **not** evidence
about any tenant.

### How the container was built, since it is not the documented stack

The documented stack is Docker (`docker/docker-compose.yml`). **There is no
Docker daemon in this container**, so the stack could not be used and the
database was built natively instead. Recorded because it is a difference between
the environment that verified and the environment that runs:

| | Documented stack | This assessment |
|---|---|---|
| Odoo | image `odoo:19.0@sha256:e415f99…` | source clone `odoo/odoo` branch `19.0`, commit `ccce9fcc` (2026-06-29) |
| Postgres | image `postgres:16@sha256:33f923b…` | Ubuntu `postgresql-16` 16.13, local cluster |
| Python deps | image's own | `requirements.txt` into a venv, **two substitutions**: `psycopg2` → `psycopg2-binary`, and `python-ldap` omitted (build deps absent; no LDAP module is installed) |
| PDF engine | image's patched wkhtmltopdf | Ubuntu `wkhtmltopdf 0.12.6`, **unpatched Qt** — PDFs render, headers/footers are not the patched-build layout |
| Ethiopic font | `fonts-sil-abyssinica` in the image | **not installed** — so Amharic glyph rendering in PDFs is UNTESTED here and no claim is made about it either way |

The build followed `scripts/build_demo.sh`'s phase order, which is load-bearing
(country before chart, provisioning strictly after install):

1. `-i base --without-demo=all` → 14 modules.
2. company country set to `ET` before any chart loaded.
3. `-i sapian_demo_trader,sapian_theme,web_responsive --without-demo=all` → **84 modules**.
4. `sapian.demo.trader._provision_demo_tenant(adopt_existing=True)` →
   `>> provisioned: Selam General Trading PLC | chart: et | country: ET`, and
   launcher defaults applied to 2 users.

**84 modules, not 229.** The 229-module database is `--all-apps`, the navigation
-scale build. This assessment is deliberately run on the **shipped default set**,
because that is what a first client gets, and because a sweep across 229 modules
produces hundreds of findings that are all stock Odoo's. Tier 3 lists what is
therefore absent.

Scripts were run through a purpose-built runner (`/workspace/rt/run.py`) rather
than `odoo shell < file`, because `odoo shell` reading a pipe behaves like an
interactive console: a traceback on one line does not stop the next, so a phase
can half-execute in silence. The runner raises, rolls back and exits non-zero.

### The tenant as provisioned, before any flow ran

| | |
|---|---|
| Company | Selam General Trading PLC, id 1, ETB, chart `et`, fiscal year ends 7 July |
| Company TIN (`vat`) | **not set** — see flow (c) and (d) |
| Our modules | `l10n_et`, `l10n_et_base`, `l10n_et_payroll`, `l10n_et_reports`, `sapian_core`, `sapian_demo_trader`, `sapian_theme`, `sapian_theme_auth_signup`, `sapian_theme_mail` |
| Journals | INV, BILL, BNK1, MISC, CABA, EXCH, **PAY**, STJ |
| Sale taxes | 15%, 0%, 0% EXEMPT, 0% Out, 15% WH, **3% WHT (Withheld by Customer)** |
| Purchase taxes | 15%, 0%, 0% EXEMPT, 0% Out, **3% WHT (Goods)**, **3% WHT (Services)**, **30% WHT (No TIN/Licence)**, 15% WHT (Foreign Digital), 3% Social Welfare Levy (Imports) |
| Opening documents | 2 posted customer invoices, 3 posted vendor bills, 1 posted payroll entry |
| Employees | 6 + Administrator |
| Users | **1** (`admin`) |

---

## Severity scale

Judged for a **first client going live**, not in the abstract.

- **BLOCKER** — the client cannot operate or cannot file. Go-live stops.
- **SERIOUS** — the client can operate, but someone is doing manual work every
  month, or a number is wrong in a way an accountant would catch.
- **COSMETIC** — visible, embarrassing, harmless.
- **NOT NEEDED YET** — real, but not for the first client.

Attribution is one of: **STOCK ODOO** / **OUR CODE** / **CONFIGURATION** /
**DEMO DATA**.

---

## Tier 1 — a client cannot go live without these

_In progress. Flows are appended as they are run._
