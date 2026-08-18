# -*- coding: utf-8 -*-
"""Fill core ``vat`` from ``l10n_et_tin`` on databases that already exist.

New and edited partners are synced by ``res.partner.create``/``write``; neither
reaches a partner that was created before this version. Without this, an existing
tenant keeps sending invoices with no tax identifier on them while the upgrade
reports success — the same install-versus-upgrade trap as the expense-account
default, and the reason that one needed a migration too.

The country label (``res.country`` ET → ``vat_label = TIN``) is applied here too,
and it CANNOT be a data record: ``ir_model_data`` for ``base.et`` is
``noupdate = true``, so an XML record targeting it is skipped in silence — the
file loads, nothing is written, and no error is raised.

Idempotent, and conservative: ``_l10n_et_backfill_vat_from_tin`` moves only
partners whose ``vat`` is empty, so an identifier somebody typed is never
overwritten.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if version is None:
        # Fresh install: create/write sync as records are made.
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.country"]._l10n_et_ensure_vat_label()
    moved = env["res.partner"]._l10n_et_backfill_vat_from_tin()
    if moved:
        env["ir.logging"].sudo().create(
            {
                "name": "l10n_et_base",
                "type": "server",
                "dbname": cr.dbname,
                "level": "INFO",
                "message": "Filled core `vat` from the Ethiopian TIN on %d partner(s); "
                "their documents now print a tax identifier." % len(moved),
                "path": "l10n_et_base/migrations/19.0.1.6.0",
                "func": "migrate",
                "line": "0",
            }
        )
