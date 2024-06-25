# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _

from odoo.addons.component.core import Component

from .common import iso8601_to_utc_datetime

_logger = logging.getLogger(__name__)


class JiraAnalyticLineImporter(Component):
    _name = "jira.analytic.line.importer"
    _inherit = "jira.importer"
    _apply_on = ["jira.account.analytic.line"]

    def __init__(self, work_context):
        super().__init__(work_context)
        self.external_issue_id = None
        self.task_binding = None
        self.project_binding = None
        self.fallback_project = None

    def _get_external_updated_at(self):
        assert self.external_record
        external_updated_at = self.external_record.get("updated")
        if not external_updated_at:
            return None
        return iso8601_to_utc_datetime(external_updated_at)

    @property
    def _issue_fields_to_read(self):
        epic_field_name = self.backend_record.epic_link_field_name
        return ["issuetype", "project", "parent", epic_field_name]

    def _recurse_import_task(self):
        """Import and return the task of proper type for the worklog

        As we decide which type of issues are imported for a project,
        a worklog could be linked to an issue that we don't import.
        In that case, we climb the parents of the issue until we find
        a issue of a type we synchronize.

        It ensures that the 'to-be-linked' issue is imported and return it.

        """
        issue_adapter = self.component(
            usage="backend.adapter", model_name="jira.project.task"
        )
        issue_binder = self.binder_for("jira.project.task")
        issue_type_binder = self.binder_for("jira.issue.type")
        jira_issue_id = self.external_record["issueId"]
        epic_field_name = self.backend_record.epic_link_field_name
        project_matcher = self.component(usage="jira.task.project.matcher")
        current_project_id = self.external_issue["fields"]["project"]["id"]
        while jira_issue_id:
            issue = issue_adapter.read(jira_issue_id, fields=self._issue_fields_to_read)
            jira_project_id = issue["fields"]["project"]["id"]
            jira_issue_type_id = issue["fields"]["issuetype"]["id"]
            project_binding = project_matcher.find_project_binding(issue)
            issue_type_binding = issue_type_binder.to_internal(jira_issue_type_id)
            # JIRA allows to set an EPIC of a different project.
            # If it happens, we discard it.
            if (
                jira_project_id == current_project_id
                and issue_type_binding.is_sync_for_project(project_binding)
            ):
                break
            if issue["fields"].get("parent"):
                # 'parent' is used on sub-tasks relating to their parent task
                jira_issue_id = issue["fields"]["parent"]["id"]
            elif issue["fields"].get(epic_field_name):
                # the epic link is set on a jira custom field
                epic_key = issue["fields"][epic_field_name]
                epic = issue_adapter.read(epic_key, fields="id")
                # we got the key of the epic issue, so we translate
                # it to the ID with a call to the API
                jira_issue_id = epic["id"]
            else:
                # no parent issue of a type we are synchronizing has been
                # found, the worklog will be assigned to no task
                jira_issue_id = None

        if jira_issue_id:
            self._import_dependency(jira_issue_id, "jira.project.task")
            return issue_binder.to_internal(jira_issue_id)

    def _create_data(self, map_record, **kwargs):
        return super()._create_data(
            map_record,
            **dict(
                kwargs or [],
                task_binding=self.task_binding,
                project_binding=self.project_binding,
                fallback_project=self.fallback_project,
                linked_issue=self.external_issue,
            ),
        )

    def _update_data(self, map_record, **kwargs):
        return super()._update_data(
            map_record,
            **dict(
                kwargs or [],
                task_binding=self.task_binding,
                project_binding=self.project_binding,
                fallback_project=self.fallback_project,
                linked_issue=self.external_issue,
            ),
        )

    def run(self, external_id, force=False, record=None, **kwargs):
        assert "issue_id" in kwargs
        self.external_issue_id = kwargs.pop("issue_id")
        return super().run(external_id, force=force, record=record, **kwargs)

    def _handle_record_missing_on_jira(self):
        """Hook called when we are importing a record missing on Jira

        For worklogs, we drop the analytic line if we discover it doesn't exist
        on Jira, as the latter is the master.
        """
        binding = self._get_binding()
        if binding:
            record = binding.odoo_id
            binding.unlink()
            record.unlink()
        return _("Record does no longer exist in Jira")

    def _get_external_data(self):
        """Return the raw Jira data for ``self.external_id``"""
        adapt = self.component(usage="backend.adapter", model_name="jira.project.task")
        self.external_issue = adapt.read(self.external_issue_id)
        return self.backend_adapter.read(self.external_issue_id, self.external_id)

    def _before_import(self):
        task_binding = self._recurse_import_task()
        if task_binding and task_binding.active:
            self.task_binding = task_binding
        if not self.task_binding:
            # when no task exists in Odoo (because we don't synchronize
            # the issue type for instance), we link the line directly
            # to the corresponding project, not linked to any task
            issue = self.external_issue
            assert issue
            matcher = self.component(usage="jira.task.project.matcher")
            project_binding = matcher.find_project_binding(issue)
            if project_binding and project_binding.active:
                self.project_binding = project_binding
            else:
                self.fallback_project = matcher.fallback_project_for_worklogs()

    def _import(self, binding, **kwargs):
        if not (self.task_binding or self.project_binding or self.fallback_project):
            _logger.debug(
                "No task or project synchronized for attaching worklog %s",
                self.external_record["id"],
            )
            return
        return super()._import(binding, **kwargs)

    def _import_dependency_assignee(self):
        jira_assignee = self.external_record["author"]
        jira_key = jira_assignee.get("accountId")
        self._import_dependency(jira_key, "jira.res.users", record=jira_assignee)

    def _import_dependencies(self):
        """Import the dependencies for the record"""
        self._import_dependency_assignee()
