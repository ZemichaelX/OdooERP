# -*- coding: utf-8 -*-
{
    "name": "SapianERP Dress Rehearsal",
    "version": "19.0.1.0.0",
    "summary": "Pre-release ritual: provision a fresh tenant through the onboarding "
    "wizard, script one realistic month (August 2026) of sales, purchases, payroll, "
    "payments and an inventory adjustment, then run an independent exam that ties out "
    "the trial balance, VAT declaration, WHT summary, payroll and stock — recomputed "
    "from source documents, expected-vs-actual. Rerunnable; not for client installs. "
    "See README.md.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    "depends": [
        "sapian_core",
        "sale_management",
        "purchase",
        "stock",
        "hr",
        "l10n_et_base",
        "l10n_et_payroll",
        "l10n_et_reports",
    ],
}
