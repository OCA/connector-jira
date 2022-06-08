# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, exceptions, fields, models

_logger = logging.getLogger(__name__)


class ProjectLinkJira(models.TransientModel):
    _name = "project.link.jira"
    _inherit = ["jira.project.base.mixin", "multi.step.wizard.mixin"]
    _description = "Link Project with JIRA"

    project_id = fields.Many2one(
        comodel_name="project.project",
        name="Project",
        required=True,
        ondelete="cascade",
        default=lambda self: self._default_project_id(),
    )
    jira_key = fields.Char(
        default=lambda self: self._default_jira_key(),
    )
    backend_id = fields.Many2one(
        comodel_name="jira.backend",
        string="Jira Backend",
        required=True,
        ondelete="cascade",
        default=lambda self: self._default_backend_id(),
    )
    jira_project_id = fields.Many2one(
        comodel_name="jira.project.project",
        ondelete="cascade",
    )

    @api.model
    def _default_project_id(self):
        return self.env.context.get("active_id")

    @api.model
    def _default_jira_key(self):
        project_id = self._default_project_id()
        if not project_id:
            return
        project = self.env["project.project"].browse(project_id)
        valid = self.env["jira.project.project"]._jira_key_valid
        if valid(project.name):
            return project.name

    @api.model
    def _default_backend_id(self):
        backends = self.env["jira.backend"].search([])
        if len(backends) == 1:
            return backends.id

    @api.model
    def _selection_state(self):
        return [
            ("start", "Start"),
            ("issue_types", "Issue Types"),
            ("export_config", "Export Config."),
            ("final", "Final"),
        ]

    @api.constrains("jira_key")
    def check_jira_key(self):
        for record in self:
            valid = self.env["jira.project.project"]._jira_key_valid
            if not valid(record.jira_key):
                raise exceptions.ValidationError(
                    _("%s is not a valid JIRA Key") % record.jira_key
                )

    def add_all_issue_types(self):
        issue_types = self.env["jira.issue.type"].search(
            [("backend_id", "=", self.backend_id.id)]
        )
        self.sync_issue_type_ids = issue_types.ids

    def state_exit_start(self):
        if self.sync_action == "export":
            self.add_all_issue_types()
        elif self.sync_action == "link":
            if not self.jira_project_id:
                self._link_binding()
        self.state = "issue_types"

    def state_exit_issue_types(self):
        if self.sync_action == "export":
            self.state = "export_config"
        elif self.sync_action == "link":
            self._copy_issue_types()
            self.state = "final"

    def state_exit_export_config(self):
        if not self.jira_project_id:
            self._create_export_binding()
        self.state = "final"

    def _prepare_base_binding_values(self):
        values = {
            "backend_id": self.backend_id.id,
            "odoo_id": self.project_id.id,
            "jira_key": self.jira_key,
        }
        return values

    def _prepare_export_binding_values(self):
        values = self._prepare_base_binding_values()
        values.update(
            {
                "backend_id": self.backend_id.id,
                "odoo_id": self.project_id.id,
                "sync_action": "export",
                "sync_issue_type_ids": [(6, 0, self.sync_issue_type_ids.ids)],
                "project_template": self.project_template,
                "project_template_shared": self.project_template_shared,
            }
        )
        return values

    def _create_export_binding(self):
        values = self._prepare_export_binding_values()
        self.jira_project_id = self.env["jira.project.project"].create(values)

    def _link_binding(self):
        with self.backend_id.work_on("jira.project.project") as work:
            adapter = work.component(usage="backend.adapter")
            with adapter.handle_user_api_errors():
                jira_project = adapter.get(self.jira_key)
            self._link_with_jira_project(work, jira_project)

    def _link_with_jira_project(self, work, jira_project):
        values = self._prepare_link_binding_values(jira_project)
        self.jira_project_id = self.env["jira.project.project"].create(values)
        type_binder = work.component(usage="binder", model_name="jira.issue.type")
        issue_types = self.env["jira.issue.type"].browse()
        for jira_issue_type in jira_project.issueTypes:
            issue_types |= type_binder.to_internal(jira_issue_type.id)
        self.sync_issue_type_ids = issue_types.ids

    def _prepare_link_binding_values(self, jira_project):
        values = self._prepare_base_binding_values()
        values.update(
            {
                "sync_action": self.sync_action,
                "external_id": jira_project.id,
                "project_type": jira_project.projectTypeKey,
            }
        )
        return values

    def _copy_issue_types(self):
        self.jira_project_id.sync_issue_type_ids = self.sync_issue_type_ids.ids
