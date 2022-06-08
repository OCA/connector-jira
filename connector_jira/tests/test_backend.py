# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from odoo import fields

from ..fields import MilliDatetime
from .common import JiraTransactionComponentCase


class TestBackendTimestamp(JiraTransactionComponentCase):
    def _create_timestamp(self):
        return self.env["jira.backend.timestamp"].create(
            {
                "backend_id": self.backend_record.id,
                "from_date_field": "import_project_task_from_date",
                "last_timestamp": datetime.fromtimestamp(0),
                "component_usage": "timestamp.batch.importer",
            }
        )

    def test_millidatetime_field(self):
        ts = self._create_timestamp()
        self.assertEqual(ts.last_timestamp, datetime(1970, 1, 1, 0, 0))
        new_date = datetime(2019, 4, 8, 10, 30, 59, 375000)
        ts._update_timestamp(new_date)
        # keeps milliseconds precision and return datetime instance
        self.assertEqual(ts.last_timestamp, new_date)

    def test_unix_timestamp_helpers(self):
        as_datetime = datetime(2019, 4, 8, 10, 30, 59, 375000)
        as_timestamp = MilliDatetime.to_timestamp(as_datetime)
        self.assertEqual(as_timestamp, 1554719459375)
        dt2 = MilliDatetime.from_timestamp(as_timestamp)
        self.assertEqual(dt2, as_datetime)

    def test_from_to_string(self):
        self.assertEqual(
            MilliDatetime.to_string(datetime(2019, 4, 8, 10, 30, 59, 375000)),
            "2019-04-08 10:30:59.375000",
        )
        self.assertEqual(
            MilliDatetime.from_string("2019-04-08 10:30:59.375000"),
            datetime(2019, 4, 8, 10, 30, 59, 375000),
        )


class TestBackend(JiraTransactionComponentCase):
    def _test_import_date_computed_field(self, timestamp_field_name, component_usage):
        backend = self.backend_record
        self.assertFalse(backend[timestamp_field_name])
        # We don't have milliseconds on the jira.backend fields,
        # they are shown on the webclient. We lose precision when
        # users fill dates, but we mostly want to keep precision
        # for dates given by Jira.
        test_date = "2019-04-08 10:30:59"
        backend.write({timestamp_field_name: test_date})
        jira_ts = self.env["jira.backend.timestamp"].search(
            [
                ("backend_id", "=", backend.id),
                ("from_date_field", "=", timestamp_field_name),
                ("component_usage", "=", component_usage),
            ]
        )
        # The field on jira.backend is a standard odoo Datetime field so works
        # with strings (in 11.0). But the field on jira.backend.timestamp is a
        # "custom" MilliDatetime field which works with datetime instances.
        self.assertEqual(jira_ts.last_timestamp, fields.Datetime.from_string(test_date))

    def test_import_project_task_from_date(self):
        self._test_import_date_computed_field(
            "import_project_task_from_date", "timestamp.batch.importer"
        )

    def test_import_analytic_line_from_date(self):
        self._test_import_date_computed_field(
            "import_analytic_line_from_date", "timestamp.batch.importer"
        )

    def test_delete_analytic_line_from_date(self):
        self._test_import_date_computed_field(
            "delete_analytic_line_from_date", "timestamp.batch.deleter"
        )

    def test_run_background_from_date(self):
        test_date = "2019-04-08 10:30:59"
        self.backend_record.write({"import_project_task_from_date": test_date})
        jira_ts = self.env["jira.backend.timestamp"].search(
            [
                ("backend_id", "=", self.backend_record.id),
                ("from_date_field", "=", "import_project_task_from_date"),
                ("component_usage", "=", "timestamp.batch.importer"),
            ]
        )

        with self.mock_with_delay() as (delayable_cls, delayable):
            self.backend_record._run_background_from_date(
                "jira.project.task",
                "import_project_task_from_date",
                "timestamp.batch.importer",
            )
            delayable_cls.assert_called_once()
            # arguments passed in 'with_delay()'
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual(
                (self.env["jira.project.task"],),
                delay_args,
            )

            # job method called after 'with_delay()'
            delayable.run_batch_timestamp.assert_called_once()
            delay_args, __ = delayable.run_batch_timestamp.call_args

            self.assertEqual(
                (
                    self.backend_record,
                    jira_ts,
                ),
                delay_args,
            )
