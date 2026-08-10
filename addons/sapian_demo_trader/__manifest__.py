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
    # Exactly what the demo demonstrates, and nothing else. Every catalog entry
    # the provisioner PICKS (the core and common tiers — see DEMO_CATALOG_TIERS
    # in models/sapian_demo_trader.py) must be listed here, because module
    # installation is forbidden while the registry is loading and inside tests,
    # so the wizard's install step has to be a no-op. Adding a core/common
    # catalog entry without adding it here breaks the demo build
    # (scripts/build_demo.sh); test_catalog_dependencies pins that.
    #
    # The catalog's `optional` tier — crm, mrp, project, mass_mailing, fleet,
    # repair, maintenance, website_sale — is deliberately ABSENT. None of them
    # is touched by the demo data; they were listed only because the wizard used
    # to be handed the whole catalog. Installing them put Manufacturing,
    # Project, Fleet, Repair, Maintenance and Website in the main menu bar of a
    # tenant built for a 2–5 person hardware shop. They remain in the catalog,
    # listed and not enabled.
    "depends": [
        "sale_management",
        "purchase",
        "stock",
        "hr",
        "l10n_et_base",
        "l10n_et_payroll",
        "l10n_et_reports",
    ],
    # NO data/ or demo/ entry, deliberately. The tenant used to load from
    # demo/, which meant it only appeared when Odoo demo data was enabled —
    # and that also loaded Odoo's US placeholder companies and a website bound
    # to the wrong company. Moving it to data/ removed that, but introduced a
    # worse fault: module data loads MID-INSTALL, so the wizard charted the new
    # company and account's end-of-load _auto_install_template hook then tried
    # to load the chart again ("Account codes must be unique ... 230100").
    # So provisioning is not triggered by installation at all: it is a plain
    # model method that scripts/build_demo.sh calls once the install is
    # finished. Everything still lives in the module — the build command is
    # the documented path, and the next demo database is identical.
}
