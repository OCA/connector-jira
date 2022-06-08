# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
from collections import namedtuple

from odoo import _, api, exceptions, fields, models

from odoo.addons.component.core import Component

UpdatedWorklog = namedtuple(
    "UpdatedWorklog",
    "worklog_id updated"
    # id as integer, timestamp
)

UpdatedWorklogSince = namedtuple(
    "UpdatedWorklogSince",
    "since until updated_worklogs"
    # timestamp, timestamp, [UpdatedWorklog]
)


DeletedWorklogSince = namedtuple(
    "DeletedWorklogSince",
    "since until deleted_worklog_ids"
    # timestamp, timestamp, [ids as integer]
)


class JiraAccountAnalyticLine(models.Model):
    _name = "jira.account.analytic.line"
    _inherit = "jira.binding"
    _inherits = {"account.analytic.line": "odoo_id"}
    _description = "Jira Worklog"

    odoo_id = fields.Many2one(
        comodel_name="account.analytic.line",
        string="Timesheet Line",
        required=True,
        index=True,
        ondelete="restrict",
    )
    # The REST API needs issue id + worklog id, so we keep it along
    # in case we'll need it for an eventual export
    jira_issue_id = fields.Char()

    # As we can have more than one jira binding on a project.project, we store
    # to which one a task binding is related.
    jira_project_bind_id = fields.Many2one(
        comodel_name="jira.project.project",
        ondelete="restrict",
    )

    # we have to store these fields on the analytic line because
    # they may be different than the ones on their odoo task:
    # for instance, we do not import "Tasks" but we import "Epics",
    # the analytic line for a "Task" will be linked to an "Epic" on
    # Odoo, but we still want to know the original task here
    jira_issue_key = fields.Char(
        string="Original Task Key",
        readonly=True,
    )
    jira_issue_type_id = fields.Many2one(
        comodel_name="jira.issue.type",
        string="Original Issue Type",
        readonly=True,
    )
    jira_issue_url = fields.Char(
        string="Original JIRA issue Link",
        compute="_compute_jira_issue_url",
    )
    jira_epic_issue_key = fields.Char(
        string="Original Epic Key",
        readonly=True,
    )
    jira_epic_issue_url = fields.Char(
        string="Original JIRA Epic Link",
        compute="_compute_jira_issue_url",
    )

    _sql_constraints = [
        (
            "jira_binding_backend_uniq",
            "unique(backend_id, odoo_id)",
            "A binding already exists for this line and this backend.",
        ),
    ]

    def _is_linked(self):
        return self.mapped("jira_project_bind_id")._is_linked()

    @api.depends(
        "backend_id", "backend_id.uri", "jira_issue_key", "jira_epic_issue_key"
    )
    def _compute_jira_issue_url(self):
        """Compute the external URL to JIRA."""
        for record in self:
            record.jira_issue_url = self.backend_id.make_issue_url(
                record.jira_issue_key
            )
            record.jira_epic_issue_url = self.backend_id.make_issue_url(
                record.jira_epic_issue_key
            )

    @api.model
    def import_record(self, backend, issue_id, worklog_id, force=False):
        """Import a worklog from JIRA"""
        with backend.work_on(self._name) as work:
            importer = work.component(usage="record.importer")
            return importer.run(worklog_id, issue_id=issue_id, force=force)

    def force_reimport(self):
        for binding in self.sudo().mapped("jira_bind_ids"):
            binding.with_delay(priority=8).import_record(
                binding.backend_id,
                binding.jira_issue_id,
                binding.external_id,
                force=True,
            )


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    jira_bind_ids = fields.One2many(
        comodel_name="jira.account.analytic.line",
        inverse_name="odoo_id",
        copy=False,
        string="Worklog Bindings",
        context={"active_test": False},
    )
    # fields needed to display JIRA issue link in views
    jira_issue_key = fields.Char(
        string="Original JIRA Issue Key",
        compute="_compute_jira_references",
        store=True,
    )
    jira_issue_url = fields.Char(
        string="Original JIRA issue Link",
        compute="_compute_jira_references",
        compute_sudo=True,
    )
    jira_epic_issue_key = fields.Char(
        compute="_compute_jira_references",
        string="Original JIRA Epic Key",
        store=True,
    )
    jira_epic_issue_url = fields.Char(
        string="Original JIRA Epic Link",
        compute="_compute_jira_references",
        compute_sudo=True,
    )

    jira_issue_type_id = fields.Many2one(
        comodel_name="jira.issue.type",
        string="Original JIRA Issue Type",
        compute="_compute_jira_references",
        store=True,
    )

    @api.depends(
        "jira_bind_ids.jira_issue_key",
        "jira_bind_ids.jira_issue_type_id",
        "jira_bind_ids.jira_epic_issue_key",
    )
    def _compute_jira_references(self):
        """Compute the various references to JIRA.

        We assume that we have only one external record for a line
        """
        for record in self:
            if not record.jira_bind_ids:
                record.jira_issue_url = False
                record.jira_epic_issue_key = False
                record.jira_epic_issue_url = False
                continue
            main_binding = record.jira_bind_ids[0]
            record.jira_issue_key = main_binding.jira_issue_key
            record.jira_issue_url = main_binding.jira_issue_url
            record.jira_issue_type_id = main_binding.jira_issue_type_id
            record.jira_epic_issue_key = main_binding.jira_epic_issue_key
            record.jira_epic_issue_url = main_binding.jira_epic_issue_url

    @api.model
    def _get_connector_jira_fields(self):
        return [
            "jira_bind_ids",
            "project_id",
            "task_id",
            "user_id",
            "employee_id",
            "name",
            "date",
            "unit_amount",
        ]

    @api.model
    def _connector_jira_create_validate(self, vals):
        ProjectProject = self.env["project.project"]
        project_id = vals.get("project_id")
        if project_id:
            project_id = ProjectProject.sudo().browse(project_id)
            if (
                not self.env.context.get("connector_jira")
                and project_id.mapped("jira_bind_ids")._is_linked()
            ):
                raise exceptions.UserError(
                    _("Timesheet can not be created in project linked to JIRA!")
                )

    def _connector_jira_write_validate(self, vals):
        if (
            not self.env.context.get("connector_jira")
            and self.mapped("jira_bind_ids")._is_linked()
        ):
            fields = list(vals.keys())
            new_values = self._convert_to_write(
                vals,
            )
            for old_values in self.read(fields, load="_classic_write"):
                old_values = self._convert_to_write(
                    old_values,
                )
                for field in self._get_connector_jira_fields():
                    if field not in fields:
                        continue
                    if new_values[field] == old_values[field]:
                        continue
                    raise exceptions.UserError(
                        _("Timesheet linked to JIRA Worklog can not be modified!")
                    )

    def _connector_jira_unlink_validate(self):
        if (
            not self.env.context.get("connector_jira")
            and self.mapped("jira_bind_ids")._is_linked()
        ):
            raise exceptions.UserError(
                _("Timesheet linked to JIRA Worklog can not be deleted!")
            )

    @api.model
    def create(self, vals):
        self._connector_jira_create_validate(vals)
        return super().create(vals)

    def write(self, vals):
        self._connector_jira_write_validate(vals)
        return super().write(vals)

    def unlink(self):
        self._connector_jira_unlink_validate()
        return super().unlink()


class WorklogAdapter(Component):
    _name = "jira.worklog.adapter"
    _inherit = "jira.webservice.adapter"
    _apply_on = ["jira.account.analytic.line"]

    def read(self, issue_id, worklog_id):
        # pylint: disable=W8106
        with self.handle_404():
            return self.client.worklog(issue_id, worklog_id).raw

    def search(self, issue_id):
        """Search worklogs of an issue"""
        worklogs = self.client.worklogs(issue_id)
        return [worklog.id for worklog in worklogs]

    @staticmethod
    def _chunks(whole, size):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(whole), size):
            yield whole[i : i + size]

    def yield_read(self, worklog_ids):
        """Generator returning worklog ids data"""
        path = "worklog/list"

        # the method returns max 1000 results
        for chunk in self._chunks(worklog_ids, 1000):
            payload = json.dumps({"ids": chunk})
            result = self._post_get_json(path, data=payload)
            for worklog in result:
                yield worklog

    def updated_since(self, since=None):
        path = "worklog/updated"

        start_since = since
        updated_worklogs = []

        while True:
            result = self.client._get_json(path, params={"since": since})
            updated_worklogs += [
                UpdatedWorklog(worklog_id=row["worklogId"], updated=row["updatedTime"])
                for row in result["values"]
            ]
            until = since = result["until"]
            if result["lastPage"]:
                break
        return UpdatedWorklogSince(
            since=start_since, until=until, updated_worklogs=updated_worklogs
        )

    def deleted_since(self, since=None):
        path = "worklog/deleted"

        start_since = since
        deleted_worklog_ids = []

        while True:
            result = self.client._get_json(path, params={"since": since})
            deleted_worklog_ids += [row["worklogId"] for row in result["values"]]
            until = since = result["until"]
            if result["lastPage"]:
                break
        return DeletedWorklogSince(
            since=start_since, until=until, deleted_worklog_ids=deleted_worklog_ids
        )
