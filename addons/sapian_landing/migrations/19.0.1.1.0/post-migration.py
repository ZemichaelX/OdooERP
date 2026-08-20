# -*- coding: utf-8 -*-
"""Correct the employment income tax deadline on a tenant that already has it.

WHY A MIGRATION AND NOT AN XML EDIT. `data/filing_deadline_data.xml` is
`noupdate="1"` on purpose — an upgrade must never overwrite a rule an accountant
has corrected. That protection also means editing the XML fixes only FRESH
installs, and every tenant already carrying the 30-day employment-income-tax row
keeps it forever. Fresh installs read the XML; this reaches the rest.

WHY NOT AN EFFECTIVE-DATED SECOND ROW. Because the 30-day row was never right.
Effective-dating expresses "the law changed on this date"; adding a row from
today would leave every historical period assessed against a deadline that never
applied, and the landing page would keep absolving returns that were late. The
reference (§2) is explicit that the earlier Gregorian-flavoured answer is
"**wrong**", not superseded.

WHAT IT WILL NOT TOUCH. Only a row that still holds exactly the seeded value —
30 days, the `days` shape. A row somebody has already edited is somebody's
answer, and this is not the place to overrule it; it is reported instead.

CLAUDE.md, "a success signal that can be produced by doing nothing": this logs
the count it changed AND the count it deliberately left, so an upgrade that
matched nothing is visible instead of silent.
"""

import logging

# NAMED UNDER `odoo.`, not `__name__`: Odoo configures its handler on the odoo
# logger hierarchy, and a migration file's `__name__` is whatever the loader
# happened to give it. A log line nobody sees is the same as no log line, and
# CI greps for this one.
_logger = logging.getLogger("odoo.addons.sapian_landing.migration")

SEEDED_XMLID = "sapian_landing.deadline_paye"


def migrate(cr, version):
    if not version:
        # Fresh install: the XML above already carries the corrected row.
        return

    cr.execute(
        """
        SELECT d.id, d.window, d.days_after_period_end
          FROM sapian_filing_deadline d
          JOIN ir_model_data m
            ON m.model = 'sapian.filing.deadline' AND m.res_id = d.id
         WHERE m.module = %s AND m.name = %s
        """,
        ("sapian_landing", "deadline_paye"),
    )
    rows = cr.fetchall()
    if not rows:
        _logger.info(
            "sapian_landing: no seeded %s row on this database, nothing to correct",
            SEEDED_XMLID,
        )
        return

    corrected, left_alone = 0, 0
    for row_id, window, days in rows:
        if window != "days" or days != 30:
            left_alone += 1
            continue
        cr.execute(
            """
            UPDATE sapian_filing_deadline
               SET window = 'end_of_next_period',
                   days_after_period_end = 0,
                   source_note = %s
             WHERE id = %s
            """,
            (
                "VERIFIED — docs/ethiopian-tax-reference.md section 2: the "
                "declaration for one Ethiopian month is filed at any time "
                "during the following Ethiopian month. Corrected by the "
                "19.0.1.1.0 migration from the seeded 30-day analogy.",
                row_id,
            ),
        )
        corrected += 1

    _logger.info(
        "sapian_landing: employment income tax deadline corrected on %d row(s), "
        "%d left as edited by hand",
        corrected,
        left_alone,
    )
