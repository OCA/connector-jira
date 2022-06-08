# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from .common import JiraTransactionComponentCase, recorder


class TestImportIssueType(JiraTransactionComponentCase):
    @recorder.use_cassette
    def test_import_issue_type_batch(self):
        issue_types = self.env["jira.issue.type"].search([])
        self.assertEqual(len(issue_types), 0)
        self.env["jira.issue.type"].import_batch(
            self.backend_record,
        )
        issue_types = self.env["jira.issue.type"].search([])
        self.assertEqual(len(issue_types), 5)

    def test_import_is_issue_type_sync(self):
        self._create_issue_type_bindings()

        epic_issue_type = self.env["jira.issue.type"].search([("name", "=", "Epic")])
        task_issue_type = self.env["jira.issue.type"].search([("name", "=", "Task")])

        project = self.env["project.project"].create({"name": "Jira Project"})
        project_binding = self._create_project_binding(
            project,
            issue_types=epic_issue_type,
        )

        self.assertTrue(epic_issue_type.is_sync_for_project(project_binding))
        self.assertFalse(task_issue_type.is_sync_for_project(project_binding))
