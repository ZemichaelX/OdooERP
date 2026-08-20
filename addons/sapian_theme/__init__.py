# -*- coding: utf-8 -*-
from . import brand
from . import models


def post_init_hook(env):
    """Give companies with no colour of their own the house brand.

    Only fills empties — see ResCompany._sapian_apply_brand_defaults.
    """
    import logging

    changed = env["res.company"]._sapian_apply_brand_defaults()
    logging.getLogger(__name__).info(
        "sapian_theme: brand defaults applied to %d compan%s (companies with a "
        "colour already set were left alone)",
        len(changed),
        "y" if len(changed) == 1 else "ies",
    )
    # THE INSTALL PATH for the default company logo. The upgrade path is
    # migrations/19.0.2.2.0/end-brand_assets.py, and they are separate on
    # purpose: a post_init_hook does not run on `-u`, so a database that
    # already has this module would keep Odoo's stock logo forever.
    #
    # The favicon is NOT here: res.company has no favicon field in Odoo 19, and
    # the browser tab is branded by views/favicon.xml instead.
    written = env["res.company"]._sapian_apply_default_logo()
    logging.getLogger(__name__).info(
        "sapian_theme: default logo written on %d compan%s",
        written,
        "y" if written == 1 else "ies",
    )
