{
    "name": "SapianERP Core",
    "version": "19.0.2.1.0",
    "summary": "Product base: company setup, Ethiopian defaults, a module catalog "
    "with on/off toggles and the onboarding wizard (company profile, module picks, "
    "light branding, Ethiopian defaults). The dependency every other "
    "sapian_*/l10n_et_* product module builds on. See README.md.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    # `web` is JUSTIFIED and the Stage A audit closed this row: the onboarding
    # wizard is exercised over real HTTP by tests/test_onboarding_web.py, an
    # HttpCase, which needs the web client's request dispatch. A scanner
    # looking only for models and xml ids cannot see that — the same blind-spot
    # class as a FIELD reference (l10n_et_tin) and a TEMPLATE CODE
    # (@template("et", ...)), both of which also produced false "unjustified"
    # verdicts in that audit. Do not remove on the strength of a grep.
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "security/sapian_core_security.xml",
        "views/sapian_module_catalog_views.xml",
        "wizard/sapian_onboarding_wizard_views.xml",
        "data/sapian_catalog_sync.xml",
    ],
    "application": True,
}
