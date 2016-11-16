# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import api, fields, models, exceptions, _

from ...unit.backend_adapter import JiraAdapter
from ...backend import jira


class JiraProjectTask(models.Model):
    _name = 'jira.project.task'
    _inherit = 'jira.binding'
    _inherits = {'project.task': 'openerp_id'}
    _description = 'Jira Tasks'

    openerp_id = fields.Many2one(comodel_name='project.task',
                                 string='Task',
                                 required=True,
                                 index=True,
                                 ondelete='restrict')

    @api.multi
    def unlink(self):
        if any(self.mapped('external_id')):
            raise exceptions.UserError(
                _('A Jira task cannot be deleted.')
            )
        return super(JiraProjectTask, self).unlink()


class ProjectTask(models.Model):
    _inherit = 'project.task'

    jira_bind_ids = fields.One2many(
        comodel_name='jira.project.task',
        inverse_name='openerp_id',
        copy=False,
        string='Task Bindings',
        context={'active_test': False},
    )


@jira
class TaskAdapter(JiraAdapter):
    _model_name = 'jira.project.task'

    def read(self, id, fields=None):
        return self.client.issue(id, fields=fields).raw

    def search(self, jql, fields=None):
        if fields is None:
            fields = ['id']
        return self.client.search_issues(jql, fields=fields)
