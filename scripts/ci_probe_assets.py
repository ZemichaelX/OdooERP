# -*- coding: utf-8 -*-
"""Does the launcher exist in the ASSET PIPELINE, independent of any HTTP fetch?

Read by `odoo shell`. Diagnostic only — it asserts nothing and is not part of
the shipped verification path.

`scripts/lib/check_launcher.py` measures what the BROWSER is served, which is
the right standard for a shipping check and the wrong instrument for telling
two defects apart:

  * the assets are genuinely absent from this database's bundle, or
  * the assets are present and the verifier's fetch never reached the backend
    page (so the zero it reports describes the fetch, not the database).

Both produce `launcher_backend_js_bundles=0`. This file answers the first
question on its own, by asking `ir.qweb` for the bundle contents directly —
no session, no request, no page. A PROBE line showing web_responsive files in
`web.assets_web` while check_launcher reports zero bundles means the fetch is
the defect; a PROBE line showing zero files means the pipeline is.
"""

IrQweb = env["ir.qweb"].sudo()
IrAsset = env["ir.asset"].sudo()

installed = env["ir.module.module"].search([("state", "=", "installed")]).mapped("name")
print("PROBE modules_installed=%d" % len(installed))
for name in ("web_responsive", "sapian_theme", "website", "website_sale", "sapian_demo_trader"):
    print("PROBE module_%s=%s" % (name, name in installed))
    print("PROBE init_%s=%s" % (name, name in env.registry._init_modules))

params = IrAsset._get_asset_params()
print("PROBE asset_params=%s" % (params,))

for bundle in ("web.assets_web", "web.assets_backend", "web.assets_frontend"):
    try:
        files, external = IrQweb._get_asset_content(bundle, params)
    except Exception as exc:                              # noqa: BLE001 - diagnostic
        print("PROBE bundle_%s=ERROR %r" % (bundle, exc))
        continue
    urls = [f["url"] for f in files]
    print(
        "PROBE bundle_%s files=%d web_responsive=%d sapian_theme=%d launcher_file=%s"
        % (
            bundle,
            len(urls),
            sum(1 for u in urls if "/web_responsive/" in u),
            sum(1 for u in urls if "/sapian_theme/" in u),
            any("apps_menu/apps_menu.esm" in u for u in urls),
        )
    )

try:
    links = IrQweb._get_asset_links("web.assets_web", css=True, js=True)
    print("PROBE asset_links=%d" % len(links))
    for link in links[:8]:
        print("PROBE asset_link=%s" % (link,))
except Exception as exc:                                  # noqa: BLE001 - diagnostic
    print("PROBE asset_links=ERROR %r" % (exc,))

if "website" in env:
    site = env["website"].get_current_website(fallback=False)
    print("PROBE current_website=%s" % (site.id or "FALSE"))
    print("PROBE websites=%s" % [(w.id, w.name, w.domain) for w in env["website"].search([])])

# Did the trader tenant's data get created at all? Separate question, same run.
print("PROBE companies=%s" % [c.name for c in env["res.company"].search([])])
print("PROBE products=%d" % env["product.template"].search_count([]))
print("PROBE posted_moves=%d" % env["account.move"].search_count([("state", "=", "posted")]))
print("PROBE probe_finished=1")
