# -*- coding: utf-8 -*-
"""The grid button opens the launcher and closes it back onto the landing page.

MEASURED IN A BROWSER, because the defect is in a click handler.

`AppsMenu.onMenuClick` has two branches, and which one runs is decided by
`user.context.is_redirect_to_home`. Everything about this fix is that the user
now has a home action, which makes web_responsive clear `is_redirect_home`
itself (its own `res_users.py:42`) and puts the button back in its plain
toggling branch. None of that is visible from Python: the only honest way to
assert "it toggles back" is to click it twice and look at what is on the screen.

TAGGED `-standard` and selected by name in CI, like the rail's browser tests:
it needs Chrome and `web_responsive`, and a job that has neither must not
silently pass it.
"""

from odoo.tests import HttpCase, tagged

TOGGLE_JS = """
const settle = (ms) => new Promise((r) => setTimeout(r, ms || 400));

async function waitFor(selector, label, timeout) {
    const deadline = Date.now() + (timeout || 20000);
    while (Date.now() < deadline) {
        if (document.querySelector(selector)) { return document.querySelector(selector); }
        await settle(150);
    }
    throw new Error('never saw ' + label + ' (' + selector + ')');
}

(async () => {
    // 1. WHERE LOGIN LANDS. The home action is the landing page, so the
    //    overview must be on screen before anything is clicked.
    const landing = await waitFor('.o_sapian_landing', 'the landing page');
    if (!/Ministry of Revenues/i.test(landing.textContent)) {
        throw new Error('the landing page rendered without its compliance section');
    }

    // 2. THE GRID BUTTON opens the launcher.
    const grid = await waitFor('.o_grid_apps_menu__button, .o_navbar_apps_menu button',
                               'the grid button');
    grid.click();
    await settle(700);
    if (!document.body.classList.contains('o_apps_menu_opened')) {
        throw new Error('the grid button did not open the launcher');
    }

    // 3. AND CLOSES IT BACK ONTO THE LANDING PAGE. This is the whole defect:
    //    before the home action existed, the second click had nothing behind
    //    the launcher to return to.
    const grid2 = document.querySelector('.o_grid_apps_menu__button, .o_navbar_apps_menu button');
    grid2.click();
    await settle(900);
    if (document.body.classList.contains('o_apps_menu_opened')) {
        throw new Error('the launcher stayed open — the grid button still goes one way');
    }
    if (!document.querySelector('.o_sapian_landing')) {
        throw new Error('the launcher closed onto something that is not the landing page');
    }
    console.log('SAPIAN-GRID toggled=2 landed=overview');
    console.log('test successful');
})();
"""


@tagged("post_install", "-at_install", "-standard", "sapian_grid")
class TestGridTogglesBackToTheLanding(HttpCase):
    def test_the_grid_button_toggles_back_to_the_landing_page(self):
        admin = self.env.ref("base.user_admin")
        action = self.env["res.users"]._sapian_landing_action()
        self.assertTrue(action, "the landing action is missing")
        admin.sudo().write({"action_id": action.id})
        # web_responsive clears this itself on write; asserted rather than
        # assumed, because the whole fix rests on it.
        if "is_redirect_home" in admin._fields:
            self.assertFalse(
                admin.is_redirect_home,
                "web_responsive did not clear is_redirect_home, so the grid "
                "button will still take its one-way branch",
            )
        self.browser_js("/odoo", TOGGLE_JS, "web.Chrome", login="admin", timeout=120)
