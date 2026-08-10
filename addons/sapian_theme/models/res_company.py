# -*- coding: utf-8 -*-
"""Brand defaults for the printed-document colour system.

Odoo's external report layouts read ``primary_color``/``secondary_color`` off
the company as data. We set the house brand as the DEFAULT for companies that
have expressed no preference, and never touch one that has.
"""

from odoo import api, models

from .. import brand


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model_create_multi
    def create(self, vals_list):
        """New companies start on the house brand.

        ``setdefault`` and not an assignment: a caller that passes its own
        colour — the onboarding wizard, a data file, a client who picked one —
        keeps it. This is the only reason a white-label deployment works.
        """
        for vals in vals_list:
            vals.setdefault("primary_color", brand.brand_primary())
            vals.setdefault("secondary_color", brand.brand_secondary())
        return super().create(vals_list)

    @api.model
    def _sapian_apply_brand_defaults(self):
        """Fill the brand on companies that have NO colour set. Idempotent.

        Runs once at install (post_init_hook) so an existing database picks the
        brand up on its documents. It writes only where the field is empty:
        a company that has already chosen a colour is never overwritten, which
        is the whole contract of this module for white-label clients.

        Returns the companies it actually changed, so the caller can log a
        number rather than assume the work happened.
        """
        untouched = (
            self.sudo()
            .with_context(active_test=False)
            .search(["|", ("primary_color", "=", False), ("secondary_color", "=", False)])
        )
        changed = self.browse()
        for company in untouched:
            vals = {}
            if not company.primary_color:
                vals["primary_color"] = brand.brand_primary()
            if not company.secondary_color:
                vals["secondary_color"] = brand.brand_secondary()
            if vals:
                company.write(vals)
                changed |= company
        return changed
