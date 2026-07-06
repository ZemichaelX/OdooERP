# -*- coding: utf-8 -*-
"""A1: move PAYE bands + pension config from install-company XML records to
per-company Python seeding.

Before this version the standard bands/pension config shipped as XML
``<record>``s whose ``company_id`` defaulted to whichever company was active at
module install — so every OTHER company (a second company in a group, a
provisioned demo tenant, a SaaS tenant) silently fell back to hard-coded rate
constants in the compute helper.

The records are now seeded per company from ``et_payroll_calc`` on install and
every upgrade. Here we DETACH the old xmlid-bound rows from the module (delete
only their ``ir.model.data`` links, not the records) so end-of-load orphan
cleanup does not delete them: the install company keeps its bands exactly as
they are (including any a client tuned), while the seed ``<function>`` fills in
every company that never had configuration. Idempotent and safe to re-run.
"""


def migrate(cr, version):
    if version is None:
        # Fresh install: no legacy xmlid records to detach.
        return
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE module = 'l10n_et_payroll'
           AND model IN ('l10n.et.paye.band', 'l10n.et.pension.config')
        """)
