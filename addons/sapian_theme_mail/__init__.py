# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Two provisioning steps, both idempotent, both safe to run again.

    1. The house colour on the email button of existing companies. `create`
       covers companies that do not exist yet; this covers every tenant already
       running. See ResCompany._sapian_apply_email_defaults for why the
       "untouched" test is `== Odoo's default` rather than `is empty`.

    2. The system partner's name, address and mark. This hook is the INSTALL
       half only — `migrations/19.0.1.3.0/end-bot_identity.py` is the other
       half, for databases that already carry this module. Both call the same
       method, because a fix that reaches only new databases is not a fix; see
       models/res_partner.py for why neither can be a data record.
    """
    import logging

    logger = logging.getLogger(__name__)
    changed = env["res.company"]._sapian_apply_email_defaults()
    logger.info(
        "sapian_theme_mail: email button colour applied to %d compan%s "
        "(a company that had chosen its own email colour was left alone)",
        len(changed),
        "y" if len(changed) == 1 else "ies",
    )
    env["res.partner"]._sapian_apply_bot_identity()
