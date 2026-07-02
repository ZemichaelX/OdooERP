{
    "name": "Ethiopia Payroll (PAYE & Pension)",
    "version": "19.0.1.0.0",
    "summary": "Ethiopian employment income tax (PAYE) and pension engine with effective-dated, configurable rate tables.",
    "description": """
Ethiopia Payroll — PAYE & Pension
=================================
Reusable Ethiopian localization for payroll math:
- PAYE monthly bands (2024/25 reform) as EFFECTIVE-DATED configuration records, so a future
  rate change never rewrites historical payslips.
- Pension (default 7% employee / 11% employer, citizens only, optional insurable cap).
- A compute helper that wraps the tested pure-Python reference calculator
  (reference/et_payroll_calc.py — fast pytest coverage, no Odoo needed).

IMPORTANT: Re-verify all rates against the Ministry of Revenue before a payroll go-live.
""",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    "depends": ["base", "sapian_core"],
    "data": [
        "security/ir.model.access.csv",
        "data/paye_band_data.xml",
        "data/pension_config_data.xml",
    ],
    "installable": True,
}
