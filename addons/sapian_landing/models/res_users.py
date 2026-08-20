# -*- coding: utf-8 -*-
"""Where a person lands, and what the grid button does when they click it twice.

ONE CHANGE, BOTH SYMPTOMS
-------------------------
"Logging in lands on an admin list" and "the grid button goes one way" are the
same defect seen from two ends, and web_responsive's own model says why:

    vendor/oca_web/web_responsive/models/res_users.py:42
        self.filtered("action_id").is_redirect_home = False

`is_redirect_home = True` with NO home action is what `sapian_theme` sets today,
and it is what makes the launcher the landing surface. In that mode the grid
button does not toggle — `AppsMenu.onMenuClick` takes its `is_redirect_to_home`
branch, which juggles a `redirect_menuId` in localStorage and rewrites the URL,
so clicking it again does not bring you back to anything. There is nothing
behind the launcher to come back TO.

Giving the user a home action fixes both at once. Login opens it, and the grid
button falls back into its plain branch — `setOpenState(!this.state.open)` —
which opens the launcher over the page and closes it back onto the page. The
"toggle back to the landing page" is web_responsive's own behaviour, uncovered
rather than patched, which is the only kind of change allowed against a
vendored tree pinned by hash.

WHY NOT EDIT sapian_theme'S DEFAULTS
------------------------------------
`sapian_theme` must install on a database carrying no other product module, and
its own manifest and a CI job say so. The landing action does not exist there.
So the theme keeps setting the launcher as the landing surface, which is right
for a tenant that has only the theme, and THIS module — which by definition has
the page — moves users onto it.
"""

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def default_get(self, fields_list):
        """A new user lands on the overview."""
        defaults = super().default_get(fields_list)
        if "action_id" in fields_list and not defaults.get("action_id"):
            action = self._sapian_landing_action()
            if action:
                defaults["action_id"] = action.id
        return defaults

    @api.model
    def _sapian_landing_action(self):
        return self.env.ref("sapian_landing.action_sapian_landing", raise_if_not_found=False)

    @api.model
    def _sapian_apply_landing_home(self, dry_run=True):
        """Put EXISTING users on the landing page. A provisioning step.

        The same shape as `sapian_theme._sapian_apply_launcher_defaults`, and
        for the same reason: `default_get` reaches users that do not exist yet,
        and every user of every tenant we have already provisioned does. Not a
        migration and not called on install — an operator invokes it, it
        defaults to a dry run, and it only moves users that have NO home action
        of their own, because a user who chose one has chosen one.

        Returns the users it moved, so the caller can log a number.
        """
        action = self._sapian_landing_action()
        if not action:
            _logger.error("sapian_landing: the landing action is missing, so no user was moved")
            return self.browse()
        candidates = self.sudo().search([("action_id", "=", False), ("share", "=", False)])
        if dry_run:
            _logger.info(
                "sapian_landing: DRY RUN — %d user(s) would land on the overview. "
                "Re-run with dry_run=False to apply.",
                len(candidates),
            )
            return candidates
        candidates.write({"action_id": action.id})
        _logger.info("sapian_landing: %d user(s) now land on the overview", len(candidates))
        return candidates
