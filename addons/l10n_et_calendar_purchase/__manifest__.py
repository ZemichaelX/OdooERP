# -*- coding: utf-8 -*-
{
    "name": "Ethiopian Calendar — Purchase Orders",
    "version": "19.0.1.0.0",
    "summary": "Puts the Ethiopian order deadline and expected arrival on the "
    "purchase order form and on the printed order.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    # A BRIDGE — see l10n_et_calendar_account for the reasoning. Both of this
    # one's source fields are Datetimes rather than Dates, which is handled in
    # the mixin, not here: a bridge is a declaration.
    "depends": ["l10n_et_calendar", "purchase"],
    "auto_install": True,
    "data": [
        "views/purchase_views.xml",
        "views/report_purchase_order.xml",
    ],
    # No new model and no new records: two mirrored fields on purchase.order,
    # which carries its own access rules.
}
