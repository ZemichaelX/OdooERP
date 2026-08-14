# -*- coding: utf-8 -*-
"""Every selectable withholding rate must be one Ethiopian law actually has.

WHY AN INVARIANT AND NOT A LIST OF FOUR XML IDS
-----------------------------------------------
The defect this guards was: core `l10n_et` ships 2% WH and 35% WH, neither of
which Ethiopian law supports — the domestic rate has been 3% since Aug 2025 and
there is no 35% withholding rate at all (the punitive no-TIN rate is 30%). An
accountant raising a vendor bill saw six withholding options, two of them wrong.

Asserting "id_tax02, id_tax05, id_tax12, id_tax13 are inactive" would only
re-state the fix. It would pass forever while a SEVENTH wrong rate appeared in
the next Odoo release and went out on a client's declaration. The property that
must hold is: **no active withholding tax offers a rate our WHT configuration
does not serve.** That holds today at four deactivations and it holds whatever
upstream ships next.

WHAT COUNTS AS A WITHHOLDING TAX HERE
-------------------------------------
A negative-amount percentage tax on a company using chart 'et'. On this chart
VAT is positive and withholding is negative, so the sign is a structural signal
rather than a naming convention that can drift.

ONE KNOWN PASSENGER, STATED RATHER THAN LEFT TO RIDE
-----------------------------------------------------
Core `id_tax14` "15% WH" is *VAT* withholding (government bodies withholding VAT
on payments), which is a different mechanism from the income withholding this
module models — we do not implement it, and it is out of scope. It passes this
guard because 15% happens to coincide with `rate_foreign_digital`. That is a
coincidence, not a judgement that the tax is correct. If `rate_foreign_digital`
ever changes, this test will start failing on `id_tax14`, and the right response
is to model VAT withholding explicitly, not to widen the allowed set.
"""

from odoo import fields
from odoo.tests import tagged

from .common import L10nEtBaseCommon

# Rates are stored as fractions (0.03); taxes as signed percentages (-3.0).
_PCT = 100.0
_TOLERANCE = 0.001


@tagged("post_install", "-at_install")
class TestSupportedWhtRates(L10nEtBaseCommon):
    """The invariant, plus proof that it discriminates."""

    def _served_rates(self):
        """The withholding percentages our configuration can actually justify."""
        config, _skip_note = self.env["l10n.et.wht.config"]._l10n_et_resolve_config(
            self.company, fields.Date.context_today(self.env.user)
        )
        self.assertTrue(
            config,
            "No l10n.et.wht.config resolves for this company, so 'served rates' "
            "would be empty and every withholding tax would look unsupported. "
            "The configuration seeding is what is broken, not the taxes.",
        )
        return {
            round(config.rate_standard * _PCT, 3),
            round(config.rate_punitive * _PCT, 3),
            round(config.rate_foreign_digital * _PCT, 3),
        }

    def _active_withholding_taxes(self):
        """Negative-percentage taxes selectable on this company's chart."""
        return self.env["account.tax"].search(
            [
                ("company_id", "=", self.company.id),
                ("amount_type", "=", "percent"),
                ("amount", "<", 0),
                ("active", "=", True),
            ]
        )

    def test_no_active_withholding_tax_offers_an_unsupported_rate(self):
        served = self._served_rates()
        taxes = self._active_withholding_taxes()

        # Assert the positive first: a company with no withholding taxes at all
        # satisfies "none of them is wrong" by having nothing to check.
        self.assertTrue(
            taxes,
            "No active withholding taxes found on the 'et' chart at all — this "
            "test would pass by checking nothing. Expected at least our own "
            "3%/15%/30% purchase taxes.",
        )

        offenders = sorted(
            (t.name, t.type_tax_use, round(abs(t.amount), 3))
            for t in taxes
            if round(abs(t.amount), 3) not in served
        )
        self.assertEqual(
            offenders,
            [],
            "\nThese withholding taxes are SELECTABLE but offer a rate Ethiopian "
            "law does not support:\n"
            "    %s\n"
            "\nRates our configuration serves: %s%%\n"
            "\nAn accountant can pick one of these on a vendor bill; the WHT "
            "summary will then report that wrong figure correctly, and the "
            "declaration goes out wrong. Nothing will crash.\n"
            "\nIf the rate is genuinely wrong, deactivate it (never delete or "
            "rename it — posted bills reference it) by adding it to "
            "CORE_TAX_DEACTIVATIONS in models/template_et.py.\n"
            "If Ethiopian law gained the rate, that is a new "
            "l10n.et.wht.config record with an effective_from and a "
            "proclamation citation — not a widened allow-list."
            % (
                "\n    ".join(
                    "%s (%s) at %s%%" % (name, use, rate) for name, use, rate in offenders
                ),
                sorted(served),
            ),
        )

    def test_the_unsupported_core_rates_are_present_but_inactive(self):
        """History survives: the records still exist, they are just not offered.

        Deactivation is only correct if the record stays. A deleted tax orphans
        every move line that referenced it and breaks the WHT summary for prior
        periods, which is worse than the defect being fixed.
        """
        chart_template = self.env["account.chart.template"].with_company(self.company)
        found = 0
        for xmlid in ("id_tax02", "id_tax05", "id_tax12", "id_tax13"):
            tax = chart_template.with_context(active_test=False).ref(
                xmlid, raise_if_not_found=False
            )
            if not tax:
                continue
            found += 1
            with self.subTest(xmlid=xmlid):
                self.assertFalse(
                    tax.active,
                    "%s (%s at %s%%) is still selectable." % (xmlid, tax.name, tax.amount),
                )
        self.assertEqual(
            found,
            4,
            "Expected all four unsupported core taxes to still EXIST (inactive). "
            "Found %d. If they were deleted rather than deactivated, posted "
            "bills that used them now reference a missing record." % found,
        )

    def test_the_guard_discriminates(self):
        """Re-activate one and watch the invariant go red.

        An untested guard is another thing that passes by doing nothing.
        """
        chart_template = self.env["account.chart.template"].with_company(self.company)
        tax = chart_template.with_context(active_test=False).ref(
            "id_tax05", raise_if_not_found=False
        )
        self.assertTrue(tax, "id_tax05 not found; cannot prove the guard fires.")
        tax.active = True
        self.addCleanup(tax.write, {"active": False})

        served = self._served_rates()
        offenders = [
            t.name
            for t in self._active_withholding_taxes()
            if round(abs(t.amount), 3) not in served
        ]
        self.assertIn(
            "2% WH",
            offenders,
            "Re-activating the 2%% core withholding tax did NOT make it an "
            "offender, so a green run of the invariant proves nothing. "
            "Offenders seen: %s; served rates: %s" % (offenders, sorted(served)),
        )
