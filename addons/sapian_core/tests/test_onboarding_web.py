# -*- coding: utf-8 -*-
"""Browser-path tests for the onboarding wizard (HttpCase → real /web/dataset
routing, session auth and action returns — the path the container unit tests
never exercised and where the original bugs lived).

True cross-request COMMIT semantics can't be asserted under HttpCase (test mode
intercepts commits); those were reproduced and verified over XML-RPC against a
live server (see the bug-fix session notes in the wizard docstring). These
tests pin the request-level contract: values applied through web dispatch,
redirect actions, the completion flag and the menu router.
"""

import json

from odoo.tests import HttpCase, tagged

VALID_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4"
    "z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
)


@tagged("post_install", "-at_install")
class TestOnboardingWebPath(HttpCase):
    def setUp(self):
        super().setUp()
        self.authenticate("admin", "admin")

    def _call_kw(self, model, method, args=None, kwargs=None):
        """One /web/dataset/call_kw round trip — the browser's RPC path."""
        response = self.url_open(
            f"/web/dataset/call_kw/{model}/{method}",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "model": model,
                        "method": method,
                        "args": args or [],
                        "kwargs": kwargs or {},
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        payload = response.json()
        self.assertNotIn(
            "error", payload, payload.get("error", {}).get("data", {}).get("message")
        )
        return payload.get("result")

    def _create_wizard(self, company_id, **overrides):
        fields_list = [
            "company_id",
            "company_name",
            "tin",
            "street",
            "city",
            "fiscal_year",
            "logo",
            "primary_color",
            "module_catalog_ids",
        ]
        values = self._call_kw("sapian.onboarding.wizard", "default_get", [fields_list])
        values["company_id"] = company_id
        values.update(overrides)
        return self._call_kw("sapian.onboarding.wizard", "create", [values])

    def test_apply_via_web_persists_and_redirects_home(self):
        """Apply through web dispatch: profile/branding/flag land on the
        company; the returned action is a redirect to the apps home (so the
        wizard never remains the client's restorable URL action)."""
        company_id = self._call_kw("res.company", "create", [{"name": "Web Onboard Co"}])
        wizard_id = self._create_wizard(
            company_id,
            company_name="Web Onboarded PLC",
            tin="0066554433",
            fiscal_year="ethiopian",
            logo=VALID_PNG,
            primary_color="#123abc",
        )
        result = self._call_kw("sapian.onboarding.wizard", "action_apply", [[wizard_id]])
        self.assertEqual(result["type"], "ir.actions.act_url")
        self.assertEqual(result["url"], "/odoo")

        company = self._call_kw(
            "res.company",
            "read",
            [[company_id]],
            {
                "fields": [
                    "name",
                    "primary_color",
                    "logo",
                    "sapian_onboarding_done",
                    "partner_id",
                ]
            },
        )[0]
        self.assertEqual(company["name"], "Web Onboarded PLC")
        self.assertEqual(company["primary_color"], "#123abc")
        self.assertTrue(company["logo"], "logo lost through the web path")
        self.assertTrue(company["sapian_onboarding_done"], "completion flag not set")
        company_fields = self._call_kw("res.company", "fields_get", [[], ["type"]])
        if "fiscalyear_last_month" in company_fields:
            fy = self._call_kw(
                "res.company",
                "read",
                [[company_id]],
                {"fields": ["fiscalyear_last_month", "fiscalyear_last_day"]},
            )[0]
            self.assertEqual(fy["fiscalyear_last_month"], "7")
            self.assertEqual(fy["fiscalyear_last_day"], 7)
        partner_fields = self._call_kw("res.partner", "fields_get", [[], ["type"]])
        if "l10n_et_tin" in partner_fields:
            tin = self._call_kw(
                "res.partner",
                "read",
                [[company["partner_id"][0]]],
                {"fields": ["l10n_et_tin"]},
            )[0]
            self.assertEqual(tin["l10n_et_tin"], "0066554433")

    def test_reopen_prefills_from_company(self):
        """A reopened wizard shows the company's saved values, not blanks."""
        company_id = self._call_kw("res.company", "create", [{"name": "Prefill Co"}])
        wizard_id = self._create_wizard(
            company_id,
            company_name="Prefill Applied PLC",
            logo=VALID_PNG,
            primary_color="#445566",
        )
        self._call_kw("sapian.onboarding.wizard", "action_apply", [[wizard_id]])
        defaults = self._call_kw(
            "sapian.onboarding.wizard",
            "default_get",
            [["company_name", "logo", "primary_color"]],
            {"context": {"allowed_company_ids": [company_id]}},
        )
        self.assertEqual(defaults["company_name"], "Prefill Applied PLC")
        self.assertEqual(defaults["primary_color"], "#445566")
        self.assertTrue(defaults["logo"], "logo not prefilled on reopen")

    def test_cancel_redirects_home(self):
        """Cancel never strands the user on a blank screen."""
        company_id = self._call_kw("res.company", "create", [{"name": "Cancel Co"}])
        wizard_id = self._create_wizard(company_id)
        result = self._call_kw("sapian.onboarding.wizard", "action_cancel", [[wizard_id]])
        self.assertEqual(result["type"], "ir.actions.act_url")
        self.assertEqual(result["url"], "/odoo")

    def test_menu_router_respects_completion_flag(self):
        """The onboarding menu opens the wizard only while the active company
        is not onboarded; afterwards it routes to the module catalog."""
        company_id = self._call_kw("res.company", "create", [{"name": "Router Co"}])
        context = {"allowed_company_ids": [company_id]}
        action = self._call_kw(
            "sapian.onboarding.wizard",
            "action_open_onboarding",
            [],
            {"context": context},
        )
        self.assertEqual(action["res_model"], "sapian.onboarding.wizard")
        self._call_kw("res.company", "write", [[company_id], {"sapian_onboarding_done": True}])
        action = self._call_kw(
            "sapian.onboarding.wizard",
            "action_open_onboarding",
            [],
            {"context": context},
        )
        self.assertEqual(action["res_model"], "sapian.module.catalog")
