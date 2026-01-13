# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, fields

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError


class JiraProjectTaskMapper(Component):
    _name = "jira.project.task.mapper"
    _inherit = "jira.import.mapper"
    _apply_on = ["jira.project.task"]

    direct = [("key", "jira_key")]

    from_fields = [("duedate", "date_deadline")]

    @mapping
    def from_attributes(self, record):
        return self.component(usage="map.from.attrs").values(record, self)

    @mapping
    def name(self, record):
        name = ""
        # On an Epic, you have 2 fields:
        #   - a field like 'customfield_10003' labelled "Epic Name"
        #   - a field 'summary' labelled "Summary"
        # The other types of tasks have only the 'summary' field, the other is
        # empty. To simplify, we always try to read the Epic Name, which
        # will always be empty for other types.
        epic_name_field = self.backend_record.epic_name_field_name
        if epic_name_field:
            name = record["fields"].get(epic_name_field) or ""
        if not name:
            name = record["fields"]["summary"]
        return {"name": name}

    @mapping
    def issue_type(self, record):
        jira_type_id = record["fields"]["issuetype"]["id"]
        binding = self.binder_for("jira.issue.type").to_internal(jira_type_id)
        return {"jira_issue_type_id": binding.id}

    @mapping
    def assignee(self, record):
        assignee = record["fields"].get("assignee")
        if not assignee:
            return {"user_ids": [fields.Command.set([])]}
        jira_key = assignee["accountId"]
        user = self.binder_for("jira.res.users").to_internal(jira_key, unwrap=True)
        if not user:
            raise MappingError(
                _(
                    'No user found with accountId "%(jira_key)s" or email "%(email)s".'
                    "You must create a user or link it manually if the "
                    "login/email differs.",
                    jira_key=jira_key,
                    email=assignee.get("emailAddress"),
                )
            )
        return {"user_ids": [fields.Command.set(user.ids)]}

    @mapping
    def description(self, record):
        return {"description": record["renderedFields"]["description"]}

    @mapping
    def project(self, record):
        proj_binding = self.options.project_binding
        project = self.binder_for("jira.project.project").unwrap_binding(proj_binding)
        values = {
            "project_id": project.id,
            "company_id": project.company_id.id,
            "jira_project_bind_id": proj_binding.id,
        }
        if not project.active:
            values["active"] = False
        return values

    @mapping
    def epic(self, record):
        if not self.options.jira_epic:
            return {}
        binder = self.binder_for("jira.project.task")
        binding = binder.to_internal(self.options.jira_epic["id"])
        return {"jira_epic_link_id": binding.id}

    @mapping
    def parent(self, record):
        jira_parent = record["fields"].get("parent")
        if not jira_parent:
            return {}
        binding = self.binder_for("jira.project.task").to_internal(jira_parent["id"])
        return {"jira_parent_id": binding.id}

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}

    @mapping
    def status(self, record):
        status_name = record["fields"].get("status", {}).get("name")
        if not status_name:
            return {"stage_id": False}
        project_binder = self.binder_for("jira.project.project")
        project = project_binder.unwrap_binding(self.options.project_binding)
        domain = [("name", "=", status_name), ("project_ids", "=", project.id)]
        return {"stage_id": self.env["project.task.type"].search(domain, limit=1).id}

    @mapping
    def time_estimate(self, record):
        est = record["fields"].get("timeoriginalestimate") or 0.0
        return {"allocated_hours": float(est) / 3600.0}

    def finalize(self, map_record, values):
        values = values.copy()
        if values.get("odoo_id"):
            # If a mapping binds the issue to an existing odoo
            # task, we should not change the project.
            # It's not only unexpected, but would fail as soon
            # as we have invoiced timesheet lines on the task.
            values.pop("project_id")
        return values
