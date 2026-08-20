# -*- coding: utf-8 -*-
{
    "name": "SapianERP Landing Page",
    "version": "19.0.1.0.0",
    "summary": "The page a person lands on: what is owed to the Ministry of "
    "Revenues and by when, what does not reconcile, and what the business "
    "earned. Every figure is read from the report that owns it.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    # WHY A MODULE OF ITS OWN, and not part of sapian_core.
    #
    # This page reads the statutory reports and the payroll runs. Putting it in
    # sapian_core would make the product's PLATFORM module depend on its
    # accounting and payroll modules, which is the wrong way round and is a
    # direction l10n_et_payroll deliberately reversed once already (see its
    # manifest: it no longer depends on sapian_core).
    #
    # l10n_et_calendar is a HARD dependency, and that is a decision rather than
    # convenience: the deadlines are set in the Ethiopian calendar, so a page
    # that showed them in Gregorian would leave the operator converting in their
    # head every month. A soft "use it if it is installed" would make the
    # product's compliance page mean different things on two tenants.
    "depends": [
        "l10n_et_reports",
        "l10n_et_payroll",
        "l10n_et_calendar",
        "sapian_theme",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/filing_deadline_data.xml",
        "views/sapian_landing_views.xml",
        "views/sapian_filing_views.xml",
        "views/menus.xml",
    ],
}
