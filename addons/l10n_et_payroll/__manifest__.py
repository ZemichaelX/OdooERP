{
    "name": "Ethiopia Payroll (PAYE & Pension)",
    "version": "19.0.5.0.0",
    "summary": "Ethiopian payroll: effective-dated PAYE bands and pension rates, "
    "monthly payslip batch runs with manual input lines, and aggregated payroll "
    "journal posting. Re-verify all rates against the Ministry of Revenue before "
    "a payroll go-live. See README.md.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    # A top-level app, not an Employees section. This is the standalone
    # Payroll+HR product, and it carries its own icon
    # (static/description/icon.png) so it renders as a tile rather than a bare
    # label. See brand/icons/README.md.
    "application": True,
    # STANDALONE. `depends` describes what the CODE requires, not what a
    # customer buys. A Stage A dependency audit found ZERO references to
    # sapian_core anywhere in this module — no sapian.module.catalog, no
    # sapian.onboarding.wizard, no sapian_core xml id, no group, no import; the
    # only `groups=` attributes here are account.*, base.* and hr.*. Since
    # sapian_core is application:True, declaring it also put the SapianERP tile
    # in every database that installed payroll.
    #
    # That "Payroll+HR ships with the SapianERP core" rule is real, but it is
    # PRODUCT PACKAGING and belongs in sapian.module.catalog, not here. Proven
    # standalone: installed on a database where sapian_core is 'uninstalled',
    # full suite green. Do not re-add sapian_core without a code reference.
    "depends": ["hr", "account", "l10n_et_base"],
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
        "views/paye_band_views.xml",
        "views/pension_config_views.xml",
        "report/l10n_et_payroll_reports.xml",
        "report/payslip_templates.xml",
        "report/statutory_templates.xml",
    ],
    "demo": [
        "demo/demo_payroll.xml",
    ],
}
