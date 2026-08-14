# -*- coding: utf-8 -*-
"""The Ethiopian-date mixin: a Gregorian date field, mirrored.

HOW A MODEL OPTS IN
-------------------
Two things — inherit the mixin, and say which fields to mirror:

    class AccountMove(models.Model):
        _name = "account.move"
        _inherit = ["account.move", "l10n.et.date.mixin"]

        _l10n_et_date_map = {
            "invoice_date": "l10n_et_invoice_date",
            "invoice_date_due": "l10n_et_invoice_date_due",
        }

        l10n_et_invoice_date = l10n_et_mirror_field("Invoice Date (ET)")
        l10n_et_invoice_date_due = l10n_et_mirror_field("Due Date (ET)")

`l10n_et_mirror_field` is a factory, so the field declaration carries no logic
at all: compute, store, index, readonly, search and the depends are all fixed
by the mixin. Adding a second date is one map entry and one factory call.

WHY THE FIELDS ARE DECLARED AND NOT INJECTED
--------------------------------------------
Odoo can add fields to a model class programmatically —
`odoo.orm.model_classes.add_field` — and a mixin that read `_l10n_et_date_map`
and created the fields itself would remove even those two lines.

It is not done, deliberately. That function is ORM internals: it lived on
`BaseModel._add_field` before Odoo 19 and moved to a module-level function in
`odoo/orm/model_classes.py` in it. CLAUDE.md rule 1 says extend Odoo through
inheritance, and a localisation module reaching into the registry builder is
exactly the kind of cleverness that turns a version upgrade into a debugging
session. Two declarative lines per date is a small price for a module that will
still import on Odoo 20.

WHAT IS STORED, AND WHY IT IS NOT THE PRETTY STRING
---------------------------------------------------
The stored value is CANONICAL and format-independent: ``2017-11-01``, the
Ethiopian year-month-day in the same shape as an ISO date. Not "Hamle 1, 2017".

Three reasons, in order of how much they matter:

1. **The company's display format must not be able to invalidate a million
   rows.** If the stored string were the formatted one, then `depends` would
   have to include the company setting, and a consultant flipping Latin to
   Amharic during a demo would queue a full recompute of every invoice, every
   purchase order, every mirrored date in the database. Storing the canonical
   form makes that setting a pure display concern — a metadata change with no
   write at all.
2. **It sorts.** "Hamle 1, 2017" and "Meskerem 1, 2018" sort M before H, which
   is wrong by eight months. `2017-11-01` and `2018-01-01` sort correctly, so
   an ordered list view and a `>=` domain both behave.
3. **It filters the way a period filter should.** `l10n_et_invoice_date` like
   `2017-11%` is every invoice in Hamle 2017 — one month, exactly, with no
   Gregorian arithmetic in the domain.

The human-readable form is produced at DISPLAY time by
:meth:`l10n_et_display`, which honours the company format setting. It is a
method rather than a second stored field, so a mirrored date costs exactly one
column.
"""

import pytz

from odoo import api, fields, models

from ..reference import et_calendar as cal

#: The canonical stored form. Ten characters, fixed width, sortable.
CANONICAL_LENGTH = 10

#: Ethiopia's civil timezone, used to turn a Datetime source into a day.
#:
#: Odoo stores Datetime fields as naive UTC. Taking `.date()` off one of those
#: is wrong by a day for a third of every Ethiopian evening: an order placed at
#: 01:00 on 8 July in Addis is stored as 22:00 on 7 July UTC, and a naive
#: conversion would file it under Sene 30 rather than Hamle 1 — the "wrong by
#: one day, and trusted" failure this module exists to avoid.
#:
#: It is FIXED rather than read from a company or a user setting on purpose.
#: "What Ethiopian date was this?" is a question about the day in Ethiopia, and
#: Ethiopia has one timezone and has never observed daylight saving. A user
#: setting would also make a stored value depend on who saved the record, and a
#: company setting would silently invalidate every stored mirror the day
#: somebody edited it.
ETHIOPIAN_TZ = pytz.timezone("Africa/Addis_Ababa")


def l10n_et_mirror_field(string, **overrides):
    """Declare a mirrored Ethiopian date field.

    Everything that makes the mirror work is fixed here rather than repeated at
    each declaration: stored so it can be searched, indexed so the search is
    not a sequential scan, readonly because the Gregorian field is the source
    of truth, and `copy=False` because duplicating a record re-derives it.
    """
    values = {
        "string": string,
        "compute": "_compute_l10n_et_dates",
        "store": True,
        "readonly": True,
        "copy": False,
        "index": "btree_not_null",
        "size": CANONICAL_LENGTH,
        "help": (
            "The Ethiopian calendar date, derived from the Gregorian field "
            "beside it. Stored as year-month-day so it sorts and can be "
            "filtered by period (2017-11 is all of Hamle 2017)."
        ),
    }
    values.update(overrides)
    return fields.Char(**values)


class L10nEtDateMixin(models.AbstractModel):
    _name = "l10n.et.date.mixin"
    _description = "Ethiopian Calendar Date Mirror"

    #: {gregorian field name: ethiopian field name}. Set by the opting-in model.
    _l10n_et_date_map = {}

    # ------------------------------------------------------------------ compute

    @api.depends(lambda self: list(self._l10n_et_date_map))
    def _compute_l10n_et_dates(self):
        """Mirror every mapped Gregorian date onto its Ethiopian field.

        `depends` is a lambda over the map, so a model that mirrors two dates
        gets both triggers with no extra declaration — and a model that adds a
        third later does not have to remember to update a decorator.

        A False source gives a False mirror rather than a placeholder: an
        invoice with no due date must not grow a due date in Ethiopian.

        The source may be a Date or a Datetime — an invoice date is a Date, a
        purchase order deadline is a Datetime — and the difference is handled
        here rather than in each bridge, because getting it wrong is a one-day
        error and a bridge is supposed to be a declaration.
        """
        for record in self:
            for source, target in record._l10n_et_date_map.items():
                value = record[source]
                if not value:
                    record[target] = False
                    continue
                is_datetime = record._fields[source].type == "datetime"
                record[target] = self._l10n_et_canonical(value, is_datetime=is_datetime)

    # ------------------------------------------------------------- conversion

    @api.model
    def _l10n_et_canonical(self, value, is_datetime=False):
        """The stored form: ``2017-11-01``. Never localised, never formatted.

        A Datetime is converted to the day it was in ETHIOPIA before the
        calendar arithmetic runs — see :data:`ETHIOPIAN_TZ` for why that is a
        fixed timezone and not a setting.
        """
        if is_datetime:
            moment = fields.Datetime.to_datetime(value)
            day = pytz.utc.localize(moment).astimezone(ETHIOPIAN_TZ).date()
        else:
            day = fields.Date.to_date(value)
        ethiopian = cal.gregorian_to_ethiopian(day)
        return "%04d-%02d-%02d" % (ethiopian.year, ethiopian.month, ethiopian.day)

    @api.model
    def l10n_et_parse(self, canonical):
        """Inverse of :meth:`_l10n_et_canonical` — for domains and reports."""
        year, month, day = (int(part) for part in canonical.split("-"))
        return cal.EthiopianDate(year, month, day)

    # ---------------------------------------------------------------- display

    def l10n_et_display(self, field_name=None, company=None):
        """The human-readable Ethiopian date, in the company's chosen format.

        Called from views and QWeb rather than stored, so the format setting is
        a display choice and not a reason to rewrite a million rows.

        ``field_name`` is the GREGORIAN field name — the caller names the thing
        it already knows about, and the map does the rest.
        """
        self.ensure_one()
        if field_name is None:
            field_name = next(iter(self._l10n_et_date_map), None)
        target = self._l10n_et_date_map.get(field_name)
        canonical = self[target] if target else False
        if not canonical:
            return ""
        company = company or self.env.company
        return self._l10n_et_format(self.l10n_et_parse(canonical), company)

    @api.model
    def _l10n_et_format(self, ethiopian, company=None):
        """Format an :class:`EthiopianDate` for a company.

        The month names come from the reference library as DATA and are wrapped
        for translation here, which is the whole reason the library ships no
        English: a hardcoded English month in a localisation library is a
        translation nobody can ever correct.

        One honest caveat about that wrapping: because the argument is a lookup
        rather than a literal, Odoo's .pot exporter cannot see these strings, so
        they will not appear in an exported catalog on their own. Nothing is
        broken by that — the module already ships both scripts, and the company
        setting chooses between them, so neither format needs a .po file to
        read correctly. The wrapper is here so that a client who wants a
        different spelling ("Hidar" vs "Hedar") can be served by a catalog entry
        added by hand, rather than by a patch to this module.
        """
        company = company or self.env.company
        style = company.l10n_et_date_format or "latin"
        if style == "numeric":
            return "%02d/%02d/%04d" % (ethiopian.day, ethiopian.month, ethiopian.year)
        if style == "amharic":
            return "%s %d ቀን %d ዓ.ም." % (
                self.env._(cal.MONTHS_AMHARIC[ethiopian.month - 1]),
                ethiopian.day,
                ethiopian.year,
            )
        return "%s %d, %d" % (
            self.env._(cal.MONTHS_LATIN[ethiopian.month - 1]),
            ethiopian.day,
            ethiopian.year,
        )

    # ----------------------------------------------------------------- report

    @api.model
    def l10n_et_report_shows(self, which, company=None):
        """Should a PDF print ``which`` calendar? ('gregorian' or 'ethiopian')

        One company setting, consulted by the document templates, so a client
        who files in Ethiopian and a client who invoices exporters in Gregorian
        each get what they need without a second report layout.
        """
        company = company or self.env.company
        setting = company.l10n_et_report_calendar or "both"
        return setting == "both" or setting == which
