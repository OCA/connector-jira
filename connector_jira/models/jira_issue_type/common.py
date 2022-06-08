# Copyright 2016-2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

from odoo.addons.component.core import Component


class JiraIssueType(models.Model):
    _name = "jira.issue.type"
    _inherit = "jira.binding"
    _description = "Jira Issue Type"

    name = fields.Char(required=True, readonly=True)
    description = fields.Char(readonly=True)
    backend_id = fields.Many2one(ondelete="cascade")

    def is_sync_for_project(self, project_binding):
        self.ensure_one()
        if not project_binding:
            return False
        return self in project_binding.sync_issue_type_ids

    def import_batch(self, backend, from_date=None, to_date=None):
        """Prepare a batch import of issue types from Jira

        from_date and to_date are ignored for issue types
        """
        with backend.work_on(self._name) as work:
            importer = work.component(usage="batch.importer")
            importer.run()


class IssueTypeAdapter(Component):
    _name = "jira.issue.type.adapter"
    _inherit = ["jira.webservice.adapter"]
    _apply_on = ["jira.issue.type"]

    def read(self, id_):
        # pylint: disable=W8106
        with self.handle_404():
            return self.client.issue_type(id_).raw

    def search(self):
        issues = self.client.issue_types()
        return [issue.id for issue in issues]
