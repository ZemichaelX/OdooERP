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
    "depends": [
        "sale_management",
        "purchase",
        "stock",
        "hr",
        "l10n_et_base",
        "l10n_et_payroll",
        "l10n_et_reports",
    ],
    "demo": [
        "demo/demo_trader.xml",
    ],
}
