# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json
import logging
import re
import tempfile

from jira import JIRAError
from jira.utils import json_loads

from odoo import api, fields, models, exceptions, _

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class JiraProjectProject(models.Model):
    _name = 'jira.project.project'
    _inherit = 'jira.binding'
    _inherits = {'project.project': 'odoo_id'}
    _description = 'Jira Projects'

    odoo_id = fields.Many2one(comodel_name='project.project',
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
    project_template_shared = fields.Char(
        string='Default Shared Template',
    )

    @api.model
    def _selection_project_template(self):
        return self.env['jira.backend']._selection_project_template()

    @api.onchange('backend_id')
    def onchange_project_backend_id(self):
        self.project_template = self.backend_id.project_template
        self.project_template_shared = self.backend_id.project_template_shared

    @staticmethod
    def _jira_key_valid(key):
        return bool(re.match(r'^[A-Z][A-Z0-9]{1,9}$', key))

    @api.constrains('project_template_shared')
    def check_project_template_shared(self):
        for binding in self:
            if not binding.project_template_shared:
                continue
            if not self._jira_key_valid(binding.project_template_shared):
                raise exceptions.ValidationError(
                    _('%s is not a valid JIRA Key') %
                    binding.project_template_shared
                )

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
        inverse_name='odoo_id',
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

    @api.constrains('jira_key')
    def check_jira_key(self):
        for project in self:
            if not project.jira_key:
                continue
            valid = self.env['jira.project.project']._jira_key_valid
            if not valid(project.jira_key):
                raise exceptions.ValidationError(
                    _('%s is not a valid JIRA Key') % project.jira_key
                )

    @api.depends('jira_bind_ids')
    def _compute_jira_exportable(self):
        for project in self:
            project.jira_exportable = bool(project.jira_bind_ids)

    @api.multi
    def write(self, values):
        result = super(ProjectProject, self).write(values)
        for record in self:
            if record.jira_exportable and not record.jira_key:
                raise exceptions.UserError(
                    _('The JIRA Key is mandatory on JIRA projects.')
                )
        return result

    @api.multi
    def name_get(self):
        names = []
        for project in self:
            project_id, name = super(ProjectProject, project).name_get()[0]
            if project.jira_key:
                name = '[%s] %s' % (project.jira_key, name)
            names.append((project_id, name))
        return names


class ProjectAdapter(Component):

    _name = 'jira.project.adapter'
    _inherit = ['jira.webservice.adapter']
    _apply_on = ['jira.project.project']

    def read(self, id_):
        return self.get(id_).raw

    def get(self, id_):
        return self.client.project(id_)

    def write(self, id_, values):
        self.get(id_).update(values)

    def create(self, key=None, name=None, template_name=None, values=None):
        project = self.client.create_project(
            key=key,
            name=name,
            template_name=template_name,
        )
        if values:
            project.update(values)
        return project

    def create_shared(self, key=None, name=None, shared_key=None, lead=None):
        assert key and name and shared_key
        # There is no public method for creating a shared project:
        # https://jira.atlassian.com/browse/JRA-45929
        # People found a private method for doing so, which is explained on:
        # https://jira.atlassian.com/browse/JRA-27256?src=confmacro&_ga=1.162710906.750569280.1479368101

        try:
            project = self.read(shared_key)
            project_id = project['id']
        except JIRAError as err:
            if err.status_code == 404:
                raise exceptions.UserError(
                    _('Project template with key "%s" not found.') % shared_key
                )
            else:
                raise

        url = (self.client._options['server'] +
               '/rest/project-templates/1.0/createshared/%s' % project_id)
        payload = {'name': name,
                   'key': key,
                   'lead': lead,
                   }

        r = self.client._session.post(url, data=json.dumps(payload))
        if r.status_code == 200:
            r_json = json_loads(r)
            return r_json

        f = tempfile.NamedTemporaryFile(
            suffix='.html',
            prefix='python-jira-error-create-shared-project-',
            delete=False)
        f.write(r.text)

        if self.logging:
            logging.error(
                "Unexpected result while running create shared project."
                "Server response saved in %s for further investigation "
                "[HTTP response=%s]." % (f.name, r.status_code))
        return False
