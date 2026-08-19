# -*- coding: utf-8 -*-
"""What the backend footer is handed, added to the session payload.

The backend is a single-page OWL application: server-side QWeb never runs
there, so a footer component has to be handed its text by the session rather
than reading a template variable. `session_info` is the one payload every
backend page already fetches, so this adds no request.

THESE ARE SAPIAN'S VALUES, NOT THE TENANT'S — and that is the change.

They used to be `res.company.name` and the `sapian_theme.support_contact`
parameter, which meant a tenant installed for Golbon Trading signed every
backend page "© 2026 Golbon Trading. All Rights Reserved." with Golbon's
support number. Measured on the demo tenant before this change:

    © 2026 Selam General Trading PLC. All Rights Reserved.
    For Support: +251 11 123 4567 / support@selamtrading.example

That is the login page's "Powered by Odoo" defect pointed the other way: the
product on screen is not the product being sold. The competitor's footer signs
itself with the CONSULTANCY's name and the consultancy's numbers, and that is
the right shape.

They come from `sapian_theme/vendor.py` — constants, not system parameters, so
a tenant admin cannot rewrite them from Technical > System Parameters. The
reasoning is in that file; the guard is `TestVendorFooterIsNotTheTenants`,
which renames the company and sets the parameter and asserts this payload does
not move.
"""

from odoo import models

from .. import vendor


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        info = super().session_info()
        # Named `vendor` rather than reusing the old keys: the old names said
        # "the support contact" and "the footer company", which is exactly the
        # ambiguity that let the tenant's values sit there unnoticed.
        info["sapian_vendor_company"] = vendor.SAPIAN_COMPANY
        info["sapian_vendor_support"] = vendor.SAPIAN_SUPPORT
        info["sapian_vendor_url"] = vendor.SAPIAN_URL
        # The PRODUCT name, for backend JS that has to name the thing the user
        # is looking at — `sapian_theme_mail` renames Odoo's "Install Odoo"
        # prompt with it. Delivered the same way and for the same reason as the
        # three above: the backend is an OWL application, so a constant reaches
        # it through the session or not at all, and a JS literal would be a
        # fourth copy of a name that has to move in one edit at a re-brand.
        info["sapian_vendor_product"] = vendor.SAPIAN_PRODUCT
        return info
