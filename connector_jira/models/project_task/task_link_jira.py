# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class TaskLinkJira(models.TransientModel):
    _name = "task.link.jira"
    _inherit = "multi.step.wizard.mixin"
    _description = "Link Task with JIRA"

    task_id = fields.Many2one(
        comodel_name="project.task",
        name="Task",
        required=True,
        ondelete="cascade",
    )
    jira_key = fields.Char(
        string="JIRA Key",
        required=True,
    )
    backend_id = fields.Many2one(
        comodel_name="jira.backend",
        string="Jira Backend",
        required=True,
        ondelete="cascade",
        domain="[('id', 'in', linked_backend_ids)]",
    )
    linked_backend_ids = fields.Many2many(
        comodel_name="jira.backend",
    )
    jira_task_id = fields.Many2one(
        comodel_name="jira.project.task",
        ondelete="cascade",
    )

    @api.model
    def _selection_state(self):
        return [
            ("start", "Start"),
            ("final", "Final"),
        ]

    @api.model
    def default_get(self, fields):
        values = super().default_get(fields)
        context = self.env.context
        if context.get("active_model") == "project.task" and context.get("active_id"):
            task = self.env["project.task"].browse(context["active_id"])
            project_linked_backends = task.mapped("project_id.jira_bind_ids.backend_id")
            values.update(
                {
                    "task_id": task.id,
                    "linked_backend_ids": [(6, 0, project_linked_backends.ids)],
                }
            )
            if len(project_linked_backends) == 1:
                values["backend_id"] = project_linked_backends.id
        return values

    def state_exit_start(self):
        if not self.jira_task_id:
            self._link_binding()
        self.state = "final"

    def _link_binding(self):
        with self.backend_id.work_on("jira.project.task") as work:
            adapter = work.component(usage="backend.adapter")
            with adapter.handle_user_api_errors():
                jira_task = adapter.get(self.jira_key)
            self._link_with_jira_task(work, jira_task)
            self._run_import_jira_task(work, jira_task)

    def _link_with_jira_task(self, work, jira_task):
        values = self._prepare_link_binding_values(jira_task)
        self.jira_task_id = self.env["jira.project.task"].create(values)

    def _run_import_jira_task(self, work, jira_task):
        importer = work.component(usage="record.importer")
        importer.run(jira_task.id, force=True, record=jira_task.raw)

    def _prepare_link_binding_values(self, jira_task):
        values = {
            "backend_id": self.backend_id.id,
            "odoo_id": self.task_id.id,
            "jira_key": self.jira_key,
            "external_id": jira_task.id,
        }
        return values
