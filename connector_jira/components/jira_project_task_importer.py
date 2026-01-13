# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class JiraProjectTaskImporter(Component):
    _name = "jira.project.task.importer"
    _inherit = ["jira.importer"]
    _apply_on = ["jira.project.task"]

    def __init__(self, work_context):
        super().__init__(work_context)
        self.jira_epic = None
        self.project_binding = None

    def _get_external_data(self):
        # OVERRIDE: return the raw Jira data for ``self.external_id``
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
        type_id = self.external_record["fields"]["issuetype"]["id"]
        binding = self.binder_for("jira.issue.type").to_internal(type_id)
        return binding.is_sync_for_project(self.project_binding)

    def _create_data(self, map_record, **kwargs):
        return super()._create_data(
            map_record,
            **dict(
                kwargs or [],
                jira_epic=self.jira_epic,
                project_binding=self.project_binding,
            ),
        )

    def _update_data(self, map_record, **kwargs):
        return super()._update_data(
            map_record,
            **dict(
                kwargs or [],
                jira_epic=self.jira_epic,
                project_binding=self.project_binding,
            ),
        )

    def _import(self, binding, **kwargs):
        # called at the beginning of _import because we must be sure
        # that dependencies are there (project and issue type)
        self._find_project_binding()
        if not self._is_issue_type_sync():
            _logger.debug(
                "Project or issue type %s is not synchronized.",
                self.external_record["id"],
            )
            return
        return super()._import(binding, **kwargs)

    def _import_dependency_assignee(self):
        jira_assignee = self.external_record["fields"].get("assignee") or {}
        if jira_assignee:
            jira_key = jira_assignee.get("accountId")
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
