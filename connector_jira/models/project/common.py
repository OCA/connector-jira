# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import api, fields, models, exceptions, _


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
