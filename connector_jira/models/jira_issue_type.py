# Copyright 2016-2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class JiraIssueType(models.Model):
    _name = "jira.issue.type"
    _inherit = "jira.binding"
    _description = "Jira Issue Type"

    name = fields.Char(required=True)
    description = fields.Char()
    backend_id = fields.Many2one(ondelete="cascade")

    def is_sync_for_project(self, project_binding):
        self.ensure_one()
        return bool(project_binding) and self in project_binding.sync_issue_type_ids

    def import_batch(self, backend, from_date=None, to_date=None):
        """Prepare a batch import of issue types from Jira

        from_date and to_date are ignored for issue types
        """
        with backend.work_on(self._name) as work:
            work.component(usage="batch.importer").run()
