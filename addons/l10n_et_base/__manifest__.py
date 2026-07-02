# -*- coding: utf-8 -*-
{
    "name": "Ethiopia Accounting Base (SapianERP)",
    "version": "19.0.1.0.0",
    "summary": "Ethiopian chart-of-accounts additions, VAT fiscal positions, "
    "threshold-driven withholding tax automation and the Proc 1395/2025 "
    "cash-payment cap. See README.md; re-verify all rates with the "
    "Ministry of Revenue before each go-live.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    "depends": ["account", "l10n_et"],
    "data": [
        "security/ir.model.access.csv",
        "security/l10n_et_base_security.xml",
        "views/l10n_et_wht_config_views.xml",
        "views/l10n_et_cash_cap_config_views.xml",
        "views/res_partner_views.xml",
        "views/l10n_et_base_menus.xml",
        "report/wht_certificate_reports.xml",
        "report/wht_certificate_templates.xml",
        "report/et_invoice_reports.xml",
        "report/et_invoice_templates.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "post_init_hook": "_l10n_et_base_post_init",
}
