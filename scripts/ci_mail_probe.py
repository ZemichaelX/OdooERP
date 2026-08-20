# -*- coding: utf-8 -*-
"""Does an outgoing email still name another vendor? Run under `odoo shell`.

    odoo shell ${ARGS} -d <db> --no-http < scripts/ci_mail_probe.py

A FILE AND NOT AN INLINE STRING, for two reasons and both were paid for. YAML
block scalars end at the first unindented line, so a multi-line Python probe
embedded in a `run: |` step either breaks the workflow file or arrives at the
interpreter with the step's indentation still attached. And a probe that both
phases of a red/green proof must run has to be provably the SAME probe; a file
is, two copies of a shell heredoc are not.

Prints three facts and nothing else, so a CI step greps rather than parses:

    SAPIAN-MAIL leaks=<n>              in the body+subject actually sent
    SAPIAN-MAIL templates=<n> branded_templates=<n>

`leaks` is deliberately blunt — the bare word and any odoo.com URL — so a
phrase nobody wrote a rule for still shows up. It is the detector, not the
rewriter.
"""

import re

BRANDING = re.compile(r"odoo\.com|\bOdoo\b", re.I)

# The attribution every affected template ships some form of, and the subject
# `auth_signup.set_password_email` actually sends.
BODY = (
    'Powered by <a target="_blank" '
    'href="https://www.odoo.com?utm_source=db&amp;utm_medium=auth">Odoo</a>'
)
SUBJECT = "invites you to connect to Odoo"

mail = (
    env["mail.mail"]  # noqa: F821 - `env` is injected by `odoo shell`
    .sudo()
    .create(
        {
            "subject": SUBJECT,
            "body_html": BODY,
            "email_to": "probe@example.com",
            "auto_delete": False,
        }
    )
)

# The string handed to IrMailServer, not the stored field: the scrub runs at
# `_prepare_outgoing_body`, so reading `body_html` would answer a different
# question and would keep answering it after the hook was removed.
outgoing = mail._prepare_outgoing_body()
prepared = mail._prepare_outgoing_list()
outgoing_subject = prepared[0]["subject"] if prepared else SUBJECT
print("SAPIAN-MAIL leaks=%d" % len(BRANDING.findall(outgoing + " || " + outgoing_subject)))

templates = env["mail.template"].sudo().search([])  # noqa: F821
branded = [t for t in templates if BRANDING.search((t.body_html or "") + (t.subject or ""))]
print("SAPIAN-MAIL templates=%d branded_templates=%d" % (len(templates), len(branded)))
