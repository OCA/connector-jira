# Copyright 2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import exceptions

from .common import JiraTransactionComponentCase, recorder


class TestImportTask(JiraTransactionComponentCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_issue_type_bindings()
        cls.epic_issue_type = cls.env["jira.issue.type"].search([("name", "=", "Epic")])
        cls.task_issue_type = cls.env["jira.issue.type"].search([("name", "=", "Task")])
        cls.subtask_issue_type = cls.env["jira.issue.type"].search(
            [("name", "=", "Sub-task")]
        )
        cls.project = cls.env["project.project"].create({"name": "Jira Project"})
        cls.env["project.task.type"].create(
            {"name": "To Do", "sequence": 1, "project_ids": [(4, cls.project.id)]}
        )

    @recorder.use_cassette
    def test_import_task_epic(self):
        """
        Import Epic task where we sync this type issue on activated project
        """
        self._test_import_task_epic(expected_active=True)

    @recorder.use_cassette("test_import_task_epic.yaml")
    def test_import_task_epic_deactivated_project(self):
        """
        Import Epic task where we sync this type issue on deactivated project
        """
        self.project.write({"active": False})
        self._test_import_task_epic(expected_active=False)

    def _test_import_task_epic(self, expected_active):
        self._create_project_binding(
            self.project, issue_types=self.epic_issue_type, external_id="10000"
        )
        jira_issue_id = "10000"
        self.env["jira.project.task"].import_record(self.backend_record, jira_issue_id)
        binding = (
            self.env["jira.project.task"]
            .with_context(active_test=False)
            .search(
                [
                    ("backend_id", "=", self.backend_record.id),
                    ("external_id", "=", jira_issue_id),
                ]
            )
        )
        self.assertEqual(len(binding), 1)

        self.assertEqual(binding.jira_key, "TEST-1")
        self.assertEqual(binding.jira_issue_type_id, self.epic_issue_type)
        self.assertFalse(binding.jira_epic_link_id)
        self.assertFalse(binding.jira_parent_id)

        self.assertEqual(binding.odoo_id.active, expected_active)
        self.assertEqual(binding.odoo_id.stage_id.name, "To Do")

        with self.assertRaises(exceptions.UserError):
            binding.odoo_id.active = not expected_active

        with self.assertRaises(exceptions.UserError):
            binding.odoo_id.unlink()

    @recorder.use_cassette
    def test_import_task_type_not_synced(self):
        """Import ask where we do not sync this type issue: ignored"""
        self._create_project_binding(self.project, external_id="10000")
        jira_issue_id = "10000"
        self.env["jira.project.task"].import_record(self.backend_record, jira_issue_id)
        binding = self.env["jira.project.task"].search(
            [
                ("backend_id", "=", self.backend_record.id),
                ("external_id", "=", jira_issue_id),
            ]
        )
        self.assertEqual(len(binding), 0)

    @recorder.use_cassette
    def test_import_task_parents(self):
        """Import Epic/Task/Subtask recursively"""
        self._create_project_binding(
            self.project,
            issue_types=(
                self.epic_issue_type + self.task_issue_type + self.subtask_issue_type
            ),
            external_id="10000",
        )

        projects_by_name = self.env["project.project"].name_search("TEST")
        self.assertEqual(len(projects_by_name), 1)

        jira_subtask_issue_id = "10002"
        self.env["jira.project.task"].import_record(
            self.backend_record, jira_subtask_issue_id
        )

        binding = self.env["jira.project.task"].search(
            [
                ("backend_id", "=", self.backend_record.id),
                ("external_id", "=", jira_subtask_issue_id),
            ]
        )
        self.assertEqual(len(binding), 1)

        self.assertEqual(binding.jira_key, "TEST-3")
        self.assertEqual(binding.name, "Subtask1")
        self.assertEqual(binding.jira_issue_type_id, self.subtask_issue_type)
        self.assertTrue(binding.jira_parent_id)

        task_binding = binding.jira_parent_id
        self.assertEqual(task_binding.jira_key, "TEST-2")
        self.assertEqual(task_binding.name, "Task1")
        self.assertEqual(task_binding.jira_issue_type_id, self.task_issue_type)
        self.assertTrue(task_binding.jira_epic_link_id)
        self.assertAlmostEqual(task_binding.odoo_id.planned_hours, 4.5)

        epic_binding = task_binding.jira_epic_link_id
        self.assertEqual(epic_binding.jira_key, "TEST-1")
        self.assertEqual(epic_binding.name, "Epic1")
        self.assertEqual(epic_binding.jira_issue_type_id, self.epic_issue_type)

        tasks_by_name = self.env["project.task"].name_search("TEST-3")
        self.assertEqual(len(tasks_by_name), 1)
        self.assertEqual(tasks_by_name[0][0], binding.odoo_id.id)

    def test_task_restrict_create(self):
        self._create_project_binding(
            self.project,
            issue_types=self.env["jira.issue.type"].search([]),
            external_id="10000",
        )
        with self.assertRaises(exceptions.UserError):
            self.env["project.task"].create(
                {"name": "My task", "project_id": self.project.id}
            )
