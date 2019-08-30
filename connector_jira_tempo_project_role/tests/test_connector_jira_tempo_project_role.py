# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import date

from .common import recorder
from odoo.addons.connector_jira.tests.test_import_analytic_line \
    import TestImportWorklogBase
from freezegun import freeze_time


class TestImportWorklogProjectRole(TestImportWorklogBase):

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

        cls.user = cls.env['res.users'].with_context(
            no_reset_password=True
        ).create({'login': 'sorsi', 'name': 'Testing Me'})
        cls.env['hr.employee'].create({
            'name': cls.user.name, 'user_id': cls.user.id
        })
        cls._link_user(cls.user, 'sorsi')

        cls.project_manager_role = cls.env['project.role'].create({
            'name': 'Project Manager',
        })

        cls.issue_type = cls.env['jira.issue.type'].search([
            ('name', '=', 'Task'),
        ])
        cls.task2 = cls.env['project.task'].with_context(
            connector_jira=True,
        ).create({
            'name': 'My task 2',
            'project_id': cls.project.id,
        })

    @freeze_time("2019-04-29 14:13:10.325")
    @recorder.use_cassette
    def test_import_worklog_project_role(self):
        jira_worklog_id = jira_issue_id = '10000'
        binding = self._setup_import_worklog(
            self.task, jira_issue_id, jira_worklog_id)
        self.assertRecordValues(
            binding,
            [{
                'account_id': self.project.analytic_account_id.id,
                'backend_id': self.backend_record.id,
                'date': date(2019, 5, 8),
                'employee_id': self.user.employee_ids[0].id,
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
                'user_id': self.user.id,
                'role_id': self.project_manager_role.id,
            }]
        )

    @freeze_time("2019-04-29 14:13:10.325")
    @recorder.use_cassette
    def test_import_worklog_project_role_missing(self):
        jira_worklog_id = jira_issue_id = '10000'
        binding = self._setup_import_worklog(
            self.task, jira_issue_id, jira_worklog_id)
        self.assertRecordValues(
            binding,
            [{
                'account_id': self.project.analytic_account_id.id,
                'backend_id': self.backend_record.id,
                'date': date(2019, 5, 8),
                'employee_id': self.user.employee_ids[0].id,
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
                'user_id': self.user.id,
                'role_id': False,
            }]
        )

    @freeze_time("2019-04-29 14:13:10.325")
    @recorder.use_cassette
    def test_import_worklog_project_role_not_set(self):
        jira_worklog_id = jira_issue_id = '10000'
        binding = self._setup_import_worklog(
            self.task, jira_issue_id, jira_worklog_id)
        self.assertRecordValues(
            binding,
            [{
                'account_id': self.project.analytic_account_id.id,
                'backend_id': self.backend_record.id,
                'date': date(2019, 5, 8),
                'employee_id': self.user.employee_ids[0].id,
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
                'user_id': self.user.id,
                'role_id': False,
            }]
        )
