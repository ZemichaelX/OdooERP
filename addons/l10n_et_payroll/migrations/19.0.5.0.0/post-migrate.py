# -*- coding: utf-8 -*-
"""Re-audit the PAYE/pension commencement dates — this time across EVERY company.

19.0.4.0.0 corrected the commencement dates but iterated
``res.company.search([("active", "=", True)])``. An ARCHIVED company was
therefore never examined: not corrected, and — because the skip-and-warn branch
lived inside that loop — not warned about either. Found on a live database,
where a placeholder company archived by the demo provisioning kept bands dated
2024-07-01 while the migration reported success and logged nothing.

Two changes here:

1. the audit works from the ROWS, not from a filtered company list, so a
   misdated row is found regardless of the company's active flag. A row set
   that matches the shipped 1395/2025 signature exactly is corrected whether
   its company is archived or not — it is exactly as safe either way. The
   skip-and-warn path now means only "these bands are customised and I will not
   touch them", never "I could not see this company".
2. a POST-CONDITION: after correcting, the migration asserts that no band or
   pension row anywhere still carries the old commencement date, and lists any
   that do (company, count, date) at WARNING level. A migration that cannot
   state "I left nothing behind" is not finished.

Idempotent: a second run finds nothing misdated and the post-condition passes.
"""

import logging
from datetime import date, timedelta

from odoo import SUPERUSER_ID, api
from odoo.addons.l10n_et_payroll.models import pension_config
from odoo.addons.l10n_et_payroll.models.payslip_compute import _calc

_logger = logging.getLogger(__name__)

# The commencement date wrongly seeded before 19.0.4.0.0.
WRONG_EFFECTIVE_FROM = date(2024, 7, 1)


def _signature(rows):
    """Comparable (lower, upper, rate, deduction) signature of band rows."""
    return sorted(
        (
            round(row.lower_bound, 2),
            None if row.is_top_band else round(row.upper_bound, 2),
            round(row.rate, 6),
            round(row.deduction, 2),
        )
        for row in rows
    )


def _shipped_signature():
    return sorted(
        (
            round(lower, 2),
            None if upper is None else round(upper, 2),
            round(rate, 6),
            round(deduction, 2),
        )
        for lower, upper, rate, deduction in _calc.PAYE_BANDS_1395_2025
    )


def migrate(cr, version):
    if version is None:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    correct_from = _calc.PAYE_1395_2025_EFFECTIVE_FROM

    # ORDER MATTERS, and the LOG must show the order that actually happened.
    # An earlier version emitted this summary after the post-condition, so the
    # log read as though the assertion had run before the band correction it
    # asserts on. It had not — but an assertion that appears to have run first
    # is worthless as evidence even when it is correct. Every summary line is
    # therefore emitted by the step that produced it, and the post-condition,
    # which must be last, is called last.
    corrected, skipped = _correct_bands(env, correct_from)
    _logger.info(
        "PAYE band re-audit: corrected %d company(ies) (archived included), "
        "skipped %d with customised bands.",
        len(corrected),
        len(skipped),
    )
    _correct_pension(env)
    _assert_nothing_left_behind(env, correct_from)


def _misdated_companies(env, model_name):
    """Companies owning rows at the wrong commencement date — ANY company.

    ``active_test=False`` on both the rows and the company read: the previous
    version's ``[("active", "=", True)]`` company loop is exactly what made an
    archived company invisible.
    """
    rows = (
        env[model_name]
        .sudo()
        .with_context(active_test=False)
        .search([("effective_from", "=", WRONG_EFFECTIVE_FROM)])
    )
    by_company = {}
    for row in rows:
        by_company.setdefault(row.company_id, env[model_name].browse())
        by_company[row.company_id] |= row
    return by_company


def _correct_bands(env, correct_from):
    band_model = env["l10n.et.paye.band"].sudo().with_context(active_test=False)
    shipped = _shipped_signature()
    corrected = []
    skipped = []

    for company, misdated in _misdated_companies(env, "l10n.et.paye.band").items():
        all_rows = band_model.search([("company_id", "=", company.id)])
        unmodified = (
            misdated == all_rows
            and _signature(misdated) == shipped
            and not any(row.effective_to for row in misdated)
        )
        if not unmodified:
            skipped.append(company)
            continue
        misdated.write({"effective_from": correct_from})
        corrected.append(company)

    if skipped:
        _logger.warning(
            "PAYE band commencement NOT corrected for %d company(ies) with "
            "customised bands — review them by hand against Proclamation "
            "1395/2025 (in force %s): %s",
            len(skipped),
            correct_from,
            ", ".join(company.display_name for company in skipped),
        )

    # Seed the earlier generation(s) for the companies just corrected; the
    # ordinary seeder skips any company that already owns bands.
    previous = [
        generation
        for generation in _calc.PAYE_BAND_GENERATIONS
        if generation.effective_from < correct_from
    ]
    for company in corrected:
        for generation in previous:
            if band_model.search_count(
                [
                    ("company_id", "=", company.id),
                    ("effective_from", "=", generation.effective_from),
                ]
            ):
                continue
            band_model.create(
                [
                    {
                        "company_id": company.id,
                        "lower_bound": lower,
                        "upper_bound": 0.0 if upper is None else upper,
                        "is_top_band": upper is None,
                        "rate": rate,
                        "deduction": deduction,
                        "effective_from": generation.effective_from,
                        "effective_to": correct_from - timedelta(days=1),
                    }
                    for lower, upper, rate, deduction in generation.bands
                ]
            )
    return corrected, skipped


def _correct_pension(env):
    correct_from = pension_config.SEED_EFFECTIVE_FROM
    config_model = env["l10n.et.pension.config"].sudo().with_context(active_test=False)
    corrected = 0
    skipped = []

    for company, misdated in _misdated_companies(env, "l10n.et.pension.config").items():
        all_rows = config_model.search([("company_id", "=", company.id)])
        unmodified = (
            misdated == all_rows
            and len(misdated) == 1
            and not misdated.effective_to
            and round(misdated.employee_rate, 6)
            == round(_calc.DEFAULT_PENSION_EMPLOYEE_RATE, 6)
            and round(misdated.employer_rate, 6)
            == round(_calc.DEFAULT_PENSION_EMPLOYER_RATE, 6)
            and not misdated.insurable_cap
        )
        if not unmodified:
            skipped.append(company)
            continue
        misdated.write({"effective_from": correct_from})
        corrected += 1

    if skipped:
        _logger.warning(
            "Pension commencement NOT corrected for %d company(ies) with "
            "customised rates/caps — review by hand (Proc 715/2011 art. 57 "
            "reaches 7%%/11%% on %s): %s",
            len(skipped),
            correct_from,
            ", ".join(company.display_name for company in skipped),
        )
    _logger.info("Pension re-audit: corrected %d company(ies).", corrected)


def _assert_nothing_left_behind(env, correct_from):
    """Post-condition: NO row anywhere may still carry the old commencement.

    Reports what remains rather than raising: a customised row that a human
    must decide about is a legitimate leftover, and failing the upgrade over it
    would strand the database mid-migration. What is not acceptable is silence.
    Returns the leftovers so tests can assert on them.
    """
    leftovers = []
    for model_name, label in (
        ("l10n.et.paye.band", "PAYE band"),
        ("l10n.et.pension.config", "pension configuration"),
    ):
        for company, rows in _misdated_companies(env, model_name).items():
            leftovers.append((label, company, len(rows), WRONG_EFFECTIVE_FROM))

    if not leftovers:
        _logger.info(
            "Post-condition OK: no PAYE band or pension row anywhere still "
            "carries the superseded commencement date %s (archived companies "
            "included).",
            WRONG_EFFECTIVE_FROM,
        )
        return leftovers

    lines = [
        "",
        "=" * 78,
        "POST-CONDITION FAILED — ROWS STILL AT THE SUPERSEDED COMMENCEMENT DATE",
        "These carry %s, before Proclamation 1395/2025 commenced (%s)."
        % (WRONG_EFFECTIVE_FROM, correct_from),
        "They were NOT corrected because they do not match the shipped set, so",
        "they are customised configuration a human must decide about. Any",
        "payslip they price is computed on bands that were not the law.",
        "-" * 78,
        "%-24s %-34s %6s %12s" % ("WHAT", "COMPANY", "ROWS", "DATE"),
    ]
    for label, company, count, wrong_date in leftovers:
        lines.append(
            "%-24s %-34s %6d %12s"
            % (label, (company.display_name or "?")[:34], count, wrong_date)
        )
    lines.append("=" * 78)
    _logger.warning("\n".join(lines))
    return leftovers
