# SapianERP — Docker deployment

Each client runs an isolated Dockerized Odoo 19 instance (see `CLAUDE.md`).

- `docker-compose.yml` — Postgres 16 + Odoo (custom addons mounted read-only).
- `Dockerfile` — Odoo 19 image + the Ethiopic font for Amharic PDF reports.
- `.env` — `DB_PASSWORD` etc. **Never commit** (git-ignored).

## Local development

```bash
cp .env.example .env          # set DB_PASSWORD
docker compose -f docker/docker-compose.yml up -d
# http://localhost:8069
```

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
