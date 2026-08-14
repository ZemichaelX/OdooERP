# -*- coding: utf-8 -*-
{
    "name": "SapianERP Sentry",
    "version": "19.0.1.0.0",
    "summary": "Error monitoring via Sentry. Dormant unless SENTRY_DSN is set. "
    "Load as a server-wide module, not a normal app.",
    "author": "Sapian Technologies PLC",
    "website": "https://sapiantech.com",
    "category": "Technical",
    "license": "LGPL-3",
    # `base` is JUSTIFIED BY CONVENTION and the Stage A audit closed this row.
    # There is no mechanical reference to it: this module hooks the logging
    # stack as a server-wide module and touches no base model. But every Odoo
    # module depends on base transitively, base is auto_install:True so it is
    # present in every database regardless, and it is not an application so it
    # adds no app tile. An empty `depends` would be unidiomatic and would gain
    # nothing.
    "depends": ["base"],
}
