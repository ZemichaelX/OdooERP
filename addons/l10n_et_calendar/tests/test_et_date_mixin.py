# -*- coding: utf-8 -*-
"""The mixin: stored, searchable, read-only, and correct on a model with two
dates.

The conversion arithmetic is NOT retested here — it has 125 goldens in
tests_fast/ that run without Odoo (CLAUDE.md rule 10). What this file asserts is
everything the ORM adds on top: that the value is really in a column, that a
domain against it returns the right records, that the column is indexed, that it
cannot be written by hand, and that a model mirroring TWO dates keeps them
independent.

WHY THE HOST MODEL IS BUILT HERE AND NOT SHIPPED
------------------------------------------------
The mixin is abstract, so it has no table of its own and nothing to search. It
needs a host. This module deliberately depends on `base` and `web` only, so
there is no real two-date model available to it — `account.move` arrives in the
bridge module, not here.

The host is therefore built for the duration of these tests and removed
afterwards, using `odoo.orm.model_classes.add_to_registry`, which is what Odoo's
own `test_orm` suite uses for the same purpose. Three things make that safe
here, and they are the reason this is not the same sin the mixin's docstring
argues against:

  * it is TEST code, not shipped code — no client registry ever sees it;
  * `_module = None`, so the class is never collected into
    `MetaModel._module_to_models__` and cannot be built into a real database by
    a later registry load in the same process;
  * the registry entry is removed in `addClassCleanup` and the table itself
    disappears with the test transaction rollback.

A shipped probe model would put two real columns on a real table in every client
database for the sake of a test, which is worse.
"""

from datetime import date

from odoo import fields, models
from odoo.exceptions import AccessError
from odoo.orm.model_classes import add_to_registry
from odoo.tests import TransactionCase, tagged

from odoo.addons.l10n_et_calendar.models.l10n_et_date_mixin import l10n_et_mirror_field

PROBE = "l10n.et.calendar.probe"


class L10nEtCalendarProbe(models.Model):
    """A two-date host. Invoice date plus due date is the ORDINARY case.

    `_module = None` keeps this class out of the metaclass's module registry —
    without it the class would be filed under `l10n_et_calendar` at import time
    and built into the next database whose registry loads in this process.
    """

    _module = None
    _name = PROBE
    _description = "Ethiopian Calendar Mixin Probe (tests only)"
    _inherit = ["l10n.et.date.mixin"]

    _l10n_et_date_map = {
        "start_date": "l10n_et_start_date",
        "end_date": "l10n_et_end_date",
    }

    name = fields.Char()
    start_date = fields.Date()
    end_date = fields.Date()
    l10n_et_start_date = l10n_et_mirror_field("Start (ET)")
    l10n_et_end_date = l10n_et_mirror_field("End (ET)")


@tagged("post_install", "-at_install")
class TestL10nEtDateMixin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        registry = cls.env.registry
        add_to_registry(registry, L10nEtCalendarProbe)
        cls.addClassCleanup(cls._forget_probe, registry, cls.env.cr)
        registry._setup_models__(cls.env.cr, [])
        registry.init_models(cls.env.cr, [PROBE], {"module": "l10n_et_calendar"}, install=True)
        cls.probe = cls.env[PROBE]
        cls.company = cls.env.company

    @staticmethod
    def _forget_probe(registry, cr):
        """Take the probe back out, so the rest of the run sees the registry it
        would have seen if this file did not exist.

        The TABLE goes away with the transaction rollback; the registry is
        process-global and would not, so it is cleaned explicitly. `__delitem__`
        also discards the model from every `_inherit_children`, which is what
        keeps `l10n.et.date.mixin` from carrying a dangling child.
        """
        if PROBE in registry:
            del registry[PROBE]
        registry._setup_models__(cr, [])

    def _make(self, start, end=None, name="probe"):
        return self.probe.create({"name": name, "start_date": start, "end_date": end})

    # ---- the mirror itself --------------------------------------------------

    def test_the_mirror_is_computed_from_the_gregorian_field(self):
        record = self._make(date(2025, 7, 8))
        self.assertEqual(record.l10n_et_start_date, "2017-11-01")

    def test_a_model_with_two_dates_keeps_them_independent(self):
        """The ordinary case: invoice date and due date on the same record.

        One `depends` lambda over the map drives both, and writing one must not
        disturb the other.
        """
        record = self._make(date(2025, 7, 8), date(2025, 8, 7))
        self.assertEqual(record.l10n_et_start_date, "2017-11-01")
        self.assertEqual(record.l10n_et_end_date, "2017-12-01")

        record.end_date = date(2025, 9, 11)
        self.assertEqual(record.l10n_et_end_date, "2018-01-01", "the second date")
        self.assertEqual(
            record.l10n_et_start_date, "2017-11-01", "the first must not have moved"
        )

    def test_an_empty_source_gives_an_empty_mirror(self):
        """An invoice with no due date must not grow one in Ethiopian."""
        record = self._make(date(2025, 7, 8), None)
        self.assertEqual(record.l10n_et_start_date, "2017-11-01")
        self.assertFalse(record.l10n_et_end_date)

    def test_clearing_the_source_clears_the_mirror(self):
        record = self._make(date(2025, 7, 8), date(2025, 8, 7))
        record.end_date = False
        self.assertFalse(record.l10n_et_end_date)

    # ---- STORED: really in a column -----------------------------------------

    def test_the_value_is_in_the_database_not_just_in_the_cache(self):
        """`store=True` asserted against SQL, because a compute that only ever
        runs in memory would pass every ORM-level check and still leave the
        column empty for a report or a BI tool reading the table."""
        record = self._make(date(2025, 7, 8))
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT l10n_et_start_date FROM l10n_et_calendar_probe WHERE id = %s",
            (record.id,),
        )
        self.assertEqual(self.env.cr.fetchone()[0], "2017-11-01")

    def test_the_column_is_indexed(self):
        """A stored field you filter on without an index is a sequential scan
        on every search — see the README for the measured cost."""
        self.env.flush_all()
        self.env.cr.execute("""
            SELECT indexdef FROM pg_indexes
             WHERE tablename = 'l10n_et_calendar_probe'
               AND indexdef LIKE '%%l10n_et_start_date%%'
            """)
        self.assertTrue(self.env.cr.fetchall(), "no index on the mirrored field")

    # ---- SEARCHABLE ---------------------------------------------------------

    def test_search_by_exact_ethiopian_date(self):
        wanted = self._make(date(2025, 7, 8), name="hamle 1")
        self._make(date(2025, 7, 9), name="hamle 2")
        self._make(date(2025, 8, 7), name="nehase 1")
        found = self.probe.search([("l10n_et_start_date", "=", "2017-11-01")])
        self.assertEqual(found, wanted)

    def test_search_by_ethiopian_month_returns_exactly_that_month(self):
        """The filter that makes this useful: one Ethiopian month, with no
        Gregorian arithmetic in the domain.

        Hamle 2017 runs 8 July – 6 August 2025, which is not a Gregorian month
        and cannot be expressed as one.
        """
        in_hamle = self.probe
        for day in (date(2025, 7, 8), date(2025, 7, 20), date(2025, 8, 6)):
            in_hamle |= self._make(day, name="hamle %s" % day)
        outside = self.probe
        for day in (date(2025, 7, 7), date(2025, 8, 7)):
            outside |= self._make(day, name="outside %s" % day)

        found = self.probe.search([("l10n_et_start_date", "like", "2017-11-%")])
        self.assertEqual(found, in_hamle)
        self.assertFalse(found & outside)
        # the boundary days specifically: Sene 30 and Nehase 1
        self.assertEqual(
            self.probe.search([("l10n_et_start_date", "=", "2017-10-30")]).name,
            "outside 2025-07-07",
        )

    def test_search_orders_and_ranges_correctly(self):
        """The reason the stored form is canonical and not the pretty string.

        'Meskerem 1, 2018' sorts before 'Hamle 1, 2017' alphabetically, which
        is wrong by eight months. The canonical form sorts by date.
        """
        early = self._make(date(2025, 7, 8), name="hamle")  # 2017-11-01
        late = self._make(date(2025, 9, 11), name="meskerem")  # 2018-01-01
        ordered = self.probe.search(
            [("id", "in", (early | late).ids)], order="l10n_et_start_date asc"
        )
        self.assertEqual(ordered[0], early)
        self.assertEqual(ordered[1], late)
        self.assertEqual(
            self.probe.search(
                [
                    ("id", "in", (early | late).ids),
                    ("l10n_et_start_date", ">=", "2018-01-01"),
                ]
            ),
            late,
        )

    # ---- READ-ONLY ----------------------------------------------------------

    def test_the_mirror_is_readonly_in_the_ui(self):
        field = self.probe._fields["l10n_et_start_date"]
        self.assertTrue(field.readonly, "the Gregorian field is the source of truth")
        self.assertTrue(field.store)
        self.assertFalse(field.copy, "duplicating a record must re-derive, not copy")

    def test_writing_the_mirror_directly_does_not_stick(self):
        """A computed field with no inverse: a write is discarded and the next
        recompute restores the truth. Proven rather than assumed, because
        'readonly' in Odoo is a UI attribute and not a database constraint."""
        record = self._make(date(2025, 7, 8))
        record.l10n_et_start_date = "9999-13-06"
        record.invalidate_recordset()
        self.assertEqual(record.l10n_et_start_date, "2017-11-01")

    # ---- DISPLAY, and the company settings ----------------------------------

    def test_display_honours_the_company_format(self):
        record = self._make(date(2025, 7, 8))
        self.company.l10n_et_date_format = "latin"
        self.assertEqual(record.l10n_et_display("start_date"), "Hamle 1, 2017")
        self.company.l10n_et_date_format = "amharic"
        self.assertEqual(record.l10n_et_display("start_date"), "ሐምሌ 1 ቀን 2017 ዓ.ም.")
        self.company.l10n_et_date_format = "numeric"
        self.assertEqual(record.l10n_et_display("start_date"), "01/11/2017")

    def test_changing_the_display_format_rewrites_nothing(self):
        """The design decision, asserted.

        The stored value is canonical, so flipping the format is a metadata
        change. If the formatted string were stored, this flip would queue a
        recompute of every mirrored date in the database — see the README.
        """
        record = self._make(date(2025, 7, 8))
        self.env.flush_all()
        self.company.l10n_et_date_format = "amharic"
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT l10n_et_start_date FROM l10n_et_calendar_probe WHERE id = %s",
            (record.id,),
        )
        self.assertEqual(
            self.env.cr.fetchone()[0],
            "2017-11-01",
            "the stored value must not depend on the display format",
        )

    def test_display_of_an_empty_date_is_empty(self):
        record = self._make(date(2025, 7, 8), None)
        self.assertEqual(record.l10n_et_display("end_date"), "")

    def test_report_calendar_setting_gates_each_calendar(self):
        record = self._make(date(2025, 7, 8))
        self.company.l10n_et_report_calendar = "both"
        self.assertTrue(record.l10n_et_report_shows("gregorian"))
        self.assertTrue(record.l10n_et_report_shows("ethiopian"))
        self.company.l10n_et_report_calendar = "ethiopian"
        self.assertFalse(record.l10n_et_report_shows("gregorian"))
        self.assertTrue(record.l10n_et_report_shows("ethiopian"))
        self.company.l10n_et_report_calendar = "gregorian"
        self.assertTrue(record.l10n_et_report_shows("gregorian"))
        self.assertFalse(record.l10n_et_report_shows("ethiopian"))

    def test_the_settings_are_per_company(self):
        """CLAUDE.md rule 3. A group with an Ethiopian arm and an export arm
        must be able to answer differently."""
        other = self.env["res.company"].create({"name": "Export Arm PLC"})
        self.company.l10n_et_date_format = "amharic"
        other.l10n_et_date_format = "latin"
        record = self._make(date(2025, 7, 8))
        self.assertEqual(record.l10n_et_display("start_date", company=other), "Hamle 1, 2017")
        self.assertEqual(
            record.l10n_et_display("start_date", company=self.company),
            "ሐምሌ 1 ቀን 2017 ዓ.ም.",
        )

    # ---- the round trip through the ORM -------------------------------------

    def test_parse_is_the_inverse_of_the_stored_form(self):
        record = self._make(date(2025, 9, 10))  # Pagume 5, 2017
        parsed = record.l10n_et_parse(record.l10n_et_start_date)
        self.assertEqual((parsed.year, parsed.month, parsed.day), (2017, 13, 5))
        self.assertTrue(parsed.is_pagume)

    def test_a_pagume_6_date_survives_the_orm(self):
        """The day the reference library's round-trip property caught a bug on.
        It goes through the ORM too."""
        record = self._make(date(2023, 9, 11))
        self.assertEqual(record.l10n_et_start_date, "2015-13-06")
        self.assertEqual(record.l10n_et_display("start_date"), "Pagume 6, 2015")


@tagged("post_install", "-at_install")
class TestL10nEtCalendarInstall(TransactionCase):
    """The module stands alone.

    It must install on a database with no other sapian or l10n_et module — it
    is the calendar, not a tax feature, and a client who wants Ethiopian dates
    on a purchase order must not be handed a chart of accounts with them.
    """

    def test_depends_on_base_and_base_setup_only(self):
        module = self.env["ir.module.module"].search(
            [("name", "=", "l10n_et_calendar")], limit=1
        )
        self.assertTrue(module, "the module must be present")
        self.assertEqual(
            set(module.dependencies_id.mapped("name")),
            {"base", "base_setup"},
            "a dependency on l10n_et_base or sapian_core would drag Ethiopian "
            "accounting onto a client who only wanted dates",
        )

    def test_nothing_of_ours_is_pulled_in_transitively(self):
        """The direct list above can stay honest while a dependency of a
        dependency drags the chart of accounts in. Walk the whole closure."""
        Module = self.env["ir.module.module"]
        seen, frontier = set(), {"l10n_et_calendar"}
        while frontier:
            names = Module.search([("name", "in", list(frontier))])
            seen |= frontier
            frontier = set(names.dependencies_id.mapped("name")) - seen
        ours = {
            name
            for name in seen
            if name.startswith(("sapian_", "l10n_et_")) and name != "l10n_et_calendar"
        }
        self.assertFalse(
            ours, "the calendar must not pull in any other module of ours: %s" % ours
        )
        self.assertEqual(
            seen,
            {"l10n_et_calendar", "base", "base_setup", "web"},
            "the whole dependency closure, spelled out so a new dependency has "
            "to be argued for rather than noticed later",
        )

    def test_the_mixin_is_abstract_and_ships_no_table(self):
        self.assertTrue(self.env["l10n.et.date.mixin"]._abstract)
        self.env.cr.execute("SELECT to_regclass('l10n_et_date_mixin')")
        self.assertIsNone(self.env.cr.fetchone()[0], "an abstract mixin has no table")

    def test_the_company_settings_have_safe_defaults(self):
        company = self.env["res.company"].create({"name": "Defaults Co"})
        self.assertEqual(company.l10n_et_date_format, "latin")
        self.assertEqual(
            company.l10n_et_report_calendar,
            "both",
            "a document read by a supplier, a customer and the MoR is safest "
            "carrying both calendars",
        )

    def test_a_non_privileged_user_can_read_a_mirrored_date(self):
        """No new ACL is needed because nothing new is a real model — but the
        fields must still be readable by an ordinary internal user."""
        user = self.env["res.users"].create(
            {
                "name": "Ordinary User",
                "login": "l10n_et_calendar_ordinary",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        company = self.env.company.with_user(user)
        try:
            self.assertTrue(company.l10n_et_date_format)
        except AccessError as error:
            self.fail("an internal user cannot read the calendar settings: %s" % error)
