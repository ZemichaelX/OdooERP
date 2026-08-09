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

import base64
import os

from odoo import SUPERUSER_ID, api
from odoo.addons.l10n_et_payroll.models import pension_config
from odoo.addons.l10n_et_payroll.models.payslip_compute import _calc
from odoo.tools import config as odoo_config

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

    _correct_pension_commencement(env)
    _report_affected_payslips(env, calc, correct_from)


def _correct_pension_commencement(env):
    """Correct the pension config commencement the same way, and for the same
    reason: the seeded date moved, so an upgraded database must move with it or
    code and data diverge silently (fresh installs would get 2014-07-08 while
    upgrades kept 2024-07-01 — exactly how the PAYE defect survived).

    The rates themselves are unchanged (7%/11%), so no payslip computes
    differently either way; this only stops the records asserting a start date
    that was never true. Same discipline as the bands: only an untouched,
    exactly-as-shipped row is corrected.
    """
    config_model = env["l10n.et.pension.config"].sudo()
    correct_from = pension_config.SEED_EFFECTIVE_FROM
    corrected = 0
    skipped = []

    for company in env["res.company"].sudo().search([("active", "=", True)]):
        configs = config_model.with_context(active_test=False).search(
            [("company_id", "=", company.id)]
        )
        misdated = configs.filtered(
            lambda config: config.effective_from == WRONG_EFFECTIVE_FROM
        )
        if not misdated:
            continue
        unmodified = (
            misdated == configs
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
            "Pension configuration commencement NOT corrected for %d "
            "company(ies) with customised rates/caps — review by hand "
            "(Proc 715/2011 art. 57 reaches 7%%/11%% on %s): %s",
            len(skipped),
            correct_from,
            ", ".join(company.display_name for company in skipped),
        )
    _logger.info(
        "Pension configuration: corrected commencement to %s for %d company(ies).",
        correct_from,
        corrected,
    )


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
    report = "\n".join(lines)
    _logger.warning(report)
    _persist_report(env, report, correct_from)


def _persist_report(env, report, correct_from):
    """Keep the report after the upgrade log scrolls away.

    This is the only record that a client's posted payroll was computed on the
    wrong bands, so a log line is not enough: it is written to a CSV-ish text
    file under the Odoo data directory AND stored as an ir.attachment so it can
    be retrieved from the UI later. Both locations are logged.
    """
    filename = "paye_band_correction_%s.txt" % correct_from.strftime("%Y%m%d")
    payload = report.encode("utf-8")

    attachment = (
        env["ir.attachment"]
        .sudo()
        .create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(payload),
                "mimetype": "text/plain",
                "description": "PAYE band commencement correction (Proc "
                "1395/2025, in force %s): payslips computed on the wrong "
                "generation. Reported only — no payslip was changed." % correct_from,
            }
        )
    )

    path = None
    try:
        directory = os.path.join(odoo_config["data_dir"], "l10n_et_payroll")
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        with open(path, "wb") as handle:
            handle.write(payload)
    except OSError as error:
        # A read-only data dir must not fail the upgrade: the attachment is
        # already stored, and that is the retrievable copy that matters.
        _logger.warning(
            "PAYE band correction report could not be written to disk (%s); "
            "it is stored as attachment id %s.",
            error,
            attachment.id,
        )
        path = None

    _logger.warning(
        "PAYE band correction report saved%s and as ir.attachment id %s "
        "(name %r) — retrieve it before the upgrade log is rotated.",
        (" to %s" % path) if path else "",
        attachment.id,
        filename,
    )
