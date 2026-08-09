# -*- coding: utf-8 -*-
"""The PAYE-correction report must never overwrite an earlier one.

Only ``filestore/`` under the Odoo data directory is per-database; the rest of
``data_dir`` is shared by every database on the instance. A report file named
without the database would mean that upgrading the second tenant silently
destroys the first tenant's report — and that report is the only surviving
record that a tenant's posted payroll was computed on the wrong bands.

Two runs must therefore leave two files, and the file name must carry both the
database and the run time.
"""

import importlib.util
import os
import sys

from odoo.tests import TransactionCase, tagged
from odoo.tools import config as odoo_config

_MIGRATION = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "migrations",
    "19.0.4.0.0",
    "post-migrate.py",
)
_spec = importlib.util.spec_from_file_location("l10n_et_payroll_post_migrate", _MIGRATION)
_migration = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _migration
_spec.loader.exec_module(_migration)


@tagged("post_install", "-at_install", "l10n_et_payroll")
class TestMigrationReportPersistence(TransactionCase):
    def _persist(self, body="report body"):
        return _migration._persist_report(
            self.env, body, _migration._calc.PAYE_1395_2025_EFFECTIVE_FROM
        )

    def test_filename_carries_database_and_run_time(self):
        filename = _migration._report_filename(self.env)
        self.assertTrue(filename.startswith("paye_band_correction_"))
        self.assertIn(self.env.cr.dbname, filename)
        self.assertTrue(filename.endswith(".txt"))
        # ..._<dbname>_<YYYYMMDDHHMMSS>.txt — 14-digit run-time stamp.
        stamp = filename[: -len(".txt")].rsplit("_", 1)[-1]
        self.assertEqual(len(stamp), 14, filename)
        self.assertTrue(stamp.isdigit(), filename)

    def test_two_runs_leave_two_files(self):
        """The regression: a shared data_dir plus a constant name lost reports."""
        first_path, first_attachment = self._persist("FIRST RUN")
        second_path, second_attachment = self._persist("SECOND RUN")

        self.assertTrue(first_path, "the first report was written to disk")
        self.assertTrue(second_path, "the second report was written to disk")
        self.assertNotEqual(first_path, second_path)
        self.assertTrue(os.path.exists(first_path))
        self.assertTrue(os.path.exists(second_path))

        # Neither run clobbered the other's content.
        with open(first_path, "rb") as handle:
            self.assertIn(b"FIRST RUN", handle.read())
        with open(second_path, "rb") as handle:
            self.assertIn(b"SECOND RUN", handle.read())

        # The attachment (already per-database) is named for the file it matches.
        self.assertNotEqual(first_attachment.id, second_attachment.id)
        self.assertEqual(first_attachment.name, os.path.basename(first_path))
        self.assertEqual(second_attachment.name, os.path.basename(second_path))

        for path in (first_path, second_path):
            os.remove(path)

    def test_report_is_written_under_the_data_dir(self):
        path, _attachment = self._persist("PATH CHECK")
        self.assertTrue(path.startswith(odoo_config["data_dir"]), path)
        os.remove(path)
