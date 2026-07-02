{
    "name": "SapianERP Core",
    "version": "19.0.1.0.0",
    "summary": "Product base: company setup, Ethiopian defaults, and a module catalog "
    "with on/off toggles. The dependency every other sapian_*/l10n_et_* product "
    "module builds on. See README.md.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/sapian_module_catalog_views.xml",
    ],
    "application": True,
}
