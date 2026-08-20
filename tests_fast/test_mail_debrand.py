# -*- coding: utf-8 -*-
"""Goldens for the outgoing-email scrub, against markup quoted from upstream.

Every fixture below is copied verbatim from the Odoo 19 file named above it, so
these tests fail when the scrub stops matching what Odoo actually SHIPS rather
than when it stops matching a paraphrase of it.

WHY HERE AND NOT IN `addons/sapian_theme_mail/reference/`. Because CI runs
`pytest tests_fast/` and nothing else. `pytest addons/<module>/reference/`,
which CLAUDE.md documents, cannot import those modules at all: pytest walks up
through the addon's `__init__.py`, that imports `odoo`, and collection dies
before a single test runs — the payroll goldens are in this directory for the
same reason. The MODULE under test stays in `reference/`, which is what rule 10
is about: logic testable without a running Odoo, called by an Odoo model.

Run: pytest tests_fast/
"""

import importlib.util
import os
import sys as _sys

_MOD = os.path.join(
    os.path.dirname(__file__),
    "..",
    "addons",
    "sapian_theme_mail",
    "reference",
    "mail_debrand.py",
)
_spec = importlib.util.spec_from_file_location("mail_debrand", _MOD)
_debrand = importlib.util.module_from_spec(_spec)
_sys.modules[_spec.name] = _debrand
_spec.loader.exec_module(_debrand)

debrand_html = _debrand.debrand_html
debrand_subject = _debrand.debrand_subject
odoo_branding_in = _debrand.odoo_branding_in

PRODUCT = "SapianERP"
OURS = 'Powered by <a target="_blank" href="https://sapiantech.com">SapianERP</a>'

# ---- fixtures, verbatim from Odoo 19 ---------------------------------------

# addons/auth_signup/data/mail_template_data.xml — three templates share this.
ATTRIBUTION = (
    'Powered by <a target="_blank" href="https://www.odoo.com?utm_source=db&amp;'
    'utm_medium=auth" style="color: #875A7B;">Odoo</a>'
)

# addons/im_livechat/data/mail_templates.xml — the chat transcript, which goes
# to the visitor on the client's website.
LIVECHAT = (
    '<tr><td align="center" style="min-width: 590px;">\n'
    '        Powered by <a target="_blank" href="https://www.odoo.com?utm_source=db&amp;'
    'utm_medium=email" style="color: #875A7B;">Odoo</a>\n'
    "</td></tr>"
)

# addons/account/data/mail_template_data.xml — the e-invoice notification. Not
# words: the competitor's actual logo, at the head of a finance email.
ACCOUNT_LOGO = (
    '<img alt="Odoo" src="/web/static/img/logo_inverse_white_206px.png" '
    'style="height: 2em; object-fit: contain;" class="align-baseline w-auto"/>'
)

# addons/auth_signup/data/mail_template_data.xml — set_password_email's body.
INVITE_BODY = (
    "You have been invited by Abebe of Selam General Trading PLC to connect on Odoo.\n"
    "<b>This link will remain valid during 6 days</b><br />\n"
    'Your Odoo domain is: <b><a href="https://selam.example.com">'
    "https://selam.example.com</a></b><br />\n"
    "Never heard of Odoo? It's an all-in-one business software loved by 12+ "
    "million users. It will considerably improve your experience at work and "
    "increase your productivity.\n"
    "<br /><br />\n"
    'Have a look at the <a href="https://www.odoo.com/page/tour?utm_source=db&amp;'
    'utm_medium=auth" style="color: #875A7B;">Odoo Tour</a> to discover the tool.\n'
    "<br /><br />\n"
    "Enjoy Odoo!<br />\n"
)

INVITE_SUBJECT = "Abebe from Selam General Trading PLC invites you to connect to Odoo"

# addons/account/data/mail_template_data.xml and base's install-request mail:
# `/odoo/...` is Odoo 19's own BACKEND ROUTE, not branding. Both link into it
# for the button the mail exists for.
BACKEND_ROUTE = (
    '<a t-attf-href="/odoo/accounting/action-account_move/{{ object.id }}" '
    'style="color: #14454F;">View your invoice</a>'
)

# addons/auth_signup/data/mail_template_data.xml — the odoo.com is the anchor's
# TEXT and the href is a variable, so the link rule never sees it.
DOMAIN_SAMPLE = (
    '<a t-att-href="website_url" t-out="website_url or \'\'">' "http://yourcompany.odoo.com</a>"
)


# ---- the fixtures really are branded (the red half) ------------------------


def test_every_fixture_is_branded_before_the_scrub():
    """Otherwise every assertion below passes by having nothing to do.

    Counted, not merely truthy: the invite body carries six mentions, and a
    fixture that quietly lost one would weaken the test that follows it.
    """
    assert len(odoo_branding_in(ATTRIBUTION)) == 2  # the URL and the word
    assert len(odoo_branding_in(LIVECHAT)) == 2
    assert len(odoo_branding_in(ACCOUNT_LOGO)) == 1
    assert len(odoo_branding_in(INVITE_SUBJECT)) == 1
    assert len(odoo_branding_in(INVITE_BODY)) == 6


# ---- and are clean after it ------------------------------------------------


def test_the_attribution_becomes_ours():
    out = debrand_html(ATTRIBUTION, PRODUCT, attribution_html=OURS)
    assert odoo_branding_in(out) == []
    assert "sapiantech.com" in out


def test_the_attribution_can_be_removed_outright():
    """Off means off. It never falls back to another vendor's name."""
    out = debrand_html(ATTRIBUTION, PRODUCT, attribution_html=None)
    assert odoo_branding_in(out) == []
    assert "sapiantech.com" not in out
    assert "Powered by" not in out


def test_the_livechat_transcript_keeps_its_table_and_loses_the_vendor():
    out = debrand_html(LIVECHAT, PRODUCT, attribution_html=OURS)
    assert odoo_branding_in(out) == []
    # The surrounding markup is structure, not branding, and must survive.
    assert out.startswith('<tr><td align="center"')
    assert out.rstrip().endswith("</td></tr>")


def test_the_account_logo_becomes_our_mark():
    out = debrand_html(ACCOUNT_LOGO, PRODUCT, attribution_html=OURS)
    assert odoo_branding_in(out) == []
    assert "/sapian_theme/static/src/img/sapian_logo.png" in out
    assert 'alt="SapianERP"' in out


def test_the_invite_loses_the_marketing_and_keeps_the_instructions():
    out = debrand_html(INVITE_BODY, PRODUCT, attribution_html=OURS)
    assert odoo_branding_in(out) == []
    # What the recipient actually needs is still there.
    assert "This link will remain valid during 6 days" in out
    assert "https://selam.example.com" in out
    assert "Your SapianERP address is" in out
    assert "Enjoy SapianERP!" in out
    # And the competitor's pitch is not.
    assert "12+ million users" not in out
    assert "discover the tool" not in out


def test_the_subject_is_scrubbed_too():
    out = debrand_subject(INVITE_SUBJECT, PRODUCT)
    assert odoo_branding_in(out) == []
    assert out.endswith("invites you to connect to SapianERP")


def test_the_backend_route_is_not_branding_and_is_left_intact():
    """`/odoo/...` is the product's own route, and the button the mail exists for.

    Found by the guard, not by inspection: the sweep flagged
    `account.mail_template_einvoice_notification` and the module install request
    because `\\bOdoo\\b` matches inside `/odoo/accounting/...`. Rewriting that URL
    would break "View your invoice" — the recipient reads link text and the URL
    never leaves the tenant's own domain.
    """
    assert odoo_branding_in(BACKEND_ROUTE) == []
    assert debrand_html(BACKEND_ROUTE, PRODUCT, attribution_html=OURS) == BACKEND_ROUTE


def test_a_domain_sample_naming_the_vendors_hosting_is_replaced():
    """The anchor's TEXT, where the link rule cannot reach it.

    `t-out` overwrites this with the tenant's real URL, so it does not reach a
    recipient — but the same rule catches a template that puts a real odoo.com
    URL in visible prose, and a sample naming a competitor's hosting has no
    business in the file either.
    """
    assert len(odoo_branding_in(DOMAIN_SAMPLE)) == 1
    out = debrand_html(DOMAIN_SAMPLE, PRODUCT, attribution_html=OURS)
    assert odoo_branding_in(out) == []
    assert "yourcompany.example.com" in out


# addons/digest/data/digest_data.xml — the digest carries TWO attributions and
# an advert for the vendor's phone app.
DIGEST_SENT_BY = (
    'Sent by <a href="https://www.odoo.com" target="_blank">'
    '<span class="odoo_link_text">Odoo</span></a>'
)
DIGEST_APP_ADVERT = (
    '<img src="https://www.odoo.com/web/image/38874595/odoo-mobile.png" alt="Odoo Mobile" />'
    '<p class="run_business">Run your business from anywhere with <b>Odoo Mobile</b>.</p>'
    '<a href="https://play.google.com/store/apps/details?id=com.odoo.mobile" target="_blank">'
    '<img class="download_app" src="https://download.odoocdn.com/digests/google_play.png" /></a>'
)


def test_the_digests_second_attribution_keeps_its_own_wording():
    """ "Sent by", not a second "Powered by".

    The digest carries both lines. Replacing this one with the attribution run
    would print "Powered by SapianERP" twice in one email.
    """
    assert len(odoo_branding_in(DIGEST_SENT_BY)) == 2
    out = debrand_html(DIGEST_SENT_BY, PRODUCT, attribution_html=OURS)
    assert odoo_branding_in(out) == []
    assert out.startswith("Sent by ")
    assert "Powered by" not in out


def test_the_vendors_app_advert_is_removed_not_renamed():
    """A client's digest must not advertise a phone app that is not theirs.

    Two of the three markers are not the word at all — a Play Store link and a
    CDN image — so a word-level scrub would leave the advert standing with our
    name on it.
    """
    out = debrand_html(DIGEST_APP_ADVERT, PRODUCT, attribution_html=OURS)
    assert odoo_branding_in(out) == []
    assert "run_business" not in out
    assert "play.google.com" not in out
    assert "odoocdn.com" not in out


def test_a_clients_own_sentence_is_left_alone():
    """The scrub is not a find-and-replace on the word.

    A client writing to their accountant about a migration keeps their
    sentence; only the branding Odoo injects into mail sent over the client's
    name is removed. This is the case that makes a blunter rule unacceptable.
    """
    theirs = "<p>Please quote for migrating our Odoo 17 database.</p>"
    assert debrand_html(theirs, PRODUCT, attribution_html=OURS) == theirs


def test_the_scrub_is_idempotent():
    once = debrand_html(INVITE_BODY, PRODUCT, attribution_html=OURS)
    assert debrand_html(once, PRODUCT, attribution_html=OURS) == once


def test_an_empty_body_is_not_an_error():
    assert debrand_html("", PRODUCT, attribution_html=OURS) == ""
    assert debrand_subject(None, PRODUCT) is None
