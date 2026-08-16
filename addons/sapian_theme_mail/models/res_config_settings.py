# -*- coding: utf-8 -*-
"""The attribution switch, where a client will actually find it.

WHY THIS FILE EXISTS AT ALL
---------------------------
The decision recorded in `views/mail_attribution.xml` is that "Powered by
SapianERP" is ours by default but the CLIENT's to switch off, because it rides
on their correspondence to their customers rather than on our product's chrome.

That was true of the field and false of the product. `sapian_email_attribution`
lived only on `res.company`, which a client reaches through Settings >
Technical > Companies — or in practice does not reach at all. A permission that
requires developer mode to exercise is not a permission the client has; it is a
line in a README. This puts the switch next to the other email settings, which
is where somebody looking for it would look.

WHERE IT LANDS
--------------
`mail`'s own "Email Templates" block in Settings > General Settings
(mail/views/res_config_settings_views.xml, `id="mail_templates_setting"`),
directly under **Button Text** and **Button Color** — the two fields this
module already seeds. One place for "what our outgoing mail looks like",
rather than a Sapian section nobody would think to open.

It inherits that block's `groups="mail.group_mail_template_editor,
base.group_system"`, so it is an administrator's setting, not something any
portal user can toggle.
"""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # `related` with readonly=False is the shape `res.config.settings` uses for
    # every company setting, including the two colour fields immediately above
    # it in the same block (mail/models/res_config_settings.py:50-51). Writing
    # the setting writes the company; there is no second copy of the value and
    # nothing to keep in step.
    sapian_email_attribution = fields.Boolean(
        related="company_id.sapian_email_attribution",
        readonly=False,
    )
