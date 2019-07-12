# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, models, exceptions, _


class ProjectTaskMergeWizard(models.TransientModel):
    _inherit = 'project.task.merge.wizard'

    @api.multi
    def merge_tasks(self):
        self._check_jira_bindings()
        result = super().merge_tasks()
        self._merge_jira_bindings()
        return result

    def _check_jira_bindings(self):
        if len(self.mapped('task_ids.jira_bind_ids')) > 1:
            raise exceptions.UserError(
                _('Merging several tasks coming from JIRA is not allowed.')
            )

    def _merge_jira_bindings(self):
        binding = self.mapped('task_ids.jira_bind_ids')
        self.target_task_id.jira_bind_ids = binding
