# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from datetime import datetime

from odoo.addons.connector_jira.fields import MilliDatetime
from .common import JiraTransactionCase


class TestBackendTimestamp(JiraTransactionCase):

    def _create_timestamp(self):
        return self.env['jira.backend.timestamp'].create({
            'backend_id': self.backend_record.id,
            'from_date_field': 'import_project_task_from_date',
            'last_timestamp': datetime.fromtimestamp(0),
            'component_usage': 'timestamp.batch.importer',
        })

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
            '2019-04-08 10:30:59.375000'
        )
        self.assertEqual(
            MilliDatetime.from_string('2019-04-08 10:30:59.375000'),
            datetime(2019, 4, 8, 10, 30, 59, 375000)
        )
