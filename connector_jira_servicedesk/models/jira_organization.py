# Copyright 2016-Today Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo import fields, models


class JiraOrganization(models.Model):
    _name = "jira.organization"
    _inherit = "jira.binding"
    _description = "Jira Organization"

    name = fields.Char(required=True, readonly=True)
    backend_id = fields.Many2one(ondelete="cascade")
    project_ids = fields.Many2many(comodel_name="jira.project.project")

    def import_batch(self, backend, from_date=None, to_date=None):
        """Prepare a batch import of organization from Jira

        from_date and to_date are ignored for organization
        """
        with backend.work_on(self._name) as work:
            importer = work.component(usage="batch.importer")
            importer.run()
