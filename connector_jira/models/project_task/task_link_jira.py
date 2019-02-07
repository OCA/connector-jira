# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

import jira

from odoo import api, fields, models, exceptions, _

_logger = logging.getLogger(__name__)


class TaskLinkJira(models.TransientModel):
    _name = 'task.link.jira'
    _inherit = 'multi.step.wizard.mixin'
    _description = 'Link Task with JIRA'

    task_id = fields.Many2one(
        comodel_name='project.task',
        name="Task",
        required=True,
        ondelete='cascade',
        default=lambda self: self._default_task_id(),
    )
    jira_key = fields.Char(
        string='JIRA Key',
        required=True,
    )
    backend_id = fields.Many2one(
        comodel_name='jira.backend',
        string='Jira Backend',
        required=True,
        ondelete='cascade',
        domain="[('id', 'in', linked_backend_ids)]",
        default=lambda self: self._default_backend_id(),
    )
    linked_backend_ids = fields.Many2many(
        comodel_name='jira.backend',
        compute="_compute_linked_backend_ids",
    )
    jira_task_id = fields.Many2one(
        comodel_name='jira.project.task',
        ondelete='cascade',
    )

    @api.depends('task_id.project_id')
    def _compute_linked_backend_ids(self):
        for record in self:
            record.linked_backend_ids = record.task_id.mapped(
                "project_id.jira_bind_ids.backend_id"
            )

    @api.model
    def _selection_state(self):
        return [
            ('start', 'Start'),
            ('final', 'Final'),
        ]

    @api.model
    def _default_task_id(self):
        return self.env.context.get('active_id')

    @api.model
    def _default_backend_id(self):
        backends = self.env['jira.backend'].search([])
        if len(backends) == 1:
            return backends.id

    def state_exit_start(self):
        if not self.jira_task_id:
            self._link_binding()
        self.state = 'final'

    def _link_binding(self):
        with self.backend_id.work_on('jira.project.task') as work:
            adapter = work.component(usage='backend.adapter')
            try:
                jira_task = adapter.get(self.jira_key)
            except jira.exceptions.JIRAError:
                _logger.exception('Error when linking to task %s',
                                  self.task_id.id)
                raise exceptions.UserError(
                    _('Could not link %s, check that this task'
                      ' keys exists in JIRA.') % (self.jira_key)
                )
            self._link_with_jira_task(work, jira_task)
            self._run_import_jira_task(work, jira_task)

    def _link_with_jira_task(self, work, jira_task):
        values = self._prepare_link_binding_values(jira_task)
        self.jira_task_id = self.env['jira.project.task'].create(
            values
        )

    def _run_import_jira_task(self, work, jira_task):
        importer = work.component(usage="record.importer")
        importer.run(jira_task.id, force=True, record=jira_task.raw)

    def _prepare_link_binding_values(self, jira_task):
        values = {
            'backend_id': self.backend_id.id,
            'odoo_id': self.task_id.id,
            'jira_key': self.jira_key,
            'external_id': jira_task.id,
        }
        return values
