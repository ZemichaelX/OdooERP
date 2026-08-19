# -*- coding: utf-8 -*-
"""The login verifier greps for a selector the stylesheet actually emits.

WHY THIS TEST EXISTS
--------------------
`scripts/lib/check_login_page.py` reads the sign-in button's colours out of the
compiled `web.assets_frontend` bundle by matching one CSS rule. PR #47 widened
that rule's scope from `.oe_login_form` (the login form) to `.o_sapian_auth`
(every auth page, because /web/reset_password was keeping the website palette).
The verifier was not changed with it.

Nothing failed. The grep matched nothing, `first()` returned "ABSENT", and every
build_demo.sh and provision_client.sh run since reported

    CHECK login_primary=ABSENT
    CHECK login_disabled=ABSENT
    CHECK login_focus_rgb=ABSENT

on a login page whose button was correctly `#14454F`. Measured on a 233-module
database and a launcher-only one, identically:

    login_selector_oe_login_form=0
    login_selector_o_sapian_auth=1

An operator read those three lines as a branding regression and spent an evening
on it. That is a check reporting a failure it produced by looking in the wrong
place — the same family as a success signal that can be produced by doing
nothing, and it stays undetected for exactly as long because a stale grep and a
missing rule are indistinguishable in the output.

Re-pointing the grep fixes today and not tomorrow: the scope can be renamed
again. So the two are tied together here, in a test that needs no Odoo, no
database and no compiled bundle — it reads both files as text.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "lib" / "check_login_page.py"
SCSS = ROOT / "addons" / "sapian_theme" / "static" / "src" / "scss" / "sapian_frontend.scss"

# The custom properties the verifier reads out of that rule. Each one is a
# button STATE that has been wrong in production before: the resting colour,
# the colour while the login request is in flight (login.js adds `disabled`),
# and the focus ring.
REQUIRED_PROPERTIES = ("--btn-bg", "--btn-disabled-bg", "--btn-focus-shadow-rgb")


def declared_scope():
    """The scope constant the verifier greps for."""
    match = re.search(r'^LOGIN_RULE_SCOPE = "([^"]+)"', CHECK.read_text(encoding="utf-8"), re.M)
    assert match, "check_login_page.py no longer declares LOGIN_RULE_SCOPE"
    return match.group(1)


def scss_source():
    return SCSS.read_text(encoding="utf-8")


def test_the_verifier_greps_for_a_scope_the_stylesheet_declares():
    scope = declared_scope()
    source = scss_source()
    # Comments in this file discuss the OLD scope by name, so the selector is
    # required as a rule opener rather than as a substring — otherwise the
    # history lesson in the header would satisfy the test.
    opener = re.compile(r"^\s*%s\s*\{" % re.escape(scope), re.M)
    assert opener.search(source), (
        "check_login_page.py greps for %r but sapian_frontend.scss does not open a rule "
        "with it. That is how the three login-colour checks became a permanent "
        "ABSENT: the stylesheet was rescoped and the verifier was not." % scope
    )


def test_the_scope_actually_styles_the_sign_in_button():
    source = scss_source()
    assert ".btn-primary" in source, (
        "sapian_frontend.scss no longer styles .btn-primary, so the rule the login "
        "verifier reads cannot exist in the compiled bundle."
    )


def test_every_button_state_the_verifier_reads_is_set():
    """Each property must be DECLARED, not merely mentioned.

    Caught while proving this test discriminates: renaming
    `--btn-focus-shadow-rgb:` in the rule left the test green, because the
    file's own header quotes the property while explaining why it matters. A
    substring check that a comment can satisfy is a check that passes by doing
    nothing, so the declaration is required at the start of a line.
    """
    source = scss_source()
    missing = [
        prop
        for prop in REQUIRED_PROPERTIES
        if not re.search(r"^\s*%s:" % re.escape(prop), source, re.M)
    ]
    assert not missing, (
        "sapian_frontend.scss does not set %s. check_login_page.py reads %s out of "
        "the compiled rule, so each missing one becomes an ABSENT that reads as a "
        "branding failure." % (", ".join(missing), ", ".join(REQUIRED_PROPERTIES))
    )


def test_the_superseded_scope_is_not_grepped_for():
    """The specific mistake, named, so it cannot be reintroduced by a revert."""
    scope = declared_scope()
    assert scope != ".oe_login_form", (
        "check_login_page.py is back to grepping for .oe_login_form, which the "
        "stylesheet stopped emitting in PR #47. Every login-colour check will "
        "report ABSENT on a correctly branded page."
    )
