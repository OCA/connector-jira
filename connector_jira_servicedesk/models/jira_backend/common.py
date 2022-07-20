# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class JiraBackend(models.Model):
    _inherit = "jira.backend"

    organization_ids = fields.One2many(
        comodel_name="jira.organization",
        inverse_name="backend_id",
        string="Organizations",
        readonly=True,
    )

    organization_field_name = fields.Char(
        string="Organization Field",
        help="The 'Organization' field on JIRA is a custom field. "
        "The name of the field is something like 'customfield_10002'. ",
    )

    @api.model
    def _selection_project_template(self):
        selection = super()._selection_project_template()
        selection += [
            ("Basic", "Basic (Service Desk)"),
            ("IT Service Desk", "IT Service Desk (Service Desk)"),
            ("Customer service", "Customer Service (Service Desk)"),
        ]
        return selection

    def import_organization(self):
        self.env["jira.organization"].with_delay(
            channel="root.connector_jira.import"
        ).import_batch(self)
        return True

    def activate_organization(self):
        """Get organization field name from JIRA web-service"""
        self.ensure_one()
        org_field = "com.atlassian.servicedesk:sd-customer-organizations"
        with self.work_on("jira.backend") as work:
            adapter = work.component(usage="backend.adapter")
            jira_fields = adapter.list_fields()
            for field in jira_fields:
                custom_ref = field.get("schema", {}).get("custom")
                if custom_ref == org_field:
                    self.organization_field_name = field["id"]
                    break
