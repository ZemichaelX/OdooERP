# -*- coding: utf-8 -*-
{
    "name": "Ethiopian Calendar — Invoices",
    "version": "19.0.1.0.0",
    "summary": "Puts the Ethiopian invoice date and due date on the customer "
    "invoice form and on the printed invoice.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    # A BRIDGE. It exists only so that l10n_et_calendar never has to depend on
    # `account`: the calendar is the calendar, and a client who wants Ethiopian
    # dates on a purchase order must not be handed a chart of accounts with
    # them — a claim l10n_et_calendar's own CI job asserts.
    #
    # auto_install means this appears by itself exactly when both sides are
    # already present, and stays out of the way when either is not.
    "depends": ["l10n_et_calendar", "account"],
    "auto_install": True,
    "data": [
        "views/account_move_views.xml",
        "views/report_invoice.xml",
    ],
    # No new model and no new records: two mirrored fields on account.move,
    # which carries its own access rules. Nothing to grant access to.
}
