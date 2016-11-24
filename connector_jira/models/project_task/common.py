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
    jira_key = fields.Char(
        string='Key',
        readonly=True,
    )
    jira_issue_type_id = fields.Many2one(
        comodel_name='jira.issue.type',
        string='Issue Type',
        readonly=True,
    )
    jira_epic_link_id = fields.Many2one(
        comodel_name='jira.project.task',
        string='Epic',
        readonly=True,
    )

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
    jira_issue_type = fields.Char(
        compute='_compute_jira_issue_type',
        string='JIRA Issue Type',
        store=True,
    )
    jira_compound_key = fields.Char(
        compute='_compute_jira_compound_key',
        string='JIRA Key',
        store=True,
    )
    jira_epic_link_task_id = fields.Many2one(
        comodel_name='project.task',
        compute='_compute_jira_epic_link_task_id',
        string='JIRA Epic',
        store=True,
    )

    @api.depends('jira_bind_ids.jira_issue_type_id.name')
    def _compute_jira_issue_type(self):
        for record in self:
            types = record.mapped('jira_bind_ids.jira_issue_type_id.name')
            record.jira_issue_type = ','.join([t for t in types if t])

    @api.depends('jira_bind_ids.jira_key')
    def _compute_jira_compound_key(self):
        for record in self:
            keys = record.mapped('jira_bind_ids.jira_key')
            record.jira_compound_key = ','.join([k for k in keys if k])

    @api.depends('jira_bind_ids.jira_epic_link_id.openerp_id')
    def _compute_jira_epic_link_task_id(self):
        for record in self:
            tasks = record.mapped(
                'jira_bind_ids.jira_epic_link_id.openerp_id'
            )
            if len(tasks) == 1:
                record.jira_epic_link_task_id = tasks


@jira
class TaskAdapter(JiraAdapter):
    _model_name = 'jira.project.task'

    def read(self, id, fields=None):
        return self.client.issue(id, fields=fields).raw

    def search(self, jql):
        # we need to have at least one field which is not 'id' or 'key'
        # due to this bug: https://github.com/pycontribs/jira/pull/289
        fields = 'id,updated'
        issues = self.client.search_issues(jql, fields=fields, maxResults=None)
        return [issue.id for issue in issues]
