# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Put the house colour on the email button of existing companies.

    `create` covers companies that do not exist yet; this covers every tenant
    already running. See ResCompany._sapian_apply_email_defaults for why the
    "untouched" test is `== Odoo's default` rather than `is empty`.
    """
    import logging

    changed = env["res.company"]._sapian_apply_email_defaults()
    logging.getLogger(__name__).info(
        "sapian_theme_mail: email button colour applied to %d compan%s "
        "(a company that had chosen its own email colour was left alone)",
        len(changed),
        "y" if len(changed) == 1 else "ies",
    )
