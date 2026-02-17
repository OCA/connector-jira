# Copyright 2016-Today Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class JiraOrganizationsFromTask(Component):
    _name = "jira.organization.from.task"
    _inherit = ["jira.base"]
    _usage = "organization.from.task"

    def get_jira_org_ids(self, jira_task_data):
        if fields := jira_task_data.get("fields", {}):
            if org_fname := self.backend_record.organization_field_name:
                if recs := fields.get(org_fname):
                    return [r["id"] for r in recs]
        return []
