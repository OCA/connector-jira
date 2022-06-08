# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from pytz import timezone, utc

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

from ...components.mapper import (
    iso8601_to_naive_date,
    iso8601_to_utc_datetime,
    whenempty,
)
from ...fields import MilliDatetime

_logger = logging.getLogger(__name__)


class AnalyticLineMapper(Component):
    _name = "jira.analytic.line.mapper"
    _inherit = "jira.import.mapper"
    _apply_on = ["jira.account.analytic.line"]

    direct = [
        (whenempty("comment", _("missing description")), "name"),
    ]

    @mapping
    def issue(self, record):
        issue = self.options.linked_issue
        assert issue
        refs = {
            "jira_issue_id": record["issueId"],
            "jira_issue_key": issue["key"],
        }
        task_mapper = self.component(
            usage="import.mapper",
            model_name="jira.project.task",
        )
        issue_type_dict = task_mapper.issue_type(issue)
        refs.update(issue_type_dict)
        epic_field_name = self.backend_record.epic_link_field_name
        if epic_field_name and epic_field_name in issue["fields"]:
            refs["jira_epic_issue_key"] = issue["fields"][epic_field_name]
        if self.backend_record.epic_link_on_epic:
            issue_type = self.env["jira.issue.type"].browse(
                issue_type_dict.get("jira_issue_type_id")
            )
            if issue_type.name == "Epic":
                refs["jira_epic_issue_key"] = issue.get("key")
        return refs

    @mapping
    def date(self, record):
        mode = self.backend_record.worklog_date_timezone_mode
        started = record["started"]
        if not mode or mode == "naive":
            return {"date": iso8601_to_naive_date(started)}
        started = iso8601_to_utc_datetime(started).replace(tzinfo=utc)
        if mode == "user":
            tz = timezone(record["author"]["timeZone"])
        elif mode == "specific":
            tz = timezone(self.backend_record.worklog_date_timezone)
        return {"date": started.astimezone(tz).date()}

    @mapping
    def duration(self, record):
        spent = float(record["timeSpentSeconds"])
        # amount is in float in odoo... 2h30 = 2.5
        return {"unit_amount": spent / 60 / 60}

    @mapping
    def author(self, record):
        jira_author = record["author"]
        jira_author_key = jira_author["key"]
        binder = self.binder_for("jira.res.users")
        user = binder.to_internal(jira_author_key, unwrap=True)
        if not user:
            email = jira_author["emailAddress"]
            raise MappingError(
                _(
                    'No user found with login "%(jira_author_key)s" or email "%(email)s".'
                    "You must create a user or link it manually if the "
                    "login/email differs.",
                    jira_author_key=jira_author_key,
                    email=email,
                )
            )
        employee = (
            self.env["hr.employee"]
            .with_context(
                active_test=False,
            )
            .search([("user_id", "=", user.id)], limit=1)
        )
        return {"user_id": user.id, "employee_id": employee.id}

    @mapping
    def project_and_task(self, record):
        assert (
            self.options.task_binding
            or self.options.project_binding
            or self.options.fallback_project
        )
        task_binding = self.options.task_binding
        if not task_binding:
            if self.options.fallback_project:
                return {"project_id": self.options.fallback_project.id}
            project = self.options.project_binding.odoo_id
            if project:
                return {
                    "project_id": project.id,
                    "jira_project_bind_id": self.options.project_binding.id,
                }

        project = task_binding.project_id
        return {
            "task_id": task_binding.odoo_id.id,
            "project_id": project.id,
            "jira_project_bind_id": task_binding.jira_project_bind_id.id,
        }

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}


class AnalyticLineBatchImporter(Component):
    """Import the Jira worklogs

    For every id in in the list, a delayed job is created.
    Import from a date
    """

    _name = "jira.analytic.line.batch.importer"
    _inherit = "jira.timestamp.batch.importer"
    _apply_on = ["jira.account.analytic.line"]

    def _search(self, timestamp):
        unix_timestamp = MilliDatetime.to_timestamp(timestamp.last_timestamp)
        result = self.backend_adapter.updated_since(since=unix_timestamp)
        worklog_ids = self._filter_update(result.updated_worklogs)
        # We need issue_id + worklog_id for the worklog importer (the jira
        # "read" method for worklogs asks both), get it from yield_read.
        # TODO we might consider to optimize the import process here:
        # yield_read reads worklogs data, then the individual
        # import will do a request again (and 2 with the tempo module)
        next_timestamp = MilliDatetime.from_timestamp(result.until)
        return (next_timestamp, self.backend_adapter.yield_read(worklog_ids))

    def _handle_records(self, records, force=False):
        count = 0
        for worklog in records:
            count += 1
            worklog_id = worklog["id"]
            issue_id = worklog["issueId"]
            self._import_record(issue_id, worklog_id, force=force)
        return count

    def _filter_update(self, updated_worklogs):
        """Filter only the worklogs needing an update

        The result from Jira contains the worklog id and
        the last update on Jira. So we keep only the worklog
        ids with an sync_date before the Jira last update.
        """
        if not updated_worklogs:
            return []
        self.env.cr.execute(
            "SELECT external_id, jira_updated_at "
            "FROM jira_account_analytic_line "
            "WHERE external_id IN %s ",
            (tuple(str(r.worklog_id) for r in updated_worklogs),),
        )
        bindings = {int(row[0]): row[1] for row in self.env.cr.fetchall()}
        worklog_ids = []
        for worklog in updated_worklogs:
            worklog_id = worklog.worklog_id
            # we store the latest "updated_at" value on the binding
            # so we can check if we already know the latest value,
            # for instance because we imported the record from a
            # webhook before, we can skip the import
            binding_updated_at = bindings.get(worklog_id)
            if not binding_updated_at:
                worklog_ids.append(worklog_id)
                continue
            binding_updated_at = MilliDatetime.from_string(binding_updated_at)
            jira_updated_at = MilliDatetime.from_timestamp(worklog.updated)
            if binding_updated_at < jira_updated_at:
                worklog_ids.append(worklog_id)
        return worklog_ids

    def _import_record(self, issue_id, worklog_id, force=False, **kwargs):
        """Delay the import of the records"""
        self.model.with_delay(**kwargs).import_record(
            self.backend_record,
            issue_id,
            worklog_id,
            force=force,
        )


class AnalyticLineImporter(Component):
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
            issue = issue_adapter.read(
                jira_issue_id,
                fields=self._issue_fields_to_read,
            )

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
            task_binding=self.task_binding,
            project_binding=self.project_binding,
            fallback_project=self.fallback_project,
            linked_issue=self.external_issue,
        )

    def _update_data(self, map_record, **kwargs):
        return super()._update_data(
            map_record,
            task_binding=self.task_binding,
            project_binding=self.project_binding,
            fallback_project=self.fallback_project,
            linked_issue=self.external_issue,
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
        issue_adapter = self.component(
            usage="backend.adapter", model_name="jira.project.task"
        )
        self.external_issue = issue_adapter.read(self.external_issue_id)
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
        jira_key = jira_assignee.get("key")
        self._import_dependency(jira_key, "jira.res.users", record=jira_assignee)

    def _import_dependencies(self):
        """Import the dependencies for the record"""
        self._import_dependency_assignee()
