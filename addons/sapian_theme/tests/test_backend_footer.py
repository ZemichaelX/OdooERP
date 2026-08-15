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
    // THE WHOLE LINE, WITH ITS SPACES, in one regex. The three checks around
    // it all passed on "© 2026Sapian Technologies PLC. All Rights Reserved."
    // — which is what the footer actually rendered once our name became a
    // link, because OWL removes whitespace-only text nodes between elements.
    // Every part was present and the line was wrong.
    if (!new RegExp('© \\\\d{4} %VENDOR%\\\\. All Rights Reserved\\\\.').test(text)) {
        problems.push('the copyright line is malformed — expected '
                      + '"© <year> %VENDOR%. All Rights Reserved." in: '
                      + JSON.stringify(text));
    }
    if (!/For Support:/.test(text)) {
        problems.push('no support line in: ' + JSON.stringify(text));
    }
    // WHOSE NAME, read off the rendered strip rather than off session_info.
    // The payload assertions live in test_vendor_identity.py; what this adds
    // is that the value survives the template — a footer handed the right name
    // and printing the wrong one would satisfy every other check here.
    // Substituted by the Python side so a re-branded build asserts its own
    // name and not a stale literal.
    if (text.indexOf('%VENDOR%') === -1) {
        problems.push('the footer does not carry the vendor name %VENDOR%: '
                      + JSON.stringify(text));
    }
    if (/%TENANT%/.test(text)) {
        problems.push('the footer is signed with the TENANT: '
                      + JSON.stringify(text));
    }
    // Our name links to us. `href` rather than getAttribute so a relative or
    // empty value shows up as what the browser would actually navigate to.
    const link = footer.querySelector('.o_sapian_footer_link');
    const href = link ? link.href : '';
    if (!link) {
        problems.push('our name is not a link, so SAPIAN_URL reaches nothing');
    } else if (link.textContent.trim() !== '%VENDOR%') {
        problems.push('the link wraps ' + JSON.stringify(link.textContent.trim())
                      + ' rather than the vendor name');
    } else if (!/^https?:\\/\\/.+\\..+/.test(href)) {
        problems.push('the vendor link points at ' + JSON.stringify(href));
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

    // REMOVING THE WHOLE BAR breaks every check at once, which is a weak proof
    // for the ones added last. These two break exactly one thing each and are
    // the regressions that actually happened: the strip signed with the
    // tenant, and our name reaching the page as plain text so SAPIAN_URL was
    // read by nothing.
    const copy = footer.querySelector('.o_sapian_footer_copy');
    const keptCopy = copy.innerHTML;
    copy.textContent = '© 2026 %TENANT%. All Rights Reserved.';
    const signedTenant = sapianFooterReport();
    copy.innerHTML = keptCopy;

    const link = footer.querySelector('.o_sapian_footer_link');
    const keptClass = link.className;
    link.className = '';
    const noLink = sapianFooterReport();
    link.className = keptClass;

    const clean = sapianFooterReport();
    if (clean.problems.length) {
        console.error('SAPIAN-FOOTER-DISCRIMINATION restore failed after the '
                      + 'targeted breaks: ' + clean.problems.join('; '));
        return;
    }
    if (!signedTenant.problems.some((p) => /signed with the TENANT/.test(p))) {
        console.error('SAPIAN-FOOTER-DISCRIMINATION a footer signed with the '
                      + 'tenant passed the check: '
                      + JSON.stringify(signedTenant.problems));
        return;
    }
    if (!noLink.problems.some((p) => /not a link/.test(p))) {
        console.error('SAPIAN-FOOTER-DISCRIMINATION our name as plain text '
                      + 'passed the check: ' + JSON.stringify(noLink.problems));
        return;
    }

    console.log('SAPIAN-FOOTER-DISCRIMINATION removed -> ' + after.problems.length
                + ' problem(s); tenant-signed -> ' + signedTenant.problems.length
                + '; unlinked -> ' + noLink.problems.length
                + '; restored -> clean');
    console.log('test successful');
})();
"""


TENANT_NAME = "Golbon Trading PLC"


class FooterBrowserCase(HttpCase):
    def setUp(self):
        super().setUp()
        # Same tour problem as the rail: Odoo's onboarding tour auto-starts on
        # /odoo and clicks its way around the UI underneath the assertions.
        admin = self.env.ref("base.user_admin")
        if "tour_enabled" in admin._fields:
            admin.sudo().tour_enabled = False
        self.env["ir.config_parameter"].sudo().set_param(SUPPORT_PARAM, SUPPORT_VALUE)
        # THE TENANT IS RENAMED ON PURPOSE, to something the vendor is not.
        # Without this the "is it signed with the tenant?" assertion could pass
        # on a database whose company happened to share a word with ours, and
        # on a fresh test database the company is "My Company" — near enough to
        # nothing to be a weak negative.
        self.env.company.name = TENANT_NAME
        self.env.flush_all()

    def run_footer(self, code):
        """Substitute the two names, so nothing here hardcodes a brand.

        A literal "Sapian Technologies PLC" in the JS would keep passing after a
        re-brand while the footer said something else.
        """
        from .. import vendor

        self.browser_js(
            "/odoo",
            code.replace("%VENDOR%", vendor.SAPIAN_COMPANY).replace("%TENANT%", TENANT_NAME),
            # Must evaluate to a BOOLEAN — ChromeBrowser._wait_ready compares
            # the CDP result against {'type': 'boolean', 'value': True}
            # (odoo/tests/common.py:1877), so a bare querySelector never
            # becomes ready and the run times out looking healthy.
            "!!document.querySelector('.o_sapian_footer')",
            login="admin",
        )


@tagged("post_install", "-at_install")
class TestSapianBackendFooterRendered(FooterBrowserCase):
    browser_size = "1366x900"

    def test_the_footer_renders_on_the_backend(self):
        self.run_footer(FOOTER_RENDERS_JS)

    def test_the_footer_check_discriminates(self):
        self.run_footer(FOOTER_DISCRIMINATES_JS)


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

    def test_the_session_carries_sapian_s_own_identity(self):
        """REWRITTEN, because the contract changed by decision.

        This used to assert `sapian_support_contact` and
        `sapian_footer_company` — the TENANT's support number and the TENANT's
        company name. That was the defect: a tenant installed for Golbon
        Trading signed every backend page as Golbon's software. The footer now
        carries Sapian's, from constants a tenant cannot edit
        (`sapian_theme/vendor.py`).

        The old assertions are not deleted quietly; they are replaced by their
        opposite, and `test_vendor_identity.py` proves the tenant cannot move
        the new values.
        """
        from .. import vendor

        self.authenticate("admin", "admin")
        response = self.url_open(
            "/web/session/get_session_info",
            data="{}",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        info = response.json()["result"]
        self.assertEqual(info["sapian_vendor_company"], vendor.SAPIAN_COMPANY)
        self.assertEqual(info["sapian_vendor_support"], vendor.SAPIAN_SUPPORT)

    def test_the_tenant_setting_still_drives_the_LOGIN_page_only(self):
        """One setting, one surface — and it is no longer the backend footer.

        `sapian_theme.support_contact` is the tenant's own number. It still
        belongs on the login page, which is where a client's staff go when they
        cannot get in and where the number they need is their internal one. It
        must NOT reach the backend footer any more, and that half is the
        assertion that would have caught the regression.
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
        self.assertNotIn(
            SUPPORT_VALUE,
            (info.get("sapian_vendor_support") or ""),
            "the tenant's support number reached the backend footer",
        )
