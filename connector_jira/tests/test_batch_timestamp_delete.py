# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from freezegun import freeze_time

from .common import JiraTransactionComponentCase, recorder


class TestBatchTimestampDelete(JiraTransactionComponentCase):
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
    @freeze_time("2019-04-08 14:13:10.325")
    @recorder.use_cassette
    def test_delete_batch_timestamp_analytic_line(self):
        """Import all deleted worklogs since last timestamp"""
        self._create_project_binding(
            self.project, issue_types=self.epic_issue_type, external_id="10000"
        )
        jira_ts = self.env["jira.backend.timestamp"]._timestamp_for_field(
            self.backend_record,
            "delete_analytic_line_from_date",
            "timestamp.batch.deleter",
        )
        since_date = "2019-04-05 00:00:00.000"
        jira_ts._update_timestamp(since_date)

        with self.mock_with_delay() as (delayable_cls, delayable):
            self.env["jira.account.analytic.line"].run_batch_timestamp(
                self.backend_record,
                jira_ts,
            )
            # Jira WS returns 2 worklog ids to delete here, we expect to have 2
            # jobs delayed
            number_of_worklogs = 2
            self.assertEqual(delayable_cls.call_count, number_of_worklogs)
            # arguments passed in 'with_delay()'
            delay_args, delay_kwargs = delayable_cls.call_args
            self.assertEqual(
                (self.env["jira.account.analytic.line"],),
                delay_args,
            )

            # Job method called after 'with_delay()'.
            self.assertEqual(delayable.delete_record.call_count, number_of_worklogs)
            delay_args = delayable.delete_record.call_args_list
            expected = [
                # backend, issue_id
                (
                    (self.backend_record, 10103),
                    {"only_binding": False, "set_inactive": False},
                ),
                (
                    (self.backend_record, 10104),
                    {"only_binding": False, "set_inactive": False},
                ),
            ]
            self.assertEqual(
                sorted((args, kwargs) for args, kwargs in delay_args),
                sorted(expected),
            )
            # the lines would actually be deleted by the 'delete_record' jobs

        # For worklogs, Jira returns the youngest timestamp of the worklogs
        # returned by the "deleted since" method, so the next time we look for
        # deleted worklogs, we can reuse this timestamp as "since". It has a
        # milliseconds precision
        self.assertEqual(
            jira_ts.last_timestamp, datetime(2019, 4, 8, 13, 51, 37, 945000)
        )
