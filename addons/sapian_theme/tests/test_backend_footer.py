# -*- coding: utf-8 -*-
"""The backend footer, asserted in a real browser.

Same reasoning as the app rail (see test_app_rail.py): it is an OWL component,
`/odoo` serves a bootstrap shell, and neither the served HTML nor the compiled
bundle can tell you whether it rendered. So this drives headless Chrome and
looks at the DOM.

`browser_js` SKIPS when no Chrome is present (odoo/tests/common.py:2153), and a
skip is a success signal produced by doing nothing. The CI job that runs these
(`rail-render` in .github/workflows/ci.yml) therefore greps the log for the
`SAPIAN-FOOTER ...` line printed from inside the page: a skipped run cannot
produce it.
"""

from odoo.tests import HttpCase, tagged

SUPPORT_PARAM = "sapian_theme.support_contact"
SUPPORT_VALUE = "+251 11 555 0000 / +251 91 555 0000"

# The check, returning problems rather than throwing, so the discrimination
# test can run the identical code against a broken DOM and watch it complain.
FOOTER_REPORT_JS = """
function sapianFooterReport() {
    const problems = [];
    const footer = document.querySelector('.o_sapian_footer');
    if (!footer) {
        problems.push('no .o_sapian_footer element in the DOM');
        return { problems, text: '', visible: false, overlaps: null };
    }
    const text = footer.innerText.trim();
    const style = getComputedStyle(footer);
    const visible = style.display !== 'none' && style.visibility !== 'hidden';
    if (!visible) {
        problems.push('the footer is in the DOM but not displayed');
    }
    if (!/©\\s*\\d{4}/.test(text)) {
        problems.push('no copyright year in: ' + JSON.stringify(text));
    }
    if (!/All Rights Reserved/i.test(text)) {
        problems.push('no rights line in: ' + JSON.stringify(text));
    }
    if (!/For Support:/.test(text)) {
        problems.push('no support line in: ' + JSON.stringify(text));
    }
    // The reservation has to match the bar, or the footer sits on top of the
    // last row of whatever is on screen. This is the rail's padding bug,
    // rotated 90 degrees.
    const client = document.querySelector('.o_web_client');
    const reserved = client ? parseFloat(getComputedStyle(client).paddingBottom) : 0;
    const height = footer.getBoundingClientRect().height;
    if (Math.abs(reserved - height) > 1) {
        problems.push('padding-bottom ' + reserved + 'px does not match the '
                      + height + 'px footer');
    }
    return { problems, text, visible, reserved, height };
}
"""

FOOTER_RENDERS_JS = FOOTER_REPORT_JS + """
(async function () {
    const report = sapianFooterReport();
    console.log('SAPIAN-FOOTER text=' + JSON.stringify(report.text)
                + ' reserved=' + report.reserved + ' height=' + report.height);
    if (report.problems.length) {
        console.error('SAPIAN-FOOTER problems: ' + report.problems.join('; '));
        return;
    }
    console.log('test successful');
})();
"""

FOOTER_DISCRIMINATES_JS = FOOTER_REPORT_JS + """
(async function () {
    // Healthy first, so a permanently-broken page cannot pass this test by
    // being broken in the way we are about to break it.
    const before = sapianFooterReport();
    if (before.problems.length) {
        console.error('SAPIAN-FOOTER-DISCRIMINATION already broken: '
                      + before.problems.join('; '));
        return;
    }
    const footer = document.querySelector('.o_sapian_footer');
    const parent = footer.parentNode;
    const next = footer.nextSibling;
    footer.remove();
    const after = sapianFooterReport();
    if (!after.problems.length) {
        console.error('SAPIAN-FOOTER-DISCRIMINATION the check passed with the '
                      + 'footer removed — it asserts nothing');
        return;
    }
    parent.insertBefore(footer, next);
    const restored = sapianFooterReport();
    if (restored.problems.length) {
        console.error('SAPIAN-FOOTER-DISCRIMINATION restore failed: '
                      + restored.problems.join('; '));
        return;
    }
    console.log('SAPIAN-FOOTER-DISCRIMINATION removed -> ' + after.problems.length
                + ' problem(s); restored -> clean');
    console.log('test successful');
})();
"""


class FooterBrowserCase(HttpCase):
    def setUp(self):
        super().setUp()
        # Same tour problem as the rail: Odoo's onboarding tour auto-starts on
        # /odoo and clicks its way around the UI underneath the assertions.
        admin = self.env.ref("base.user_admin")
        if "tour_enabled" in admin._fields:
            admin.sudo().tour_enabled = False
        self.env["ir.config_parameter"].sudo().set_param(SUPPORT_PARAM, SUPPORT_VALUE)
        self.env.flush_all()


@tagged("post_install", "-at_install")
class TestSapianBackendFooterRendered(FooterBrowserCase):
    browser_size = "1366x900"

    def test_the_footer_renders_on_the_backend(self):
        self.browser_js(
            "/odoo",
            FOOTER_RENDERS_JS,
            # Must evaluate to a BOOLEAN — ChromeBrowser._wait_ready compares
            # the CDP result against {'type': 'boolean', 'value': True}
            # (odoo/tests/common.py:1877), so a bare querySelector never
            # becomes ready and the run times out looking healthy.
            "!!document.querySelector('.o_sapian_footer')",
            login="admin",
        )

    def test_the_footer_check_discriminates(self):
        self.browser_js(
            "/odoo",
            FOOTER_DISCRIMINATES_JS,
            "!!document.querySelector('.o_sapian_footer')",
            login="admin",
        )


@tagged("post_install", "-at_install")
class TestSapianBackendFooterSmallScreen(FooterBrowserCase):
    """Below md the footer must be gone, and the space it reserved with it.

    On a phone the scarce dimension is vertical; a permanent bar costs more
    than the line is worth. This is the same failure the rail had in the other
    axis — hidden with a display utility, the element stays in the DOM and the
    `:has()` padding rule keeps reserving space for nothing.
    """

    browser_size = "375x667"

    def test_the_footer_is_absent_below_md(self):
        self.browser_js(
            "/odoo",
            """
            (function () {
                const footer = document.querySelector('.o_sapian_footer');
                const shown = footer
                    && getComputedStyle(footer).display !== 'none';
                const client = document.querySelector('.o_web_client');
                const reserved = client
                    ? parseFloat(getComputedStyle(client).paddingBottom) : 0;
                console.log('SAPIAN-FOOTER-SMALL shown=' + !!shown
                            + ' reserved=' + reserved);
                if (shown) {
                    console.error('the footer is displayed below md');
                    return;
                }
                if (reserved > 1) {
                    console.error('space is reserved for a footer that is not '
                                  + 'shown: ' + reserved + 'px');
                    return;
                }
                console.log('test successful');
            })();
            """,
            "!!document.querySelector('.o_main_navbar')",
            login="admin",
        )


@tagged("post_install", "-at_install")
class TestBackendFooterDataOverHttp(HttpCase):
    """The footer's data source, over HTTP, with no browser needed.

    It cannot prove the footer renders — the browser tests above do that — but
    it runs in every CI job rather than only the one that installs Chrome, and
    it catches the regression that would empty the bar.
    """

    def test_the_session_carries_the_support_contact_and_company(self):
        self.env["ir.config_parameter"].sudo().set_param(SUPPORT_PARAM, SUPPORT_VALUE)
        self.env.flush_all()
        self.authenticate("admin", "admin")
        response = self.url_open(
            "/web/session/get_session_info",
            data="{}",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        info = response.json()["result"]
        self.assertEqual(info["sapian_support_contact"], SUPPORT_VALUE)
        self.assertTrue(info["sapian_footer_company"], "the footer would sign nothing")

    def test_one_setting_drives_both_surfaces(self):
        """The login page and the backend footer must read the SAME parameter.

        Two settings that mean the same thing is how one of them goes stale, so
        this asserts they are literally the same key rather than that both
        happen to be configured.
        """
        self.env["ir.config_parameter"].sudo().set_param(SUPPORT_PARAM, SUPPORT_VALUE)
        self.env.flush_all()
        self.assertIn(SUPPORT_VALUE, self.url_open("/web/login").text)
        self.authenticate("admin", "admin")
        info = self.url_open(
            "/web/session/get_session_info",
            data="{}",
            headers={"Content-Type": "application/json"},
        ).json()["result"]
        self.assertEqual(info["sapian_support_contact"], SUPPORT_VALUE)
