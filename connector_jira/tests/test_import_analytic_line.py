# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from .common import recorder, JiraSavepointCase


class TestImportWorklogBase(JiraSavepointCase):

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
        # Warning: if you add new tests or change the cassettes
        # you might need to change the username
        cls._link_user(cls.env.user, 'gbaconnier')
        cls.fallback_project = cls.env['project.project'].create({
            'name': 'Test Fallback Project',
        })
        cls.backend_record.write({
            'worklog_fallback_project_id': cls.fallback_project.id,
        })

    def _setup_import_worklog(self, task, jira_issue_id, jira_worklog_id=None):
        self._create_task_binding(
            task, external_id=jira_issue_id
        )
        jira_worklog_id = jira_worklog_id or jira_issue_id
        self.env['jira.account.analytic.line'].import_record(
            self.backend_record, jira_issue_id, jira_worklog_id
        )
        binding = self.env['jira.account.analytic.line'].search([
            ('backend_id', '=', self.backend_record.id),
            ('external_id', '=', jira_worklog_id)
        ])
        self.assertEqual(len(binding), 1)
        return binding


class TestImportAccountAnalyticLine(TestImportWorklogBase):

    @recorder.use_cassette
    def test_import_worklog(self):
        """Import a worklog on a task existing in Odoo on activated project"""
        self._test_import_worklog(expected_project=self.project,
                                  expected_task=self.task)

    @recorder.use_cassette('test_import_worklog.yaml')
    def test_import_worklog_deactivated_project(self):
        """
        Import a worklog on a task existing in Odoo on deactivated project
        """
        self.project.write({'active': False})
        self._test_import_worklog(expected_project=self.fallback_project,
                                  expected_task=False)

    @recorder.use_cassette('test_import_worklog.yaml')
    def test_import_worklog_deactivated_task(self):
        """
        Import a worklog on a task existing in Odoo on deactivated task
        """
        self.task.write({'active': False})
        self._test_import_worklog(expected_project=self.project,
                                  expected_task=False)

    def _test_import_worklog(self, expected_project, expected_task):
        jira_worklog_id = jira_issue_id = '10000'
        binding = self._setup_import_worklog(
            self.task, jira_issue_id, jira_worklog_id)
        self.assertRecordValues(
            binding,
            [{
                'account_id': expected_project.analytic_account_id.id,
                'backend_id': self.backend_record.id,
                'date': '2019-04-04',
                'employee_id': self.env.user.employee_ids[0].id,
                'external_id': jira_worklog_id,
                'jira_epic_issue_key': False,
                'jira_issue_id': jira_issue_id,
                'jira_issue_key': 'TEST-1',
                'jira_issue_type_id': self.epic_issue_type.id,
                'name': 'write tests',
                'project_id': expected_project.id,
                'tag_ids': [],
                'task_id': expected_task.id if expected_task else False,
                'unit_amount': 1.0,
                'user_id': self.env.user.id,
            }]
        )
