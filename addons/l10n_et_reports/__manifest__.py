# -*- coding: utf-8 -*-
{
    "name": "Ethiopia Statutory Reports (SapianERP)",
    "version": "19.0.1.1.0",
    "summary": "Monthly VAT declaration and withholding tax summary for Ethiopia, "
    "computed from posted moves via the l10n_et_base tax codes, with GL tie-out. "
    "Verify layouts against the current MoR forms before filing. See README.md.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    # A top-level app ("Ethiopian Compliance"), not a section under Accounting >
    # Reporting. Compliance is what the client is buying; it carries its own
    # icon (static/description/icon.png). See brand/icons/README.md.
    "application": True,
    "depends": ["l10n_et_base"],
    "data": [
        "security/ir.model.access.csv",
        "security/l10n_et_reports_security.xml",
        "views/l10n_et_reports_views.xml",
        "report/l10n_et_reports_reports.xml",
        "report/l10n_et_reports_templates.xml",
    ],
}
