# Copyright 2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import date, timedelta

from .common import JiraTransactionComponentCase, recorder


class TestImportWorklogBase(JiraTransactionComponentCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_issue_type_bindings()
        cls.project = cls.env["project.project"].create({"name": "Jira Project"})
        cls.task = cls.env["project.task"].create(
            {"name": "My task", "project_id": cls.project.id}
        )
        cls.project_binding = cls._create_project_binding(
            cls.project,
            issue_types=cls.env["jira.issue.type"].search([]),
            external_id="10000",
        )
        cls.epic_issue_type = cls.env["jira.issue.type"].search([("name", "=", "Epic")])
        # Warning: if you add new tests or change the cassettes
        # you might need to change the username
        cls._link_user(cls.env.user, "gbaconnier")
        cls.env["hr.employee"].create(
            {"name": "Test Employee", "user_id": cls.env.user.id}
        )
        cls.fallback_project = cls.env["project.project"].create(
            {"name": "Test Fallback Project"}
        )
        cls.backend_record.write(
            {"worklog_fallback_project_id": cls.fallback_project.id}
        )

    def _setup_import_worklog(self, task, jira_issue_id, jira_worklog_id=None):
        self._create_task_binding(task, external_id=jira_issue_id)
        jira_worklog_id = jira_worklog_id or jira_issue_id
        self.env["jira.account.analytic.line"].import_record(
            self.backend_record, jira_issue_id, jira_worklog_id
        )
        binding = self.env["jira.account.analytic.line"].search(
            [
                ("backend_id", "=", self.backend_record.id),
                ("external_id", "=", jira_worklog_id),
            ]
        )
        self.assertEqual(len(binding), 1)
        return binding


class TestImportAccountAnalyticLine(TestImportWorklogBase):
    @recorder.use_cassette
    def test_import_worklog(self):
        """Import a worklog on a task existing in Odoo on activated project"""
        self._test_import_worklog(
            expected_project=self.project, expected_task=self.task
        )

    @recorder.use_cassette("test_import_worklog.yaml")
    def test_import_worklog_deactivated_project(self):
        """
        Import a worklog on a task existing in Odoo on deactivated project
        """
        self.project.write({"active": False})
        self._test_import_worklog(
            expected_project=self.fallback_project, expected_task=False
        )

    @recorder.use_cassette("test_import_worklog.yaml")
    def test_import_worklog_deactivated_task(self):
        """
        Import a worklog on a task existing in Odoo on deactivated task
        """
        self.task.write({"active": False})
        self._test_import_worklog(expected_project=self.project, expected_task=False)

    def _test_import_worklog(self, expected_project, expected_task):
        jira_worklog_id = jira_issue_id = "10000"
        binding = self._setup_import_worklog(self.task, jira_issue_id, jira_worklog_id)
        self.assertRecordValues(
            binding,
            [
                {
                    "account_id": expected_project.analytic_account_id.id,
                    "backend_id": self.backend_record.id,
                    "date": date(2019, 4, 4),
                    "employee_id": self.env.user.employee_ids[0].id,
                    "external_id": jira_worklog_id,
                    "jira_epic_issue_key": False,
                    "jira_issue_id": jira_issue_id,
                    "jira_issue_key": "TEST-1",
                    "jira_issue_type_id": self.epic_issue_type.id,
                    "name": "write tests",
                    "project_id": expected_project.id,
                    "tag_ids": [],
                    "task_id": expected_task.id if expected_task else False,
                    "unit_amount": 1.0,
                    "user_id": self.env.user.id,
                }
            ],
        )

    def test_reimport_worklog(self):
        jira_issue_id = "10000"
        jira_worklog_id = "10000"
        with recorder.use_cassette("test_import_worklog.yaml"):
            binding = self._setup_import_worklog(
                self.task,
                jira_issue_id,
                jira_worklog_id,
            )
        write_date = binding.write_date - timedelta(seconds=1)
        binding.write({"write_date": write_date})
        with recorder.use_cassette("test_import_worklog.yaml"):
            binding.force_reimport()
        self.assertEqual(binding.write_date, write_date)

    @recorder.use_cassette("test_import_worklog.yaml")
    def test_import_worklog_naive(self):
        jira_worklog_id = jira_issue_id = "10000"
        self.backend_record.worklog_date_timezone_mode = "naive"
        binding = self._setup_import_worklog(self.task, jira_issue_id, jira_worklog_id)
        self.assertRecordValues(
            binding,
            [
                {
                    "account_id": self.project.analytic_account_id.id,
                    "backend_id": self.backend_record.id,
                    "date": date(2019, 4, 4),
                    "employee_id": self.env.user.employee_ids[0].id,
                    "external_id": jira_worklog_id,
                    "jira_epic_issue_key": False,
                    "jira_issue_id": jira_issue_id,
                    "jira_issue_key": "TEST-1",
                    "jira_issue_type_id": self.epic_issue_type.id,
                    "name": "write tests",
                    "project_id": self.project.id,
                    "tag_ids": [],
                    "task_id": self.task.id if self.task else False,
                    "unit_amount": 1.0,
                    "user_id": self.env.user.id,
                }
            ],
        )

    @recorder.use_cassette("test_import_worklog.yaml")
    def test_import_worklog_user(self):
        jira_worklog_id = jira_issue_id = "10000"
        self.backend_record.worklog_date_timezone_mode = "user"
        binding = self._setup_import_worklog(self.task, jira_issue_id, jira_worklog_id)
        self.assertRecordValues(
            binding,
            [
                {
                    "account_id": self.project.analytic_account_id.id,
                    "backend_id": self.backend_record.id,
                    "date": date(2019, 4, 3),
                    "employee_id": self.env.user.employee_ids[0].id,
                    "external_id": jira_worklog_id,
                    "jira_epic_issue_key": False,
                    "jira_issue_id": jira_issue_id,
                    "jira_issue_key": "TEST-1",
                    "jira_issue_type_id": self.epic_issue_type.id,
                    "name": "write tests",
                    "project_id": self.project.id,
                    "tag_ids": [],
                    "task_id": self.task.id if self.task else False,
                    "unit_amount": 1.0,
                    "user_id": self.env.user.id,
                }
            ],
        )

    @recorder.use_cassette("test_import_worklog.yaml")
    def test_import_worklog_specific(self):
        jira_worklog_id = jira_issue_id = "10000"
        self.backend_record.worklog_date_timezone_mode = "specific"
        self.backend_record.worklog_date_timezone = "Europe/London"
        binding = self._setup_import_worklog(self.task, jira_issue_id, jira_worklog_id)
        self.assertRecordValues(
            binding,
            [
                {
                    "account_id": self.project.analytic_account_id.id,
                    "backend_id": self.backend_record.id,
                    "date": date(2019, 4, 3),
                    "employee_id": self.env.user.employee_ids[0].id,
                    "external_id": jira_worklog_id,
                    "jira_epic_issue_key": False,
                    "jira_issue_id": jira_issue_id,
                    "jira_issue_key": "TEST-1",
                    "jira_issue_type_id": self.epic_issue_type.id,
                    "name": "write tests",
                    "project_id": self.project.id,
                    "tag_ids": [],
                    "task_id": self.task.id if self.task else False,
                    "unit_amount": 1.0,
                    "user_id": self.env.user.id,
                }
            ],
        )

    def _test_import_worklog_epic_link_on_epic(self, expected_project, expected_task):
        jira_worklog_id = jira_issue_id = "10000"
        self.backend_record.epic_link_on_epic = True
        binding = self._setup_import_worklog(self.task, jira_issue_id, jira_worklog_id)
        self.assertRecordValues(
            binding,
            [
                {
                    "account_id": expected_project.analytic_account_id.id,
                    "backend_id": self.backend_record.id,
                    "date": "2019-04-04",
                    "employee_id": self.env.user.employee_ids[0].id,
                    "external_id": jira_worklog_id,
                    "jira_epic_issue_key": "TEST-1",
                    "jira_issue_id": jira_issue_id,
                    "jira_issue_key": "TEST-1",
                    "jira_issue_type_id": self.epic_issue_type.id,
                    "name": "write tests",
                    "project_id": expected_project.id,
                    "tag_ids": [],
                    "task_id": expected_task.id if expected_task else False,
                    "unit_amount": 1.0,
                    "user_id": self.env.user.id,
                }
            ],
        )
