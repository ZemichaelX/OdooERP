{
    "name": "Ethiopia Payroll (PAYE & Pension)",
    "version": "19.0.2.0.0",
    "summary": "Ethiopian payroll: effective-dated PAYE bands and pension rates, "
    "monthly payslip batch runs with manual input lines, and aggregated payroll "
    "journal posting. Re-verify all rates against the Ministry of Revenue before "
    "a payroll go-live. See README.md.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    "depends": ["hr", "account", "l10n_et_base", "sapian_core"],
    "data": [
        "security/ir.model.access.csv",
        "security/l10n_et_payroll_security.xml",
        "data/paye_band_data.xml",
        "data/pension_config_data.xml",
        "data/allowance_type_data.xml",
        "views/l10n_et_payslip_views.xml",
        "views/l10n_et_payroll_run_views.xml",
        "views/hr_employee_views.xml",
        "views/res_company_views.xml",
        "views/l10n_et_payroll_menus.xml",
        "views/allowance_type_views.xml",
        "report/l10n_et_payroll_reports.xml",
        "report/payslip_templates.xml",
        "report/statutory_templates.xml",
    ],
    "demo": [
        "demo/demo_payroll.xml",
    ],
}
