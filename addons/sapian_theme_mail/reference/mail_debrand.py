# -*- coding: utf-8 -*-
"""Take another vendor's name out of the client's outgoing email.

PLAIN PYTHON, AND THAT IS THE POINT (CLAUDE.md rule 10). Every decision here is
string work on rendered HTML, so it is testable without a database, without a
mail server and without an Odoo registry — and `test_mail_debrand.py` beside it
runs in milliseconds against the exact upstream markup, quoted verbatim.

WHY A SEND-TIME SCRUB AND NOT TEN TEMPLATE OVERRIDES
----------------------------------------------------
The two notification LAYOUTS were fixed by xpath, because they are QWeb
templates and inheritance is exact. Most of the rest are not:

  * `mail.template` RECORDS cannot be xpath-inherited. Overriding one means
    copying upstream's entire `body_html` into this repository, where it rots
    silently on the next Odoo release — and it means doing that once per
    template, in a bridge module per upstream module, for modules a given
    tenant may or may not have.
  * The set is not closed. A measured sweep of the 83 modules our catalogue
    reaches found ELEVEN more surfaces carrying Odoo branding. The next Odoo
    version, an optional module nobody enumerated, or a template a client
    writes by copying an Odoo one, all reintroduce it.

`mail.mail._prepare_outgoing_body` is the last point every outgoing email
passes through, whatever produced it — upstream's own documentation for that
method is "to be inherited to add custom content depending on some module". A
scrub there cannot be bypassed by a template nobody thought of.

WHAT IS AND IS NOT REMOVED
--------------------------
This does NOT delete every occurrence of the word. A client writing to their
accountant about an Odoo migration must keep their sentence, and a scrub that
mangles a user's own prose is worse than the defect. What is removed is the
BRANDING Odoo injects into mail sent over the client's name:

  1. the "Powered by <a href=odoo.com>Odoo</a>" attribution, replaced by our
     line or by nothing (`sapian_email_attribution`);
  2. any other odoo.com link, which in practice is marketing — the tour link;
  3. Odoo's logo image, which `account` puts at the head of two finance mails;
  4. a SHORT, EXPLICIT list of upstream phrases that are branding rather than
     attribution, each one commented with the template it comes from.

Rule 4 is the part that can rot: if Odoo rewords a sentence, the rule stops
matching. That is why the guard asserts the POSITIVE — zero branding in the
rendered output of every template in the database — instead of asserting that
these rules ran. A reworded sentence then fails a test rather than shipping.
"""

import re

# ---- what we are looking for ----------------------------------------------

# An <a> whose href points at odoo.com, and the "Powered by" that precedes it
# in every layout upstream ships. The words sit OUTSIDE the anchor, so removing
# the anchor alone leaves a dangling "Powered by" — the same trap the layout
# xpath documents.
_ATTRIBUTION = re.compile(
    r"Powered\s+by\s*<a\b[^>]*href=[\"'][^\"']*odoo\.com[^\"']*[\"'][^>]*>.*?</a>",
    re.I | re.S,
)

# Any remaining odoo.com anchor: the tour link, a domain sample, a footer link
# in a template we have not seen. Unwrapped to its own text rather than
# deleted, so a sentence that merely LINKS somewhere keeps reading correctly;
# the text itself is then handled by the phrase rules if it names the vendor.
_ANY_ODOO_LINK = re.compile(
    r"<a\b[^>]*href=[\"'][^\"']*odoo\.com[^\"']*[\"'][^>]*>(.*?)</a>",
    re.I | re.S,
)

# Odoo's own logo file, however it is attributed. `account` puts this at the
# head of the e-invoice notification and the journal notification — an actual
# competitor logo on a finance email, which is a stronger claim than the words.
_LOGO_IMG = re.compile(
    r"<img\b[^>]*src=[\"'][^\"']*/web/static/img/logo[^\"']*[\"'][^>]*/?>",
    re.I,
)

# A last resort for detection, never for rewriting: the word on its own.
_WORD = re.compile(r"\bOdoo\b", re.I)

#: Where our own logo lives, as an absolute path the mail client can resolve
#: once Odoo has run `_replace_local_links` over the body.
SAPIAN_LOGO_SRC = "/sapian_theme/static/src/img/sapian_logo.png"


def _phrase_rules(product):
    """Ordered (pattern, replacement) pairs for prose that names the vendor.

    Each is quoted from the template it appears in, so a reader can check it
    against upstream rather than trusting this list. Order matters: the longest
    and most specific run first, because the shorter ones are substrings of it.
    """
    return [
        # auth_signup.set_password_email — a paragraph of competitor marketing
        # in the mail that invites the client's OWN STAFF to their OWN system.
        # Deleted rather than reworded: there is no version of "Never heard of
        # us? 12+ million users love us" that belongs in that email.
        (
            re.compile(
                r"Never heard of Odoo\?.*?(?=<br\s*/?>|</)",
                re.I | re.S,
            ),
            "",
        ),
        (
            re.compile(
                r"Have a look at the\s*Odoo Tour\s*to discover the tool\.",
                re.I | re.S,
            ),
            "",
        ),
        # The remaining named mentions, in the same template.
        (re.compile(r"\bWelcome to Odoo\b", re.I), "Welcome to %s" % product),
        (re.compile(r"\bEnjoy Odoo!", re.I), "Enjoy %s!" % product),
        (re.compile(r"\bto connect on Odoo\b", re.I), "to connect on %s" % product),
        (re.compile(r"\bYour Odoo domain is\b", re.I), "Your %s address is" % product),
        # calendar.calendar_template_meeting_* — the label of the video-call
        # service, shown to whoever was invited, including a customer.
        (re.compile(r"\bOdoo Discuss\b", re.I), "%s Discuss" % product),
        # auth_signup.set_password_email subject line.
        (re.compile(r"\bconnect to Odoo\b", re.I), "connect to %s" % product),
    ]


def debrand_html(html, product, attribution_html=None, logo_src=SAPIAN_LOGO_SRC):
    """Return ``html`` with the other vendor's branding replaced.

    :param str html: a RENDERED email body. Rendered, not template source:
        upstream hides the attribution behind ``show_footer``, so scrubbing the
        source would report a clean email that still mails the footer.
    :param str product: our product name, for the phrase rules.
    :param attribution_html: the full replacement for the attribution run —
        ``None`` removes it outright, which is what a company that switched the
        line off has asked for. It never falls back to another vendor's name.
    :param str logo_src: what Odoo's logo image becomes.
    :returns: the scrubbed body.
    """
    if not html:
        return html

    out = _ATTRIBUTION.sub(lambda m: attribution_html or "", html)
    out = _LOGO_IMG.sub(
        '<img alt="%s" src="%s" style="height: 2em; object-fit: contain;"/>'
        % (product, logo_src),
        out,
    )
    # Unwrap before the phrase rules run: "Odoo Tour" is inside an anchor, and
    # the rule that deletes that sentence matches the TEXT.
    out = _ANY_ODOO_LINK.sub(lambda m: m.group(1), out)
    for pattern, replacement in _phrase_rules(product):
        out = pattern.sub(replacement, out)
    return out


def debrand_subject(subject, product):
    """Same rules, applied to a subject line.

    Separate from the body because `mail.mail` carries the two apart, and
    because a subject has no markup: only the phrase rules can apply.
    """
    if not subject:
        return subject
    out = subject
    for pattern, replacement in _phrase_rules(product):
        out = pattern.sub(replacement, out)
    return out


def odoo_branding_in(text):
    """Every remaining mention of the other vendor, as a list of snippets.

    THE GUARD'S EYES, and deliberately blunter than the rewriting rules: it
    reports the bare word and any odoo.com URL, so a phrase nobody wrote a rule
    for still fails a test. Returns snippets rather than a count so a failure
    names what it found.
    """
    if not text:
        return []
    found, url_spans = [], []
    for match in re.finditer(r"[^\s\"\'<>]*odoo\.com[^\s\"\'<>]*", text, re.I):
        url_spans.append((match.start(), match.end()))
        found.append((match.start(), match.group(0)))
    for match in _WORD.finditer(text):
        # A URL already reported is not reported twice. `\bOdoo\b` matches
        # INSIDE "www.odoo.com" — the dots are word boundaries — so without
        # this every link would count as two findings and the counts in the
        # goldens would mean nothing.
        if any(s <= match.start() < e for s, e in url_spans):
            continue
        start = max(0, match.start() - 40)
        found.append((match.start(), text[start : match.end() + 20].strip()))
    return [snippet for _, snippet in sorted(found)]
