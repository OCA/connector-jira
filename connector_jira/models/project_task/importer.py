# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError


class ProjectTaskMapper(Component):
    _name = "jira.project.task.mapper"
    _inherit = "jira.import.mapper"
    _apply_on = ["jira.project.task"]

    direct = [
        ("key", "jira_key"),
    ]

    from_fields = [
        ("duedate", "date_deadline"),
    ]

    @mapping
    def from_attributes(self, record):
        return self.component(usage="map.from.attrs").values(record, self)

    @mapping
    def name(self, record):
        # On an Epic, you have 2 fields:

        #     a field like 'customfield_10003' labelled "Epic Name"
        #     a field 'summary' labelled "Sumarry"

        # The other types of tasks have only the 'summary' field, the other is
        # empty. To simplify, we always try to read the Epic Name, which
        # will always be empty for other types.
        epic_name_field = self.backend_record.epic_name_field_name
        name = False
        if epic_name_field:
            name = record["fields"].get(epic_name_field)
        if not name:
            name = record["fields"]["summary"]
        return {"name": name}

    @mapping
    def issue_type(self, record):
        binder = self.binder_for("jira.issue.type")
        jira_type_id = record["fields"]["issuetype"]["id"]
        binding = binder.to_internal(jira_type_id)
        return {"jira_issue_type_id": binding.id}

    @mapping
    def assignee(self, record):
        assignee = record["fields"].get("assignee")
        if not assignee:
            return {"user_ids": False}
        jira_key = assignee["key"]
        binder = self.binder_for("jira.res.users")
        user = binder.to_internal(jira_key, unwrap=True)
        if not user:
            email = assignee["emailAddress"]
            raise MappingError(
                _(
                    'No user found with login "%(jira_key)s" or email "%(email)s".'
                    "You must create a user or link it manually if the "
                    "login/email differs.",
                    jira_key=jira_key,
                    email=email,
                )
            )
        return {"user_id": user.id}

    @mapping
    def description(self, record):
        return {"description": record["renderedFields"]["description"]}

    @mapping
    def project(self, record):
        binder = self.binder_for("jira.project.project")
        project = binder.unwrap_binding(self.options.project_binding)
        values = {
            "project_id": project.id,
            "company_id": project.company_id.id,
            "jira_project_bind_id": self.options.project_binding.id,
        }
        if not project.active:
            values["active"] = False
        return values

    @mapping
    def epic(self, record):
        if not self.options.jira_epic:
            return {}
        jira_epic_id = self.options.jira_epic["id"]
        binder = self.binder_for("jira.project.task")
        binding = binder.to_internal(jira_epic_id)
        return {"jira_epic_link_id": binding.id}

    @mapping
    def parent(self, record):
        jira_parent = record["fields"].get("parent")
        if not jira_parent:
            return {}
        jira_parent_id = jira_parent["id"]
        binder = self.binder_for("jira.project.task")
        binding = binder.to_internal(jira_parent_id)
        return {"jira_parent_id": binding.id}

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}

    @mapping
    def status(self, record):
        status = record["fields"].get("status", {})
        status_name = status.get("name")
        if not status_name:
            return {"stage_id": False}
        project_binder = self.binder_for("jira.project.project")
        project_id = project_binder.unwrap_binding(self.options.project_binding)
        stage = self.env["project.task.type"].search(
            [("name", "=", status_name), ("project_ids", "=", project_id.id)],
            limit=1,
        )
        return {"stage_id": stage.id}

    @mapping
    def time_estimate(self, record):
        original_estimate = record["fields"].get("timeoriginalestimate")
        if not original_estimate:
            return {"planned_hours": False}
        return {"planned_hours": float(original_estimate) / 3600.0}

    def finalize(self, map_record, values):
        values = values.copy()
        if values.get("odoo_id"):
            # If a mapping binds the issue to an existing odoo
            # task, we should not change the project.
            # It's not only unexpected, but would fail as soon
            # as we have invoiced timesheet lines on the task.
            values.pop("project_id")
        return values


class ProjectTaskBatchImporter(Component):
    """Import the Jira tasks

    For every id in in the list of tasks, a delayed job is created.
    Import from a date
    """

    _name = "jira.project.task.batch.importer"
    _inherit = ["jira.timestamp.batch.importer"]
    _apply_on = ["jira.project.task"]


class ProjectTaskProjectMatcher(Component):
    _name = "jira.task.project.matcher"
    _inherit = ["jira.base"]
    _usage = "jira.task.project.matcher"

    def find_project_binding(self, jira_task_data, unwrap=False):
        jira_project_id = jira_task_data["fields"]["project"]["id"]
        binder = self.binder_for("jira.project.project")
        return binder.to_internal(jira_project_id, unwrap=unwrap)

    def fallback_project_for_worklogs(self):
        return self.backend_record.worklog_fallback_project_id


class ProjectTaskImporter(Component):
    _name = "jira.project.task.importer"
    _inherit = ["jira.importer"]
    _apply_on = ["jira.project.task"]

    def __init__(self, work_context):
        super().__init__(work_context)
        self.jira_epic = None
        self.project_binding = None

    def _get_external_data(self):
        """Return the raw Jira data for ``self.external_id``"""
        result = super()._get_external_data()
        epic_field_name = self.backend_record.epic_link_field_name
        if epic_field_name:
            issue_adapter = self.component(
                usage="backend.adapter", model_name="jira.project.task"
            )
            epic_key = result["fields"][epic_field_name]
            if epic_key:
                self.jira_epic = issue_adapter.read(epic_key)
        return result

    def _find_project_binding(self):
        matcher = self.component(usage="jira.task.project.matcher")
        self.project_binding = matcher.find_project_binding(self.external_record)

    def _is_issue_type_sync(self):
        project_binding = self.project_binding
        task_sync_type_id = self.external_record["fields"]["issuetype"]["id"]
        task_sync_type_binder = self.binder_for("jira.issue.type")
        task_sync_type_binding = task_sync_type_binder.to_internal(
            task_sync_type_id,
        )
        return task_sync_type_binding.is_sync_for_project(project_binding)

    def _create_data(self, map_record, **kwargs):
        return super()._create_data(
            map_record,
            jira_epic=self.jira_epic,
            project_binding=self.project_binding,
            **kwargs
        )

    def _update_data(self, map_record, **kwargs):
        return super()._update_data(
            map_record,
            jira_epic=self.jira_epic,
            project_binding=self.project_binding,
            **kwargs
        )

    def _import(self, binding, **kwargs):
        # called at the beginning of _import because we must be sure
        # that dependencies are there (project and issue type)
        self._find_project_binding()
        if not self._is_issue_type_sync():
            return _("Project or issue type is not synchronized.")
        return super()._import(binding, **kwargs)

    def _import_dependency_assignee(self):
        jira_assignee = self.external_record["fields"].get("assignee") or {}
        jira_key = jira_assignee.get("key")
        self._import_dependency(jira_key, "jira.res.users", record=jira_assignee)

    def _import_dependency_issue_type(self):
        jira_issue_type = self.external_record["fields"]["issuetype"]
        jira_issue_type_id = jira_issue_type["id"]
        self._import_dependency(
            jira_issue_type_id, "jira.issue.type", record=jira_issue_type
        )

    def _import_dependency_parent(self):
        jira_parent = self.external_record["fields"].get("parent")
        if jira_parent:
            jira_parent_id = jira_parent["id"]
            self._import_dependency(jira_parent_id, "jira.project.task")

    def _import_dependency_epic(self):
        if self.jira_epic:
            self._import_dependency(
                self.jira_epic["id"], "jira.project.task", record=self.jira_epic
            )

    def _import_dependencies(self):
        """Import the dependencies for the record"""
        self._import_dependency_assignee()
        self._import_dependency_issue_type()
        self._import_dependency_parent()
        self._import_dependency_epic()
