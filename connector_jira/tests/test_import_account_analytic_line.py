# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from .common import recorder, JiraTransactionCase


class TestImportAccountAnalyticLine(JiraTransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_issue_type_bindings()
        cls.project = cls.env['project.project'].create({
            'name': 'Test Project',
        })
        cls.project_binding = cls._create_project_binding(
            cls.project,
            issue_types=cls.env['jira.issue.type'].search([]),
            external_id='10000'
        )
        cls.epic_issue_type = cls.env['jira.issue.type'].search([
            ('name', '=', 'Epic'),
        ])
        cls.task = cls.env['project.task'].create({
            'name': 'My task',
            'project_id': cls.project.id,
        })
        cls._link_user(cls.env.user, 'gbaconnier')

    @recorder.use_cassette
    def test_import_worklog(self):
        """Import a worklog on a task existing in Odoo"""
        self._create_task_binding(
            self.task, external_id='10000'
        )
        jira_issue_id = '10000'
        jira_worklog_id = '10000'
        self.env['jira.account.analytic.line'].import_record(
            self.backend_record, jira_issue_id, jira_worklog_id
        )
        binding = self.env['jira.account.analytic.line'].search([
            ('backend_id', '=', self.backend_record.id),
            ('external_id', '=', jira_worklog_id)
        ])
        self.assertEqual(len(binding), 1)

        self.assertRecordValues(
            binding,
            [{
                'account_id': self.project.analytic_account_id.id,
                'backend_id': self.backend_record.id,
                'date': '2019-04-04',
                'employee_id': self.env.user.employee_ids[0].id,
                'external_id': jira_worklog_id,
                'jira_epic_issue_key': False,
                'jira_issue_id': jira_issue_id,
                'jira_issue_key': 'TEST-1',
                'jira_issue_type_id': self.epic_issue_type.id,
                'name': 'write tests',
                'project_id': self.project.id,
                'tag_ids': [],
                'task_id': self.task.id,
                'unit_amount': 1.0,
                'user_id': self.env.user.id,
            }]
        )
