# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from freezegun import freeze_time

from .common import JiraTransactionComponentCase, recorder


class TestBatchTimestampImport(JiraTransactionComponentCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_issue_type_bindings()
        cls.epic_issue_type = cls.env["jira.issue.type"].search([("name", "=", "Epic")])
        cls.project = cls.env["project.project"].create({"name": "Jira Project"})

    # note: when you are recording tests with VCR, Jira
    # will reject any call when you pretend to have a time too
    # different from now(). So adjust this date be rougly equal
    # to now().
    @freeze_time("2019-04-08 12:51:36.595")
    @recorder.use_cassette
    def test_import_batch_timestamp_tasks(self):
        """Import all tasks since last timestamp"""
        self._create_project_binding(
            self.project, issue_types=self.epic_issue_type, external_id="10000"
        )
        jira_ts = self.env["jira.backend.timestamp"]._timestamp_for_field(
            self.backend_record,
            "import_project_task_from_date",
            "timestamp.batch.importer",
        )
        since_date = "2019-04-05 00:00:00.000"
        jira_ts._update_timestamp(since_date)
        with self.mock_with_delay() as (delayable_cls, delayable):
            self.env["jira.project.task"].run_batch_timestamp(
                self.backend_record,
                jira_ts,
            )
            # Jira WS returns 4 task ids here, we expect to have 4
            # jobs delayed
            number_of_tasks = 4
            self.assertEqual(delayable_cls.call_count, number_of_tasks)
            # arguments passed in 'with_delay()'
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual(
                (self.env["jira.project.task"],),
                delay_args,
            )

            # Job method called after 'with_delay()'.
            self.assertEqual(delayable.import_record.call_count, number_of_tasks)
            delay_args = delayable.import_record.call_args_list
            expected = [
                ((self.backend_record, "10103"), {"force": False, "record": None}),
                ((self.backend_record, "10102"), {"force": False, "record": None}),
                ((self.backend_record, "10101"), {"force": False, "record": None}),
                ((self.backend_record, "10100"), {"force": False, "record": None}),
            ]
            self.assertEqual(
                sorted((args, kwargs) for args, kwargs in delay_args),
                sorted(expected),
            )

        # For tasks, Jira does not return an "until" time, so we the timestamp
        # to start the next import is now (the freezed time for this test)
        # minus 5 minutes, the overlap being because the JQL query has a minute
        # precision and does not return immediately the modified tasks
        self.assertEqual(
            jira_ts.last_timestamp, datetime(2019, 4, 8, 12, 46, 36, 595000)
        )

    @freeze_time("2019-04-08 13:22:07.325")
    @recorder.use_cassette
    def test_import_batch_timestamp_analytic_line(self):
        """Import all worklogs since last timestamp"""
        self._create_project_binding(
            self.project, issue_types=self.epic_issue_type, external_id="10000"
        )
        jira_ts = self.env["jira.backend.timestamp"]._timestamp_for_field(
            self.backend_record,
            "import_analytic_line_from_date",
            "timestamp.batch.importer",
        )
        since_date = "2019-04-05 00:00:00.000"
        jira_ts._update_timestamp(since_date)
        with self.mock_with_delay() as (delayable_cls, delayable):
            self.env["jira.account.analytic.line"].run_batch_timestamp(
                self.backend_record,
                jira_ts,
            )
            # Jira WS returns 3 worklog ids here, we expect to have 3
            # jobs delayed
            number_of_worklogs = 3
            self.assertEqual(delayable_cls.call_count, number_of_worklogs)
            # arguments passed in 'with_delay()'
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual(
                (self.env["jira.account.analytic.line"],),
                delay_args,
            )

            # Job method called after 'with_delay()'.
            self.assertEqual(delayable.import_record.call_count, number_of_worklogs)
            delay_args = delayable.import_record.call_args_list
            expected = [
                # backend, issue_id, worklog_id
                ((self.backend_record, "10102", "10100"), {"force": False}),
                ((self.backend_record, "10100", "10102"), {"force": False}),
                ((self.backend_record, "10101", "10101"), {"force": False}),
            ]
            self.assertEqual(
                sorted((args, kwargs) for args, kwargs in delay_args),
                sorted(expected),
            )

        # For worklogs, Jira returns the youngest timestamp of
        # the worklogs returned by the "updated since" method, so the
        # next import, we can reuse this timestamp as "since".
        # It has a milliseconds precision
        self.assertEqual(
            jira_ts.last_timestamp, datetime(2019, 4, 8, 12, 32, 19, 311000)
        )
