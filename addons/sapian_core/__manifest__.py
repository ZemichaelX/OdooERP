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
