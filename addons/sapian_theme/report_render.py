# -*- coding: utf-8 -*-
"""Report rendering that cannot silently produce an unstyled document.

THE FAULT THIS EXISTS TO PREVENT
--------------------------------
Odoo renders a PDF by handing wkhtmltopdf an HTML document containing

    <link rel="stylesheet" href="/web/assets/<hash>/web.report_assets_common...css"/>

wkhtmltopdf fetches that over HTTP, from ``web.base.url``. **If it cannot, it
says nothing and renders the document unstyled.** Exit code 0, a valid PDF,
plausible byte count — and every report layout looks identical, because what
distinguishes them is Bootstrap grid classes that need the stylesheet to mean
anything.

That is exactly what happened here: report checks were run inside
``docker compose run --rm odoo`` throwaway containers, where ``localhost:8069``
is the empty container rather than the live service. Three separate
verification attempts — byte length, then SHA, then rasterised pixels — all
agreed the layouts were identical, and all three were measuring documents
rendered with no CSS at all. The conclusion "the layouts do not differ" was
wrong, and nothing in the render path objected.

So: a PDF rendered outside a live server is not the PDF a client gets. This
module turns that from a fact somebody has to remember into an error somebody
cannot miss.

USE
---
    from odoo.addons.sapian_theme.report_render import render_pdf_checked
    pdf = render_pdf_checked(env, "account.report_invoice", invoice.ids)

or, to assert the precondition without rendering::

    from odoo.addons.sapian_theme.report_render import assert_report_assets_reachable
    assert_report_assets_reachable(env)
"""

import logging
import re
import urllib.error
import urllib.request

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10

# Long enough to be unmistakable in a CI log. Whoever reads this is looking at
# a confusing result and needs the cause, not a stack trace.
_UNREACHABLE = (
    "sapian_theme: the report stylesheet is NOT reachable from this process, so "
    "any PDF rendered here would be silently UNSTYLED and would not match what a "
    "client receives.\n"
    "  web.base.url : %s\n"
    "  tried        : %s\n"
    "  failure      : %s\n"
    "wkhtmltopdf fetches the stylesheet over HTTP from web.base.url and does not "
    "complain when it 404s or the host refuses the connection — it just renders a "
    "document with no CSS, exits 0, and produces a plausible-looking PDF in which "
    "every report layout is identical.\n"
    "Most common cause: rendering inside `docker compose run --rm odoo` or "
    "`odoo shell --no-http`, where localhost:<port> is a container with no server. "
    "Render from inside the LIVE container instead:\n"
    "  docker compose -f docker/docker-compose.yml exec -T odoo odoo shell -d <db> \\\n"
    "    --db_host=db --db_port=5432 --db_user=odoo --db_password=<pw>\n"
    "or point web.base.url at a host this process can actually reach."
)


class ReportAssetsUnreachable(RuntimeError):
    """The report stylesheet cannot be fetched from this render context."""


def _base_url(env):
    return (env["ir.config_parameter"].sudo().get_param("web.base.url") or "").rstrip("/")


def _stylesheet_urls(env, report_name, res_ids):
    """The stylesheet hrefs the rendered document actually links.

    Taken from the real rendered HTML rather than guessed, so this checks the
    URL wkhtmltopdf will genuinely request — including the asset hash, which
    changes whenever the bundle is recompiled.
    """
    html = env["ir.actions.report"]._render_qweb_html(report_name, res_ids)[0]
    if isinstance(html, bytes):
        html = html.decode("utf-8", "ignore")
    return re.findall(r'<link[^>]+href="([^"]+\.css[^"]*)"', html)


def assert_report_assets_reachable(
    env, report_name=None, res_ids=None, timeout=DEFAULT_TIMEOUT
):
    """Raise ``ReportAssetsUnreachable`` unless the report CSS can be fetched.

    Checks the thing that actually matters — an HTTP GET from *this* process to
    the stylesheet URL — rather than a proxy for it such as "is a port open" or
    "does the bundle exist in the database". The bundle existing in the database
    is precisely what misled the original investigation: the CSS was present and
    correct, and the renderer still could not reach it.

    ``report_name``/``res_ids`` are optional. Given them, the exact stylesheet
    links of that document are verified. Without them, only ``web.base.url``
    itself is probed, which catches the common "no server here at all" case.
    """
    base = _base_url(env)
    if not base:
        raise ReportAssetsUnreachable(
            _UNREACHABLE % ("<not set>", "n/a", "web.base.url is empty")
        )

    targets = []
    if report_name and res_ids:
        for href in _stylesheet_urls(env, report_name, res_ids):
            targets.append(href if href.startswith("http") else base + href)
    if not targets:
        # /web/health: 200 and auth-free, so a failure here means the host is
        # genuinely unreachable rather than that we lack a session.
        targets = [base + "/web/health"]

    for url in targets:
        is_stylesheet = ".css" in url
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                status = getattr(response, "status", response.getcode())
                length = len(response.read())
        except urllib.error.HTTPError as exc:
            # A status code means a server ANSWERED. For the liveness probe that
            # is all we need to know — the fault being guarded against is
            # "nothing is listening", not "this endpoint wants a session".
            # For the stylesheet itself a bad status is fatal: that is the file
            # wkhtmltopdf needs and will not get.
            if not is_stylesheet:
                continue
            raise ReportAssetsUnreachable(
                _UNREACHABLE % (base, url, "HTTP %s" % exc.code)
            ) from exc
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise ReportAssetsUnreachable(_UNREACHABLE % (base, url, exc)) from exc
        if is_stylesheet and status >= 400:
            raise ReportAssetsUnreachable(_UNREACHABLE % (base, url, "HTTP %s" % status))
        # A stylesheet that resolves to nothing styles nothing. Assert the size,
        # not merely the absence of an error — an empty 200 is the silent case.
        if is_stylesheet and length < 1024:
            raise ReportAssetsUnreachable(
                _UNREACHABLE % (base, url, "served only %d bytes of CSS" % length)
            )
    _logger.info(
        "sapian_theme: report assets reachable from this process (%d URL(s) verified via %s)",
        len(targets),
        base,
    )
    return True


def render_pdf_checked(env, report_name, res_ids, timeout=DEFAULT_TIMEOUT):
    """Render a PDF, refusing to produce one that would be silently unstyled.

    Use this anywhere a report is rendered for VERIFICATION. It is deliberately
    not wired into Odoo's own rendering path: a live user printing an invoice
    should not have their document blocked by a transient network probe. The
    hole this closes is in how we CHECK reports, which is where it bit us.
    """
    assert_report_assets_reachable(env, report_name, res_ids, timeout=timeout)
    pdf, _ext = env["ir.actions.report"]._render_qweb_pdf(report_name, res_ids)
    return pdf
