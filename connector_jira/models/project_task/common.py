# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models, exceptions, _
from odoo.addons.component.core import Component


class JiraProjectTask(models.Model):
    _name = 'jira.project.task'
    _inherit = 'jira.binding'
    _inherits = {'project.task': 'odoo_id'}
    _description = 'Jira Tasks'

    odoo_id = fields.Many2one(comodel_name='project.task',
                              string='Task',
                              required=True,
                              index=True,
                              ondelete='restrict')
    # As we can have more than one jira binding on a project.project, we store
    # to which one a task binding is related.
    jira_project_bind_id = fields.Many2one(
        comodel_name='jira.project.project',
        ondelete='restrict',
    )
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
    jira_parent_id = fields.Many2one(
        comodel_name='jira.project.task',
        string='Parent Issue',
        readonly=True,
        help="Parent issue when the issue is a subtask. "
             "Empty if the type of parent is filtered out "
             "of the synchronizations.",
    )
    jira_issue_url = fields.Char(
        string='JIRA issue',
        compute='_compute_jira_issue_url',
    )

    _sql_constraints = [
        ('jira_binding_backend_uniq', 'unique(backend_id, odoo_id)',
         "A binding already exists for this task and this backend."),
    ]

    @api.multi
    def unlink(self):
        if any(self.mapped('external_id')):
            raise exceptions.UserError(
                _('A Jira task cannot be deleted.')
            )
        return super().unlink()

    @api.depends('jira_key')
    def _compute_jira_issue_url(self):
        """Compute the external URL to JIRA."""
        for record in self:
            record.jira_issue_url = record.backend_id.make_issue_url(
                record.jira_key
            )


class ProjectTask(models.Model):
    _inherit = 'project.task'

    jira_bind_ids = fields.One2many(
        comodel_name='jira.project.task',
        inverse_name='odoo_id',
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
    jira_parent_task_id = fields.Many2one(
        comodel_name='project.task',
        compute='_compute_jira_parent_task_id',
        string='JIRA Parent',
        store=True,
    )
    jira_issue_url = fields.Char(
        string='JIRA issue',
        compute='_compute_jira_issue_url',
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

    @api.depends('jira_bind_ids.jira_epic_link_id.odoo_id')
    def _compute_jira_epic_link_task_id(self):
        for record in self:
            tasks = record.mapped(
                'jira_bind_ids.jira_epic_link_id.odoo_id'
            )
            if len(tasks) == 1:
                record.jira_epic_link_task_id = tasks

    @api.depends('jira_bind_ids.jira_parent_id.odoo_id')
    def _compute_jira_parent_task_id(self):
        for record in self:
            tasks = record.mapped(
                'jira_bind_ids.jira_parent_id.odoo_id'
            )
            if len(tasks) == 1:
                record.jira_parent_task_id = tasks

    @api.depends('jira_bind_ids.jira_key')
    def _compute_jira_issue_url(self):
        """Compute the external URL to JIRA.

        We assume that we have only one external record.
        """
        for record in self:
            if not record.jira_bind_ids:
                continue
            main_binding = record.jira_bind_ids[0]
            record.jira_issue_url = main_binding.jira_issue_url

    @api.multi
    def name_get(self):
        names = []
        for task in self:
            task_id, name = super(ProjectTask, task).name_get()[0]
            if task.jira_compound_key:
                name = '[%s] %s' % (task.jira_compound_key, name)
            names.append((task_id, name))
        return names


class TaskAdapter(Component):
    _name = 'jira.project.task.adapter'
    _inherit = ['jira.webservice.adapter']
    _apply_on = ['jira.project.task']

    def read(self, id_, fields=None):
        return self.get(id_, fields=fields).raw

    def get(self, id_, fields=None):
        with self.handle_404():
            return self.client.issue(
                id_,
                fields=fields,
                expand=['renderedFields']
            )

    def search(self, jql):
        # we need to have at least one field which is not 'id' or 'key'
        # due to this bug: https://github.com/pycontribs/jira/pull/289
        fields = 'id,updated'
        issues = self.client.search_issues(jql, fields=fields, maxResults=None)
        return [issue.id for issue in issues]
