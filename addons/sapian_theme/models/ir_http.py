# -*- coding: utf-8 -*-
"""Two values the backend footer needs, added to the session payload.

The backend is a single-page OWL application: server-side QWeb never runs
there, so a footer component has to be handed its text by the session rather
than reading a template variable. `session_info` is the one payload every
backend page already fetches, so this adds no request.

Both values are deliberately the SAME ones the login page uses — the support
contact is `sapian_theme.support_contact`, the system parameter the login
template reads — so a deployment configures a support number once and it
appears in both places. Two settings that mean the same thing is how one of
them ends up stale.
"""

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        info = super().session_info()
        info["sapian_support_contact"] = (
            self.env["ir.config_parameter"].sudo().get_param("sapian_theme.support_contact")
            or ""
        )
        # The company whose name the footer signs. `env.company` is the active
        # one, so a user switching companies signs the company they are in.
        info["sapian_footer_company"] = self.env.company.name or ""
        return info
