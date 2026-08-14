# -*- coding: utf-8 -*-
"""Guards for the brand identity.

Each test here encodes an assumption that is currently true and would fail
silently if it stopped being true. Prose in a README does not fire when an
assumption expires.
"""

import re
from pathlib import Path

from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.sapian_theme import brand
from odoo.addons.sapian_theme.report_render import (
    ReportAssetsUnreachable,
    assert_report_assets_reachable,
)

MODULE_ROOT = Path(brand.__file__).parent
PALETTE_FILE = MODULE_ROOT / "static" / "src" / "scss" / "sapian_variables.scss"

# A colour literal: # followed by exactly 3 or 6 hex digits, not part of a
# longer token. Deliberately does NOT match format strings like "#%02X%02X%02X"
# or the character class "#[0-9A-Fa-f]{6}" inside brand.py's own regex.
HEX_LITERAL = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b")


@tagged("post_install", "-at_install")
class TestSapianTheme(TransactionCase):

    # ---- the palette is genuinely a single source ------------------------

    def test_brand_is_read_from_the_scss_file(self):
        """Python does not restate the colour, it reads the one declaration."""
        declared = HEX_LITERAL.search(
            re.search(
                r"\$sapian-brand\s*:\s*(#[0-9A-Fa-f]{6})", PALETTE_FILE.read_text()
            ).group(0)
        ).group(0)
        self.assertEqual(brand.brand_primary(), declared.upper())

    def test_the_mark_takes_its_colour_from_the_palette(self):
        """No hex in the mark, and no way for it to acquire one.

        `fill="currentColor"` is what lets the same file be brand-coloured on
        the login page and in the backend footer without a second definition of
        the colour — and it is why the hex guard below needs no exemption for
        it.
        """
        inline = (MODULE_ROOT / "views" / "sapian_mark.xml").read_text()
        self.assertIn('fill="currentColor"', inline)
        self.assertNotRegex(inline, HEX_LITERAL.pattern)

    def test_no_raw_hex_outside_palette(self):
        """The one-edit property, enforced.

        If a hex literal appears anywhere else in the module, re-branding
        silently becomes a find-and-replace and this module's central promise
        is broken.

        Two exemptions, both deliberate:
        - Markdown: the README quotes measured contrast figures, which are data
          *about* the colour, not a second definition of it.
        - This tests/ directory: proving a client's colour is never overwritten
          requires a colour that is NOT the brand, so arbitrary fixture hexes
          are the point rather than a violation.
        """
        offenders = []
        for path in sorted(MODULE_ROOT.rglob("*")):
            if not path.is_file() or path.suffix in (".md", ".pyc"):
                continue
            if path == PALETTE_FILE or "__pycache__" in path.parts:
                continue
            if "tests" in path.relative_to(MODULE_ROOT).parts:
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
            ):
                for match in HEX_LITERAL.finditer(line):
                    offenders.append(
                        "%s:%d %s" % (path.relative_to(MODULE_ROOT), lineno, match.group(0))
                    )
        self.assertFalse(
            offenders,
            "Raw colour literals outside the palette file — re-branding is no "
            "longer one edit:\n  " + "\n  ".join(offenders),
        )

    def test_python_derivation_matches_the_scss_recipe(self):
        """The Python and SCSS derivations must not drift apart.

        The document's secondary colour and the interface hover state are meant
        to be one colour computed in two languages. If they diverge a company
        prints one teal while the UI shows another.
        """
        # The two primitives, against hand-computed values.
        self.assertEqual(brand.shade("#C0FFEE", 0.15), "#A3D9CA")
        self.assertEqual(brand.tint("#C0FFEE", 0.15), "#C9FFF1")
        # The luminance-aware branch, both ways round.
        self.assertTrue(brand.is_dark("#14454F"), "deep teal must take the dark branch")
        self.assertFalse(brand.is_dark("#C416D3"), "mid magenta must take the light branch")
        primary = brand.brand_primary()
        expected = brand.tint(primary) if brand.is_dark(primary) else brand.shade(primary)
        self.assertEqual(brand.brand_secondary(), expected)

    def test_the_rule_still_reproduces_the_previous_brand(self):
        """A general rule, not a special case for teal.

        The luminance-aware derivation must give the previously-approved value
        for the previous brand. If a future edit breaks this, the rule has
        stopped being general and has become tuned to one colour.
        """
        magenta = "#C416D3"
        self.assertEqual(brand.shade(magenta), "#A713B3")
        self.assertFalse(brand.is_dark(magenta))

    def test_a_dark_brand_hover_is_actually_visible(self):
        """The defect the rule exists to prevent, stated as a number.

        Darkening #14454F moves HSL lightness by under 3 points — a hover a
        user cannot see, which reads as disabled. Lightening moves it by more
        than 10.
        """
        primary = brand.brand_primary()
        base = brand.hsl_lightness(primary)
        darker = brand.hsl_lightness(brand.shade(primary))
        lighter = brand.hsl_lightness(brand.tint(primary))
        self.assertLess(
            abs(base - darker), 5.0, "shading a dark brand should be near-invisible"
        )
        self.assertGreater(lighter - base, 8.0, "the chosen hover must be plainly visible")
        self.assertEqual(brand.brand_secondary(), brand.tint(primary))

    # ---- the dark-mode assumption ----------------------------------------

    def test_color_scheme_is_light_on_this_stack(self):
        """Odoo 19 Community hardcodes the light scheme — assumption encoded.

        web/models/ir_http.py:72 is `def color_scheme(self): return "light"`,
        with no override anywhere in Community and no web_enterprise installed,
        so the dark asset bundle is compiled and never served. On that basis
        this module ships NO dark-mode variant.

        The brand fails WCAG AA as ink on every plausible dark surface
        (3.23:1 on Bootstrap's $gray-900, 2.41:1 on $gray-800). If this test
        fails, dark mode has become reachable and those numbers are live rather
        than hypothetical: apply the fix recorded in README.md under
        "If dark mode ever becomes reachable".
        """
        self.assertEqual(
            self.env["ir.http"].color_scheme(),
            "light",
            "Dark mode is now reachable on this stack. The brand is unreadable "
            "as ink on dark surfaces — see README.md, 'If dark mode ever "
            "becomes reachable', for the derived variant to apply.",
        )

    # ---- the company-colour contract -------------------------------------

    def test_new_company_gets_the_brand(self):
        company = self.env["res.company"].create({"name": "Theme Default Co"})
        self.assertEqual(company.primary_color, brand.brand_primary())
        self.assertEqual(company.secondary_color, brand.brand_secondary())

    def test_a_chosen_colour_is_never_overwritten(self):
        """A white-label client keeps their colour — on create and on re-run."""
        company = self.env["res.company"].create(
            {
                "name": "White Label Co",
                "primary_color": "#0057B8",
                "secondary_color": "#003C7E",
            }
        )
        self.assertEqual(company.primary_color, "#0057B8")
        # The install-time backfill must leave it alone too.
        changed = self.env["res.company"]._sapian_apply_brand_defaults()
        self.assertNotIn(company, changed)
        self.assertEqual(company.primary_color, "#0057B8")
        self.assertEqual(company.secondary_color, "#003C7E")

    # ---- the default report layout ---------------------------------------

    def test_new_company_gets_the_house_layout_and_is_marked(self):
        company = self.env["res.company"].create({"name": "Layout Default Co"})
        self.assertEqual(company.external_report_layout_id.key, "web.external_layout_boxed")
        self.assertEqual(company.sapian_layout_applied, "web.external_layout_boxed")

    def test_a_chosen_layout_is_never_overridden_and_carries_no_marker(self):
        """Same rule as the colour: supplied means theirs, and unmarked."""
        wave = self.env.ref("web.external_layout_wave")
        company = self.env["res.company"].create(
            {"name": "Own Layout Co", "external_report_layout_id": wave.id}
        )
        self.assertEqual(company.external_report_layout_id, wave)
        self.assertFalse(
            company.sapian_layout_applied,
            "a layout we did not choose must not be marked as ours",
        )

    def test_existing_companies_keep_their_layout(self):
        """The default is for NEW companies only — nothing back-fills a layout.

        Nothing in this module writes external_report_layout_id outside create(),
        so a company that predates the theme keeps whatever it had, including
        no layout at all.
        """
        company = self.env["res.company"].create({"name": "Pre-existing Co"})
        company.write({"external_report_layout_id": False, "sapian_layout_applied": False})
        self.env["res.company"]._sapian_detect_brand_drift()
        self.env["res.company"]._sapian_apply_brand(dry_run=False)
        self.env["res.company"]._sapian_apply_brand_defaults()
        self.assertFalse(
            company.external_report_layout_id,
            "no code path may set a layout on an existing company",
        )

    # ---- re-brand drift: detect loudly, change nothing ---------------------

    def _fake_old_brand(self, company, primary="#0B6E4F", secondary="#095E43"):
        """Put a company in the state a PAST re-brand would have left it in."""
        company.write(
            {
                "primary_color": primary,
                "secondary_color": secondary,
                "sapian_brand_applied": "%s|%s" % (primary, secondary),
            }
        )
        return company

    def test_drift_is_detected_but_nothing_is_written(self):
        """Update-time detection must be read-only. This is the whole point."""
        company = self._fake_old_brand(
            self.env["res.company"].create({"name": "Stale Brand Co"})
        )
        drifted = self.env["res.company"]._sapian_detect_brand_drift()
        self.assertIn(company, drifted)
        self.assertEqual(
            company.primary_color, "#0B6E4F", "detection must never rewrite a colour"
        )
        self.assertEqual(company.secondary_color, "#095E43")

    def test_dry_run_is_the_default_and_writes_nothing(self):
        company = self._fake_old_brand(self.env["res.company"].create({"name": "Dry Run Co"}))
        affected = self.env["res.company"]._sapian_apply_brand()  # no argument
        self.assertIn(company, affected, "a dry run still reports what it would do")
        self.assertEqual(company.primary_color, "#0B6E4F", "dry run must not write")

    def test_explicit_apply_moves_both_halves_together(self):
        company = self._fake_old_brand(self.env["res.company"].create({"name": "Apply Co"}))
        self.env["res.company"]._sapian_apply_brand(dry_run=False)
        self.assertEqual(company.primary_color, brand.brand_primary())
        self.assertEqual(company.secondary_color, brand.brand_secondary())
        self.assertEqual(
            company.sapian_brand_applied,
            "%s|%s" % (brand.brand_primary(), brand.brand_secondary()),
        )
        # Idempotent: a second run finds nothing left to do.
        self.assertFalse(self.env["res.company"]._sapian_apply_brand(dry_run=False))

    def test_a_client_colour_is_never_seen_as_drift(self):
        """No marker means not ours — the case the marker exists to protect."""
        company = self.env["res.company"].create(
            {"name": "Chose Their Own Co", "primary_color": "#0057B8"}
        )
        self.assertFalse(company.sapian_brand_applied, "a supplied colour must carry no marker")
        self.assertNotIn(company, self.env["res.company"]._sapian_detect_brand_drift())
        self.env["res.company"]._sapian_apply_brand(dry_run=False)
        self.assertEqual(company.primary_color, "#0057B8")

    def test_a_half_edited_pair_is_left_alone(self):
        """Somebody has taken ownership; guessing which half they meant is how
        a document ends up in two brands."""
        company = self._fake_old_brand(
            self.env["res.company"].create({"name": "Half Edited Co"})
        )
        company.primary_color = "#0057B8"  # hand-edited, secondary untouched
        self.assertNotIn(company, self.env["res.company"]._sapian_detect_brand_drift())
        self.env["res.company"]._sapian_apply_brand(dry_run=False)
        self.assertEqual(company.primary_color, "#0057B8", "must not be rewritten")
        self.assertEqual(company.secondary_color, "#095E43", "must not be half-synced")

    def test_backfill_only_fills_empties_and_reports_what_it_did(self):
        """A do-nothing run must be distinguishable from a working one."""
        company = self.env["res.company"].create({"name": "Colourless Co"})
        company.write({"primary_color": False, "secondary_color": False})
        changed = self.env["res.company"]._sapian_apply_brand_defaults()
        self.assertIn(company, changed, "the empty company should have been filled")
        self.assertEqual(company.primary_color, brand.brand_primary())
        # Second run changes nothing: idempotent, and says so.
        self.assertNotIn(company, self.env["res.company"]._sapian_apply_brand_defaults())


@tagged("post_install", "-at_install")
class TestSapianThemeLogin(HttpCase):
    """The login page, fetched over HTTP rather than rendered directly.

    `web.login` uses `request` itself (the CSRF token, among others), so it
    cannot be rendered in a TransactionCase at all — the failure is in Odoo's
    template, not ours. Fetching the real URL is both the only way to test it
    and better evidence: it exercises the page a user actually gets.
    """

    def _login_page(self):
        response = self.url_open("/web/login")
        self.assertEqual(response.status_code, 200)
        return response.text

    def test_login_page_degrades_without_a_logo(self):
        """No broken image and no stock Odoo placeholder when no logo is set."""
        company = self.env["res.company"].search([], order="id", limit=1)
        company.logo = False
        self.env.flush_all()
        html = self._login_page()
        self.assertNotIn(
            "/web/binary/company_logo", html, "logo <img> rendered with no logo set"
        )
        self.assertIn(company.name, html, "company name should stand in for the logo")

    def test_login_page_shows_the_logo_when_there_is_one(self):
        """The other half — the guard must not hide a logo that exists."""
        company = self.env["res.company"].search([], order="id", limit=1)
        # 1x1 transparent GIF, the smallest thing that is a real image.
        company.logo = b"R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        self.env.flush_all()
        self.assertIn("/web/binary/company_logo", self._login_page())

    def test_support_contact_empty_renders_nothing(self):
        self.env["ir.config_parameter"].sudo().set_param("sapian_theme.support_contact", "")
        self.env.flush_all()
        self.assertNotIn(
            "Support:", self._login_page(), "an empty support contact must render nothing"
        )

    def test_support_contact_is_configurable(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sapian_theme.support_contact", "+251 91 234 5678"
        )
        self.env.flush_all()
        html = self._login_page()
        self.assertIn("+251 91 234 5678", html)
        self.assertIn("Support:", html)


@tagged("post_install", "-at_install")
class TestReportAssetGuard(HttpCase):
    """The guard that makes a silently-unstyled PDF impossible to produce.

    HttpCase because the whole point is a live server: the guard must PASS when
    one is reachable and FAIL when it is not, and only a real server can
    demonstrate the first half.
    """

    def test_guard_passes_when_the_server_is_reachable(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "http://127.0.0.1:%d" % self.http_port()
        )
        self.assertTrue(assert_report_assets_reachable(self.env))

    def test_guard_fails_when_nothing_is_listening(self):
        """The discrimination proof: make the bad thing happen on purpose.

        Port 1 is reserved and nothing listens there, which is exactly the
        state a `docker compose run --rm` container is in. An untested guard is
        one more thing that passes by doing nothing.
        """
        self.env["ir.config_parameter"].sudo().set_param("web.base.url", "http://127.0.0.1:1")
        with self.assertRaises(ReportAssetsUnreachable) as caught:
            assert_report_assets_reachable(self.env, timeout=2)
        message = str(caught.exception)
        self.assertIn("silently UNSTYLED", message, "the error must name the consequence")
        self.assertIn("web.base.url", message, "the error must name the cause")
        self.assertIn("docker compose", message, "the error must name the usual fix")

    def test_guard_fails_when_base_url_is_empty(self):
        self.env["ir.config_parameter"].sudo().set_param("web.base.url", "")
        with self.assertRaises(ReportAssetsUnreachable):
            assert_report_assets_reachable(self.env, timeout=2)


@tagged("post_install", "-at_install")
class TestLoginPageIsActuallyBranded(HttpCase):
    """Assert what the BROWSER RECEIVES, not what the SCSS source says.

    The gap between those two is exactly where this defect hid. The palette
    file said teal, `web.assets_frontend` contained the string "#14454F" seven
    times, and the login button still rendered Odoo purple — because
    `.btn-primary` is generated from Bootstrap's $theme-colors MAP, which
    `html_editor` (auto_install:True) rebuilds from the website editor's
    palette in web._assets_frontend_helpers. $o-brand-primary is never
    consulted on the frontend at all.

    A source-file assertion would have passed throughout. This one fetches the
    login page, follows its stylesheet link, and looks at the rule that styles
    the button.
    """

    def _served_login_css(self):
        page = self.url_open("/web/login")
        self.assertEqual(page.status_code, 200)
        hrefs = re.findall(r'href="([^"]+web\.assets_frontend[^"]*\.css)"', page.text)
        self.assertTrue(hrefs, "the login page must link a frontend stylesheet")
        css = self.url_open(hrefs[0])
        self.assertEqual(css.status_code, 200, "the login stylesheet must be served")
        self.assertGreater(len(css.text), 1024, "an empty stylesheet styles nothing")
        return css.text

    def test_served_login_stylesheet_brands_the_sign_in_button(self):
        css = self._served_login_css()
        primary = brand.brand_primary()
        rules = re.findall(r"\.oe_login_form \.btn-primary\{[^}]*\}", css)
        self.assertTrue(
            rules,
            "no .oe_login_form .btn-primary rule in the served CSS — the login "
            "button is falling back to Odoo's own palette. See "
            "sapian_theme/static/src/scss/sapian_frontend.scss for why this "
            "rule is needed and cannot come from $o-brand-primary.",
        )
        joined = " ".join(rules)
        self.assertIn(
            primary.upper(),
            joined.upper(),
            "the sign-in button is not the brand colour in the CSS the browser "
            "is actually served: %s" % joined[:200],
        )

    def test_served_login_stylesheet_uses_the_derived_hover(self):
        """The hover must move with the brand, from the same single source."""
        css = self._served_login_css()
        rules = " ".join(re.findall(r"\.oe_login_form \.btn-primary\{[^}]*\}", css))
        self.assertIn(brand.brand_secondary().upper(), rules.upper())
