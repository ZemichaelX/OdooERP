# -*- coding: utf-8 -*-
"""Brand defaults for the printed-document colour system.

Odoo's external report layouts read ``primary_color``/``secondary_color`` off
the company as data. We set the house brand as the DEFAULT for companies that
have expressed no preference, and never touch one that has.

The hard part is what happens LATER. A company row stores a *copy* of the
colour, so after a re-brand an old house colour and a client's deliberate
choice look identical — both are "a colour that is not the current brand".
``sapian_brand_applied`` is the marker that tells them apart: it holds
the pair we last wrote, so drift can be detected without guessing.
"""

import base64
import logging

from odoo import api, fields, models
from odoo.tools import file_open

from .. import brand

_logger = logging.getLogger(__name__)


# ---- The default company logo ---------------------------------------------
#
# WHY A MODEL AND NOT A DATA FILE
# -------------------------------
# The logo lives on a `res.company` RECORD, not in a file, so it has exactly the
# install-versus-upgrade problem the bot's name had (see
# `sapian_theme_mail/models/res_partner.py`): a `<record>` in a data file reaches
# a database being created and never reaches one being upgraded, and a company
# created after install — a second company, a new tenant — gets whatever Odoo's
# column default says.
#
# THE FAVICON IS NOT HERE, AND THAT IS THE CORRECTION
# ---------------------------------------------------
# It was, and it could not be: `res.company` HAS NO `favicon` FIELD in Odoo 19.
# `logo`, `uses_default_logo` and `primary_color` are on `base`'s res.company;
# the favicon is a field of the `website` MODEL. Writing one here raised
# `AttributeError: 'res.company' object has no attribute 'favicon'` inside
# `post_init_hook`, which fails the registry load, which is why every CI job
# that installs this module died in the same eighty seconds.
#
# The browser tab is branded by `views/favicon.xml` instead — a view inheriting
# `web.layout`, which reaches install and upgrade by the same route and needs
# neither a hook nor a migration.
#
# THE LOGO IS THEIRS, AND DELIBERATELY WEAKER THAN A BRAND CONSTANT
# -----------------------------------------------------------------
# It goes on their invoices, and the onboarding wizard exists to collect it. So
# it is only ever written while the company still carries Odoo's stock image,
# and the wizard's upload always wins. `uses_default_logo` is Odoo's own flag
# for "nobody has chosen one".
#
LOGO = "sapian_theme/static/src/img/sapian_logo.png"


class ResCompany(models.Model):
    _inherit = "res.company"

    sapian_brand_applied = fields.Char(
        string="SapianERP Brand Applied",
        copy=False,
        help="The exact primary/secondary pair SapianERP last wrote to this "
        "company, as 'primary|secondary'. Empty means the colours were chosen "
        "by someone else and must never be touched. Comparing this against the "
        "live fields is how a stale house colour is told apart from a "
        "deliberate client colour — the two are otherwise identical.",
    )

    sapian_layout_applied = fields.Char(
        string="SapianERP Layout Applied",
        copy=False,
        help="The report layout key SapianERP set on this company. Same purpose "
        "as sapian_brand_applied and the same rule: empty means somebody else "
        "chose the layout, so it is never ours to change. A separate field "
        "rather than a third part of the colour marker, because the layout and "
        "the colour pair change independently.",
    )

    # ---- helpers ---------------------------------------------------------

    @api.model
    def _sapian_brand_pair(self):
        """The current house pair, from the one palette file."""
        return (brand.brand_primary(), brand.brand_secondary())

    @api.model
    def _sapian_default_layout(self):
        """The house report layout, or an empty recordset if unavailable.

        Boxed: conservative structure that suits documents carrying many
        required fields, and it survives photocopying and mono printing —
        which is what actually happens to an Ethiopian invoice. It is also one
        of the five layouts that do NOT use company_primary/secondary_color
        (only wave and bubble do), so the brand does not reach the page through
        it. That is a deliberate, separable decision: colour and layout are
        independent here.

        TREAT AS TEMPORARY. The MoR-required invoice elements are their own
        task and will likely produce a custom layout that moots this choice.
        """
        return (
            self.env.ref("web.external_layout_boxed", raise_if_not_found=False)
            or self.env["ir.ui.view"]
        )

    def _sapian_marker(self, primary, secondary):
        return "%s|%s" % (primary, secondary)

    def _sapian_is_ours_and_stale(self):
        """Companies still wearing a house brand we have since changed.

        BOTH colours must still match what we wrote. A company whose primary
        was edited by hand but whose secondary was not is NOT ours to rewrite —
        somebody has taken ownership of the pair, and guessing which half they
        meant is how a document ends up in two brands.
        """
        primary, secondary = self._sapian_brand_pair()
        current = self._sapian_marker(primary, secondary)
        stale = self.browse()
        for company in self:
            if not company.sapian_brand_applied:
                continue
            if company.sapian_brand_applied == current:
                continue  # already on the current brand
            was_primary, _, was_secondary = company.sapian_brand_applied.partition("|")
            if (
                company.primary_color == was_primary
                and company.secondary_color == was_secondary
            ):
                stale |= company
        return stale

    # ---- create ----------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """New companies start on the house brand.

        ``setdefault`` and not an assignment: a caller that passes its own
        colour — the onboarding wizard, a data file, a client who picked one —
        keeps it, and gets no marker, so we will never rewrite it later.
        """
        primary, secondary = self._sapian_brand_pair()
        layout = self._sapian_default_layout()
        for vals in vals_list:
            ours = "primary_color" not in vals and "secondary_color" not in vals
            vals.setdefault("primary_color", primary)
            vals.setdefault("secondary_color", secondary)
            if ours:
                vals.setdefault("sapian_brand_applied", self._sapian_marker(primary, secondary))
            # The layout is marked independently of the colour: a caller may
            # supply one and not the other, and each is only ever ours to
            # change if we were the one who set it.
            if layout and "external_report_layout_id" not in vals:
                vals["external_report_layout_id"] = layout.id
                vals.setdefault("sapian_layout_applied", layout.key)
        companies = super().create(vals_list)
        # THE DEFAULT LOGO FOR A COMPANY CREATED LATER.
        #
        # Folded into the existing override rather than added as a second one:
        # two `create` methods on one class is a redefinition, and the second
        # silently wins. Written after super() because it is read from a file
        # and because `uses_default_logo` cannot be read before the record
        # exists.
        self._sapian_apply_default_logo(companies)
        return companies

    # ---- drift detection: WARN ONLY, never writes -------------------------

    @api.model
    def _sapian_detect_brand_drift(self):
        """Report companies still on a superseded house colour. Changes nothing.

        Called on module update. It deliberately does NOT fix anything: a code
        change that silently rewrites client-facing document colours on upgrade
        is the same class of fault as a migration that quietly skips a company —
        it works until the day it is wrong, and nobody is watching when it is.

        Returns the drifted companies so a caller can act on a number.
        """
        # Only companies we have marked can ever be ours, so the domain is
        # both narrower and more correct than scanning every company.
        companies = (
            self.sudo()
            .with_context(active_test=False)
            .search([("sapian_brand_applied", "!=", False)])
        )
        stale = companies._sapian_is_ours_and_stale()
        if stale:
            primary, secondary = self._sapian_brand_pair()
            _logger.warning(
                "sapian_theme: %d compan%s still carr%s a superseded SapianERP "
                "brand and will keep printing it on documents: %s. The house "
                "brand is now %s / %s. NOTHING HAS BEEN CHANGED — run "
                "env['res.company']._sapian_apply_brand(dry_run=False) to "
                "apply it, or leave them as they are.",
                len(stale),
                "y" if len(stale) == 1 else "ies",
                "ies" if len(stale) == 1 else "y",
                ", ".join("%s (%s)" % (c.name, c.primary_color) for c in stale),
                primary,
                secondary,
            )
        return stale

    # ---- the explicit command --------------------------------------------

    @api.model
    def _sapian_apply_brand(self, dry_run=True):
        """Move companies on a superseded house colour onto the current one.

        Never runs by itself — an operator has to ask for it. Defaults to
        ``dry_run=True`` so the accident is a report, not a rewrite.

        Both halves of the pair move together or neither does: a document in
        two brands is worse than a document in the old one.

        Returns the affected companies either way, and logs what it actually
        did, so a run that changed nothing is distinguishable from a run that
        worked.
        """
        primary, secondary = self._sapian_brand_pair()
        stale = (
            self.sudo()
            .with_context(active_test=False)
            .search([("sapian_brand_applied", "!=", False)])
            ._sapian_is_ours_and_stale()
        )
        names = ", ".join("%s (%s)" % (c.name, c.primary_color) for c in stale)
        if not stale:
            _logger.info(
                "sapian_theme: no company is on a superseded SapianERP brand; "
                "nothing to apply. (Companies with a colour of their own are "
                "not counted and are never touched.)"
            )
            return stale
        if dry_run:
            _logger.info(
                "sapian_theme: DRY RUN — %d compan%s would move to %s / %s: %s. "
                "Nothing was written. Re-run with dry_run=False to apply.",
                len(stale),
                "y" if len(stale) == 1 else "ies",
                primary,
                secondary,
                names,
            )
            return stale
        stale.write(
            {
                "primary_color": primary,
                "secondary_color": secondary,
                "sapian_brand_applied": self._sapian_marker(primary, secondary),
            }
        )
        _logger.info(
            "sapian_theme: APPLIED the current brand %s / %s to %d compan%s: %s",
            primary,
            secondary,
            len(stale),
            "y" if len(stale) == 1 else "ies",
            names,
        )
        return stale

    # ---- install-time backfill -------------------------------------------

    @api.model
    def _sapian_apply_brand_defaults(self):
        """Fill the brand on companies that have NO colour set. Idempotent.

        Runs once at install (post_init_hook) so an existing database picks the
        brand up on its documents. It writes only where the field is empty:
        a company that has already chosen a colour is never overwritten, which
        is the whole contract of this module for white-label clients.

        Returns the companies it actually changed, so the caller can log a
        number rather than assume the work happened.
        """
        primary, secondary = self._sapian_brand_pair()
        untouched = (
            self.sudo()
            .with_context(active_test=False)
            .search(["|", ("primary_color", "=", False), ("secondary_color", "=", False)])
        )
        changed = self.browse()
        for company in untouched:
            vals = {}
            if not company.primary_color:
                vals["primary_color"] = primary
            if not company.secondary_color:
                vals["secondary_color"] = secondary
            if vals:
                # Marked only when WE supplied the whole pair. A company that
                # had one colour of its own keeps ownership of both.
                if len(vals) == 2:
                    vals["sapian_brand_applied"] = self._sapian_marker(primary, secondary)
                company.write(vals)
                changed |= company
        return changed

    @api.model
    def _sapian_apply_default_logo(self, companies=None):
        """Put our logo on companies that never chose one. Idempotent.

        Returns the number of companies written, so a caller can log a fact
        rather than an intention.
        """
        # `search([])` with no limit is the intent, not an oversight: every
        # company that still carries Odoo's stock image should carry ours, and
        # a limit would silently leave the tail of a multi-company database on
        # somebody else's mark.
        # pylint: disable=no-search-all
        companies = companies or self.sudo().search([])
        with file_open(LOGO, "rb") as handle:
            logo = base64.b64encode(handle.read())

        written = 0
        for company in companies:
            # `uses_default_logo` is True only while the company still carries
            # the stock Odoo image. Once a client uploads their own, or the
            # onboarding wizard writes one, this stops being true and we never
            # touch it again.
            if company.uses_default_logo and company.logo != logo:
                company.sudo().write({"logo": logo})
                written += 1
                _logger.info("sapian_theme: default logo written on %s", company.display_name)
        return written
