# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import api, fields, models, exceptions, _

from ...unit.backend_adapter import JiraAdapter
from ...backend import jira


class JiraProjectProject(models.Model):
    _name = 'jira.project.project'
    _inherit = 'jira.binding'
    _inherits = {'project.project': 'openerp_id'}
    _description = 'Jira Projects'

    openerp_id = fields.Many2one(comodel_name='project.project',
                                 string='Project',
                                 required=True,
                                 index=True,
                                 ondelete='restrict')
    sync_issue_type_ids = fields.Many2many(
        comodel_name='jira.issue.type',
        string='Issue Levels to Synchronize',
        required=True,
        domain="[('backend_id', '=', backend_id)]",
        help="Only issues of these levels are imported. "
             "When a worklog is imported no a level which is "
             "not sync'ed, it is attached to the nearest "
             "sync'ed parent level. If no parent can be found, "
             "it is attached to a special 'Unassigned' task.",
    )
    project_template = fields.Selection(
        selection='_selection_project_template',
        string='Default Project Template',
        default='Scrum software development',
        required=True,
    )

    @api.model
    def _selection_project_template(self):
        return self.env['jira.backend']._selection_project_template()

    @api.onchange('backend_id')
    def onchange_project_backend_id(self):
        self.project_template = self.backend_id.project_template

    @api.model
    def create(self, values):
        record = super(JiraProjectProject, self).create(values)
        if not record.jira_key:
            raise exceptions.UserError(
                _('The JIRA Key is mandatory in order to export a project')
            )
        return record

    @api.multi
    def write(self, values):
        if 'project_template' in values:
            raise exceptions.UserError(
                _('The project template cannot be modified.')
            )
        return super(JiraProjectProject, self).write(values)

    @api.multi
    def unlink(self):
        if any(self.mapped('external_id')):
            raise exceptions.UserError(
                _('Exported project cannot be deleted.')
            )
        return super(JiraProjectProject, self).unlink()


class ProjectProject(models.Model):
    _inherit = 'project.project'

    jira_bind_ids = fields.One2many(
        comodel_name='jira.project.project',
        inverse_name='openerp_id',
        copy=False,
        string='Project Bindings',
        context={'active_test': False},
    )
    jira_exportable = fields.Boolean(
        string='Exportable on Jira',
        compute='_compute_jira_exportable',
    )
    jira_key = fields.Char(
        string='JIRA Key',
        size=10,  # limit on JIRA
    )

    @api.depends('jira_bind_ids')
    def _compute_jira_exportable(self):
        for project in self:
            project.jira_exportable = bool(project.jira_bind_ids)

    @api.multi
    def toggle_jira_exportable(self):
        for project in self:
            # TODO: possible improvement, when we have several backends,
            # show a popup to choose the backend to enable/disable
            if project.jira_exportable:
                project.jira_bind_ids.unlink()
            else:
                backends = self.env['jira.backend'].search([])
                for backend in backends:
                    self.env['jira.project.project'].create({
                        'backend_id': backend.id,
                        'openerp_id': project.id,
                    })

    @api.multi
    def write(self, values):
        result = super(ProjectProject, self).write(values)
        for record in self:
            if record.jira_exportable and not record.jira_key:
                raise exceptions.UserError(
                    _('The JIRA Key is mandatory on JIRA projects.')
            )
        return result


@jira
class ProjectAdapter(JiraAdapter):
    _model_name = 'jira.project.project'

    def read(self, id):
        return self.get(id).raw

    def get(self, id):
        return self.client.project(id)

    def create(self, key=None, name=None, template_name=None, values=None):
        project = self.client.create_project(
            key=key,
            name=name,
            template_name=template_name,
        )
        if values:
            project.update(values)
        return project
