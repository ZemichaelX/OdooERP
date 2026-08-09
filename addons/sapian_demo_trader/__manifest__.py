# -*- coding: utf-8 -*-
{
    "name": "SapianERP Demo Trader Tenant",
    "version": "19.0.1.0.0",
    "summary": "Provisioned 'Selam General Trading PLC' demo company: onboarded via "
    "the SapianERP wizard, realistic Ethiopian trading data (Amharic+English names, "
    "ETB pricing), one calendar month of transactions exercising every compliance "
    "path — 15% VAT sales, 3%/30%/15% WHT purchases, a posted payroll run and the "
    "statutory reports with clean tie-outs. Demo/sales-demo use only. See README.md.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    # Every app in sapian_core's STANDARD_CATALOG must be listed here: the demo
    # hands the onboarding wizard the FULL catalog, and the wizard installs
    # whatever is still uninstalled. Module installation is forbidden while
    # demo data loads (and inside tests), so every pick has to be installed
    # already by the time data/demo_trader.xml runs — then the wizard's install
    # step is a no-op. Adding a catalog entry without adding it here re-breaks
    # the demo build (scripts/build_demo.sh).
    "depends": [
        "sale_management",
        "purchase",
        "stock",
        "hr",
        "l10n_et_base",
        "l10n_et_payroll",
        "l10n_et_reports",
        # Standard Odoo Community apps offered by the catalog (no Ethiopian
        # layer yet) — dependencies purely so the demo can pre-install them.
        "crm",
        "mrp",
        "project",
        "mass_mailing",
        "fleet",
        "repair",
        "maintenance",
        "website_sale",
    ],
    # data/, not demo/: see data/demo_trader.xml for why, and build with
    # scripts/build_demo.sh (Odoo demo data OFF).
    "data": [
        "data/demo_trader.xml",
    ],
}
