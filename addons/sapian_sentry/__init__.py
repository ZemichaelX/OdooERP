# -*- coding: utf-8 -*-
"""Sentry error monitoring.

Loaded as a SERVER-WIDE module (server_wide_modules in odoo.conf) so it
initialises before any database and catches start-up failures too.

Completely dormant unless SENTRY_DSN is set: no init, no log noise, no
behaviour change. Monitoring must never be able to stop a tenant starting.
"""

import logging
import os

_logger = logging.getLogger(__name__)

# Odoo raises these as ordinary business outcomes, not defects. Without this
# filter Sentry fills with correct application behaviour within a day and
# stops being read.
_IGNORED = (
    "UserError",
    "ValidationError",
    "AccessError",
    "AccessDenied",
    "MissingError",
    "RedirectWarning",
    "CacheMiss",
    "NotFound",
)


def _before_send(event, hint):
    exc_info = hint.get("exc_info")
    if exc_info and exc_info[0].__name__ in _IGNORED:
        return None
    return event


def _init_sentry():
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return
    try:
        import sentry_sdk
    except ImportError:
        _logger.warning("SENTRY_DSN set but sentry-sdk not installed; monitoring off.")
        return
    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=os.environ.get("SENTRY_ENVIRONMENT", "unknown"),
            release=os.environ.get("SENTRY_RELEASE"),
            server_name=os.environ.get("HOSTNAME"),
            send_default_pii=False,
            traces_sample_rate=0,
            before_send=_before_send,
        )
        _logger.info(
            "Sentry enabled (environment=%s).",
            os.environ.get("SENTRY_ENVIRONMENT", "unknown"),
        )
    except Exception:
        _logger.exception("Sentry init failed; continuing without monitoring.")


_init_sentry()