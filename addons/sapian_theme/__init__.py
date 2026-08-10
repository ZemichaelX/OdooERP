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
