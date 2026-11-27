# Copyright 2016-Today Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class JiraTaskProjectMatcher(Component):
    _inherit = "jira.task.project.matcher"

    def find_project_binding(self, jira_task_data, unwrap=False):
        component = self.component(usage="organization.from.task")
        binder = self.binder_for("jira.organization")
        org_ids = set()
        for j_org_id in component.get_jira_org_ids(jira_task_data):
            org_ids.update(binder.to_internal(j_org_id).ids)
        return self.binder_for("jira.project.project").to_internal(
            jira_task_data["fields"]["project"]["id"],
            unwrap=unwrap,
            organizations=self.env["jira.organization"].browse(org_ids),
        )
