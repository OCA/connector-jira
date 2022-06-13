# Copyright 2016-Today Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class ProjectTaskProjectMatcher(Component):
    _inherit = "jira.task.project.matcher"

    def find_project_binding(self, jira_task_data, unwrap=False):
        organizations = self.env["jira.organization"].browse()
        jira_org_ids = self.component(usage="organization.from.task").get_jira_org_ids(
            jira_task_data
        )
        binder = self.binder_for("jira.organization")
        for jira_org_id in jira_org_ids:
            organizations |= binder.to_internal(jira_org_id)
        jira_project_id = jira_task_data["fields"]["project"]["id"]
        binder = self.binder_for("jira.project.project")
        return binder.to_internal(
            jira_project_id,
            unwrap=unwrap,
            organizations=organizations,
        )


class OrganizationsFromTask(Component):
    _name = "jira.organization.from.task"
    _inherit = ["jira.base"]
    _usage = "organization.from.task"

    def get_jira_org_ids(self, jira_task_data):
        organization_field_name = self.backend_record.organization_field_name
        if not organization_field_name:
            return []

        task_fields = jira_task_data.get("fields", {})
        return [rec["id"] for rec in task_fields.get(organization_field_name) or []]


class ProjectTaskImporter(Component):
    _inherit = "jira.project.task.importer"

    def _get_external_data(self):
        """Return the raw Jira data for ``self.external_id``"""
        result = super()._get_external_data()
        return result

    def _import_dependencies(self):
        """Import the dependencies for the record"""
        res = super()._import_dependencies()
        jira_org_ids = self.component(usage="organization.from.task").get_jira_org_ids(
            self.external_record
        )
        for jira_org_id in jira_org_ids:
            self._import_dependency(jira_org_id, "jira.organization")
        return res
