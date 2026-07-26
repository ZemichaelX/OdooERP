# SapianERP — Docker deployment

Each client runs an isolated Dockerized Odoo 19 instance (see `CLAUDE.md`).

- `docker-compose.yml` — Postgres 16 + Odoo (custom addons mounted read-only).
- `Dockerfile` — Odoo 19 image + the Ethiopic font for Amharic PDF reports.
- `docker/.env` — `DB_PASSWORD` etc. **Never commit** (git-ignored). It must
  live HERE, not at the repo root: compose is invoked with
  `-f docker/docker-compose.yml`, so its project directory — where it reads
  `.env` for `${DB_PASSWORD}` interpolation — is `docker/`.
- `config/odoo.runtime.conf` — the odoo.conf that compose actually mounts.
  Git-ignored because it carries per-tenant secrets; `config/odoo.conf` is
  only the clean, tracked template.

## Local development / deploy steps

```bash
# from the repo root
cp .env.example docker/.env                    # 1. set DB_PASSWORD
cp config/odoo.conf config/odoo.runtime.conf   # 2. runtime config (see below)
docker compose -f docker/docker-compose.yml up -d
# http://localhost:8069
```

Step 2 can be skipped when provisioning a tenant: `scripts/provision_client.sh`
creates `config/odoo.runtime.conf` from the template if it is missing, then
generates a strong per-tenant `admin_passwd` into it (printed once — vault it).
Secrets never touch the tracked `config/odoo.conf`; `git status` stays clean
across a provision run.

## Production hardening — reverse proxy + TLS (deferred to the go-live runbook)

> **A8 (audit finding A8): do this before exposing an instance to the internet.**

`config/odoo.conf` ships `proxy_mode = True`. That setting tells Odoo to trust
`X-Forwarded-*` headers — which is correct **only** when a trusted reverse proxy
terminates TLS in front of Odoo and sets those headers. The bundled
`docker-compose.yml` publishes port `8069` directly for local development, which
means, as shipped, there is **no HTTPS and no trusted proxy**. Do not expose that
port to the internet.

For any internet-facing deployment:

1. Put **nginx** (or Traefik/Caddy) in front of Odoo, terminating TLS
   (Let's Encrypt), and proxy to the `odoo` service on `8069`.
2. Stop publishing `8069` on the host — bind Odoo to the proxy's Docker network
   only (drop the `ports:` mapping, or bind to `127.0.0.1:8069`).
3. Have the proxy set `X-Forwarded-For`, `X-Forwarded-Proto` and
   `X-Forwarded-Host`; keep `proxy_mode = True` so Odoo honours them **only**
   from that trusted hop.
4. Confirm `list_db = False` stays set (it is, in `config/odoo.conf`) and that
   `provision_client.sh` has written a strong per-tenant `admin_passwd`
   (see audit finding A10).

A reference `nginx` service + TLS config belongs in the deployment runbook and
is intentionally out of scope for this repo's dev compose file.
