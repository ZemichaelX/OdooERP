# -*- coding: utf-8 -*-
{
    "name": "Pharma Vertical (SapianERP)",
    "version": "19.0.1.0.0",
    "summary": "Pharmaceutical distribution compliance (the DAT blueprint): "
    "mandatory batch+expiry on pharma receipts, FEFO picking, configurable "
    "expiry-alert digests with escalation states, expired-lot delivery blocking, "
    "GS1 DataMatrix scan parsing, import shipment dossiers (batch ↔ import file "
    "traceability) and a one-click batch recall report with customer contacts. "
    "EFDA export is a stub pending official specs. See README.md.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Localization/Ethiopia",
    "license": "LGPL-3",
    "depends": ["stock", "product_expiry"],
    "data": [
        "security/ir.model.access.csv",
        "security/vertical_pharma_security.xml",
        "data/vertical_pharma_data.xml",
        "report/pharma_recall_reports.xml",
        "report/pharma_recall_templates.xml",
        "views/product_template_views.xml",
        "views/stock_lot_views.xml",
        "views/stock_picking_views.xml",
        "views/pharma_import_dossier_views.xml",
        "views/res_company_views.xml",
    ],
}
