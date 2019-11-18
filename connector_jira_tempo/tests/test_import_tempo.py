# Copyright 2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import date

from .common import recorder
from odoo.addons.connector_jira.tests.test_import_analytic_line \
    import TestImportWorklogBase
from freezegun import freeze_time


class TestImportWorklogStatus(TestImportWorklogBase):

    # Warning: if you add new tests or change the cassettes
    # you might need to change these values
    # to make issue types match
    _base_issue_types = [
        ("Task", "10003"),
        ("Sub-task", "10000"),
        ("Story", "10002"),
        ("Bug", "10004"),
        ("Epic", "10001"),
    ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Warning: if you add new tests or change the cassettes
        # you might need to change the team ID and the username
        cls.backend_record.jira_company_team_id = 1

        # need a user for worklog + a user as TS approval manager on JIRA
        cls.user1 = cls.env['res.users'].with_context(
            no_reset_password=True
        ).create({'login': 'sorsi', 'name': 'Testing Me'})
        cls.env['hr.employee'].create({
            'name': cls.user1.name, 'user_id': cls.user1.id
        })
        cls._link_user(cls.user1, 'sorsi')

        cls.user2 = cls.env['res.users'].with_context(
            no_reset_password=True
        ).create({'login': 'manager', 'name': 'Testing Him'})
        cls.env['hr.employee'].create({
            'name': cls.user2.name, 'user_id': cls.user2.id
        })
        cls._link_user(cls.user2, 'manager')

        cls.issue_type = cls.env['jira.issue.type'].search([
            ('name', '=', 'Task'),
        ])
        cls.task2 = cls.env['project.task'].with_context(
            connector_jira=True,
        ).create({
            'name': 'My task 2',
            'project_id': cls.project.id,
        })

    # note: when you are recording tests with VCR, Jira
    # will reject any call when you pretend to have a time too
    # different from now(). So adjust this date be rougly equal
    # to now().
    @freeze_time("2019-04-29 14:13:10.325")
    @recorder.use_cassette
    def test_import_worklog_status(self):
        jira_worklog_id = jira_issue_id = '10000'
        binding = self._setup_import_worklog(
            self.task, jira_issue_id, jira_worklog_id)
        self.assertRecordValues(
            binding,
            [{
                'account_id': self.project.analytic_account_id.id,
                'backend_id': self.backend_record.id,
                'date': date(2019, 5, 8),
                'employee_id': self.user1.employee_ids[0].id,
                'external_id': jira_worklog_id,
                'jira_epic_issue_key': False,
                'jira_issue_id': jira_issue_id,
                'jira_issue_key': 'SIMO-1',
                'jira_issue_type_id': self.issue_type.id,
                'name': 'testing this thing',
                'project_id': self.project.id,
                'tag_ids': [],
                'task_id': self.task.id,
                'unit_amount': 1.0,
                'user_id': self.user1.id,
                'jira_tempo_status': 'open',
            }]
        )

    @freeze_time("2019-05-09 09:34:42.325")
    @recorder.use_cassette
    def test_import_worklog_status_update(self):
        jira_worklog_id = jira_issue_id = '10000'
        binding = self._setup_import_worklog(
            self.task, jira_issue_id, jira_worklog_id)
        jira_worklog_id = jira_issue_id = '10001'
        binding2 = self._setup_import_worklog(
            self.task2, jira_issue_id, jira_worklog_id)
        self.backend_record \
            ._scheduler_sync_tempo_timesheets_approval_status()
        self.assertEqual(binding.jira_tempo_status, 'waiting_for_approval')
        self.assertEqual(binding2.jira_tempo_status, 'waiting_for_approval')

    @freeze_time("2019-05-09 09:34:42.325")
    @recorder.use_cassette
    def test_import_worklog_status_update2(self):
        jira_worklog_id = jira_issue_id = '10000'
        binding = self._setup_import_worklog(
            self.task, jira_issue_id, jira_worklog_id)
        jira_worklog_id = jira_issue_id = '10001'
        binding2 = self._setup_import_worklog(
            self.task2, jira_issue_id, jira_worklog_id)
        self.backend_record \
            ._scheduler_sync_tempo_timesheets_approval_status()
        self.assertEqual(binding.jira_tempo_status, 'approved')
        self.assertEqual(binding2.jira_tempo_status, 'approved')
