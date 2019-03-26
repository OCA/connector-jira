# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

import jira

from odoo import api, fields, models, exceptions, _

_logger = logging.getLogger(__name__)


class ProjectLinkJira(models.TransientModel):
    _name = 'project.link.jira'
    _inherit = ['jira.project.base.mixin', 'multi.step.wizard.mixin']
    _description = 'Link Project with JIRA'

    project_id = fields.Many2one(
        comodel_name='project.project',
        name="Project",
        required=True,
        ondelete='cascade',
    )
    jira_key = fields.Char(
        string='JIRA Key',
        size=10,  # limit on JIRA
        required=True,
    )
    backend_id = fields.Many2one(
        comodel_name='jira.backend',
        string='Jira Backend',
        required=True,
        ondelete='cascade',
    )
    jira_project_id = fields.Many2one(
        comodel_name='jira.project.project',
        ondelete='cascade',
    )

    @api.model
    def _selection_state(self):
        return [
            ('start', 'Start'),
            ('issue_types', 'Issue Types'),
            ('export_config', 'Export Config.'),
            ('final', 'Final'),
        ]

    @api.model
    def default_get(self, fields):
        values = super().default_get(fields)
        context = self.env.context
        project_id = context.get('active_id')
        if not project_id:
            return values

        project = self.env['project.project'].browse(project_id)
        if project.jira_key:
            values['jira_key'] = project.jira_key
        else:
            valid = self.env['jira.project.project']._jira_key_valid
            if valid(project.name):
                values['jira_key'] = project.name

        values.update({
            'project_id': project_id,
        })

        backends = self.env['jira.backend'].search([])
        if len(backends) == 1:
            values['backend_id'] = backends.id

            jira_project_model = self.env['jira.project.project']
            new_binding = jira_project_model.new({
                'odoo_id': values['project_id'],
                'backend_id': values['backend_id'],
            })
            domain = new_binding._other_master_domain()
            if not jira_project_model.search(domain):
                values['is_master'] = True

        return values

    @api.constrains('jira_key')
    def check_jira_key(self):
        for record in self:
            valid = self.env['jira.project.project']._jira_key_valid
            if not valid(record.jira_key):
                raise exceptions.ValidationError(
                    _('%s is not a valid JIRA Key') % record.jira_key
                )

    def add_all_issue_types(self):
        issue_types = self.env['jira.issue.type'].search([
            ('backend_id', '=', self.backend_id.id)
        ])
        self.sync_issue_type_ids = issue_types.ids

    def state_exit_start(self):
        if self.sync_action == 'export':
            self.add_all_issue_types()
        elif self.sync_action == 'link':
            if not self.jira_project_id:
                self._link_binding()
        self.state = 'issue_types'

    def state_exit_issue_types(self):
        if self.sync_action == 'export':
            self.state = 'export_config'
        elif self.sync_action == 'link':
            self._copy_issue_types()
            self.state = 'final'

    def state_exit_export_config(self):
        if not self.jira_project_id:
            self._create_export_binding()
        self.state = 'final'

    def _prepare_base_binding_values(self):
        values = {
            'backend_id': self.backend_id.id,
            'odoo_id': self.project_id.id,
            'is_master': self.is_master,
        }
        if self.is_master:
            values['jira_key'] = self.jira_key
        return values

    def _prepare_export_binding_values(self):
        values = self._prepare_base_binding_values()
        values.update({
            'backend_id': self.backend_id.id,
            'odoo_id': self.project_id.id,
            'sync_action': 'export',
            'sync_issue_type_ids': [(6, 0, self.sync_issue_type_ids.ids)],
            'project_template': self.project_template,
            'project_template_shared': self.project_template_shared,
        })
        return values

    def _create_export_binding(self):
        values = self._prepare_export_binding_values()
        self.jira_project_id = self.env['jira.project.project'].create(values)

    def _link_binding(self):
        with self.backend_id.work_on('jira.project.project') as work:
            adapter = work.component(usage='backend.adapter')
            try:
                jira_project = adapter.get(self.jira_key)
            except jira.exceptions.JIRAError:
                _logger.exception('Error when linking to project %s',
                                  self.project_id.id)
                raise exceptions.UserError(
                    _('Could not link %s, check that this project'
                      ' keys exists in JIRA.') % (self.jira_key)
                )
            self._link_with_jira_project(work, jira_project)

    def _link_with_jira_project(self, work, jira_project):
        values = self._prepare_link_binding_values(jira_project)
        self.jira_project_id = self.env['jira.project.project'].create(
            values
        )
        type_binder = work.component(usage='binder',
                                     model_name='jira.issue.type')
        issue_types = self.env['jira.issue.type'].browse()
        for jira_issue_type in jira_project.issueTypes:
            issue_types |= type_binder.to_internal(
                jira_issue_type.id
            )
        self.sync_issue_type_ids = issue_types.ids

    def _prepare_link_binding_values(self, jira_project):
        values = self._prepare_base_binding_values()
        values.update({
            'sync_action': self.sync_action,
            'external_id': jira_project.id,
        })
        return values

    def _copy_issue_types(self):
        self.jira_project_id.sync_issue_type_ids = self.sync_issue_type_ids.ids
