# -*- coding: utf-8 -*-
"""Ethiopia labels its taxpayer identifier TIN, not VAT."""

from odoo import api, models

VAT_LABEL = "TIN"


class ResCountry(models.Model):
    _inherit = "res.country"

    @api.model
    def _l10n_et_ensure_vat_label(self):
        """Label Ethiopia's tax identifier ``TIN`` on every document.

        Core templates print the identifier as
        ``country_id.vat_label or "Tax ID"``. Core ``base`` ships no label for
        Ethiopia, so without this the invoice, the quotation, the delivery note
        and the POS receipt all say "Tax ID" where an Ethiopian accountant reads
        "TIN".

        THIS CANNOT BE A DATA RECORD, and the reason is worth keeping. The first
        attempt shipped ``<record id="base.et" model="res.country">`` and it
        **silently did nothing**: the module log said
        ``loading l10n_et_base/data/l10n_et_country_data.xml``, no error was
        raised, and the column stayed empty — because
        ``ir_model_data`` for ``base.et`` carries ``noupdate = true``, so every
        write to it from XML is skipped without a word. Caught only because the
        test asserted the value rather than the file loading. Defect register
        rule 2: the load succeeded, the work did not.

        Only fills an EMPTY label, so a client who chose their own wording keeps
        it. Idempotent; returns the record actually changed.
        """
        ethiopia = self.env.ref("base.et", raise_if_not_found=False)
        if ethiopia and not ethiopia.vat_label:
            ethiopia.vat_label = VAT_LABEL
            return ethiopia
        return self.browse()
