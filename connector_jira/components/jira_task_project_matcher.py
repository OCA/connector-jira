# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo.addons.component.core import Component


class JiraTaskProjectMatcher(Component):
    _name = "jira.task.project.matcher"
    _inherit = ["jira.base"]
    _usage = "jira.task.project.matcher"

    def find_project_binding(self, jira_task_data, unwrap=False):
        jira_project_id = jira_task_data["fields"]["project"]["id"]
        binder = self.binder_for("jira.project.project")
        return binder.to_internal(jira_project_id, unwrap=unwrap)

    def fallback_project_for_worklogs(self):
        return self.backend_record.worklog_fallback_project_id
