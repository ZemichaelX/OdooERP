# -*- coding: utf-8 -*-
"""Correct the PAYE band commencement date and add the missing 979/2016 generation.

The shipped bands (0/15/20/25/30/35%, exempt to 2,000, top above 14,000) are
those of Income Tax (Amendment) Proclamation 1395/2025, in force 8 July 2025.
They were seeded as effective 2024-07-01, so every payslip dated
2024-07-01 → 2025-07-07 computed PAYE on bands more generous than the law of
the day — understated PAYE, which is the employer's liability at assessment.
The preceding regime (Proclamation 979/2016) had no records at all.

This migration:

1. corrects ``effective_from`` to 2025-07-08 ONLY for companies whose bands
   still match the shipped 1395/2025 set exactly and are otherwise unmodified;
2. leaves any customised set untouched and logs a warning naming the company,
   so a human decides;
3. seeds the 979/2016 generation for the companies it corrected;
4. REPORTS every existing payslip dated before the boundary whose PAYE would
   now differ — employee, period, old tax, new tax, delta — and changes none of
   them. Posted payroll is not something a migration rewrites on its own
   authority; surfacing it is the deliverable.

Idempotent: a second run finds the dates already correct and the 979 rows
already present, and does nothing.
"""

import logging
from datetime import date, timedelta

from odoo import SUPERUSER_ID, api
from odoo.addons.l10n_et_payroll.models.payslip_compute import _calc

_logger = logging.getLogger(__name__)

WRONG_EFFECTIVE_FROM = date(2024, 7, 1)


def _shipped_1395_signature(calc):
    """The shipped current-generation bands as a comparable signature."""
    return sorted(
        (
            round(lower, 2),
            None if upper is None else round(upper, 2),
            round(rate, 6),
            round(deduction, 2),
        )
        for lower, upper, rate, deduction in calc.PAYE_BANDS_1395_2025
    )


def _company_signature(bands):
    """Existing band rows as the same comparable signature."""
    return sorted(
        (
            round(band.lower_bound, 2),
            None if band.is_top_band else round(band.upper_bound, 2),
            round(band.rate, 6),
            round(band.deduction, 2),
        )
        for band in bands
    )


def migrate(cr, version):
    if version is None:
        # Fresh install: the seeder already writes the correct dates.
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    band_model = env["l10n.et.paye.band"].sudo()
    calc = _calc
    correct_from = calc.PAYE_1395_2025_EFFECTIVE_FROM
    shipped = _shipped_1395_signature(calc)

    corrected_companies = env["res.company"].browse()
    skipped = []

    for company in env["res.company"].sudo().search([("active", "=", True)]):
        company_bands = band_model.with_context(active_test=False).search(
            [("company_id", "=", company.id)]
        )
        if not company_bands:
            continue

        misdated = company_bands.filtered(
            lambda band: band.effective_from == WRONG_EFFECTIVE_FROM
        )
        if not misdated:
            # Already corrected (or never wrong): nothing to do for this company.
            continue

        # Only touch a set that is EXACTLY what we shipped: same rows, no
        # closing date, and nothing else living in that window. Anything else
        # is a client's own configuration and is none of this migration's
        # business.
        unmodified = (
            misdated == company_bands
            and _company_signature(misdated) == shipped
            and not any(band.effective_to for band in misdated)
        )
        if not unmodified:
            skipped.append(company)
            continue

        misdated.write({"effective_from": correct_from})
        corrected_companies |= company

    if skipped:
        _logger.warning(
            "PAYE band commencement NOT corrected for %d company(ies) with "
            "customised bands — review them by hand against Proclamation "
            "1395/2025 (in force 2025-07-08): %s",
            len(skipped),
            ", ".join(company.display_name for company in skipped),
        )

    # Seed the 979/2016 generation for the companies we just corrected. The
    # ordinary seeder skips any company that already has bands, so it cannot do
    # this itself.
    previous = [
        generation
        for generation in calc.PAYE_BAND_GENERATIONS
        if generation.effective_from < correct_from
    ]
    for company in corrected_companies:
        for generation in previous:
            already = band_model.with_context(active_test=False).search_count(
                [
                    ("company_id", "=", company.id),
                    ("effective_from", "=", generation.effective_from),
                ]
            )
            if already:
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

    _logger.info(
        "PAYE bands: corrected commencement to %s for %d company(ies); "
        "seeded %d earlier generation(s) where missing.",
        correct_from,
        len(corrected_companies),
        len(previous),
    )

    _report_affected_payslips(env, calc, correct_from)


def _report_affected_payslips(env, calc, correct_from):
    """Log every pre-boundary payslip whose PAYE would now differ. Changes none.

    Payslips select bands by their period END (``date_to``), so that is the
    date compared here — the same one ``_compute_amounts`` uses.
    """
    payslips = (
        env["l10n.et.payslip"]
        .sudo()
        .search([("date_to", "<", correct_from)], order="date_to, id")
    )
    if not payslips:
        _logger.info(
            "PAYE band correction: no payslip is dated before %s — nothing to " "review.",
            correct_from,
        )
        return

    rows = []
    for slip in payslips:
        bands = calc.get_paye_bands(slip.date_to)
        recomputed = calc.compute_paye(slip.taxable_income, bands=bands)
        delta = round(recomputed - slip.paye, 2)
        if abs(delta) >= 0.01:
            rows.append((slip, recomputed, delta))

    if not rows:
        _logger.info(
            "PAYE band correction: %d payslip(s) dated before %s, none whose "
            "PAYE changes under the corrected bands.",
            len(payslips),
            correct_from,
        )
        return

    total = round(sum(row[2] for row in rows), 2)
    lines = [
        "",
        "=" * 78,
        "PAYE BAND CORRECTION — PAYSLIPS AFFECTED (REPORTED ONLY, NOT CHANGED)",
        "These payslips were computed on the 1395/2025 bands while dated before",
        "that proclamation commenced (%s). Under the bands actually in force" % correct_from,
        "their PAYE differs as below. A positive delta is tax that was",
        "UNDERSTATED. Posted payroll is not rewritten automatically — decide",
        "per payslip, with your accountant, whether to correct or disclose.",
        "-" * 78,
        "%-28s %-10s %12s %12s %10s" % ("EMPLOYEE", "PERIOD", "OLD PAYE", "NEW PAYE", "DELTA"),
    ]
    for slip, recomputed, delta in rows:
        lines.append(
            "%-28s %-10s %12.2f %12.2f %10.2f"
            % (
                (slip.employee_id.name or "?")[:28],
                slip.date_to and slip.date_to.strftime("%Y-%m") or "?",
                slip.paye,
                recomputed,
                delta,
            )
        )
    lines.append("-" * 78)
    lines.append("%d payslip(s) affected; total PAYE delta %.2f" % (len(rows), total))
    lines.append("=" * 78)
    _logger.warning("\n".join(lines))
