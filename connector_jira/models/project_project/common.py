# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json
import logging
import re
import tempfile

try:
    from jira import JIRAError
    from jira.utils import json_loads
except ImportError:
    pass  # already logged in components/adapter.py

from odoo import api, fields, models, exceptions, _, tools

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class JiraProjectBaseFields(models.AbstractModel):
    """JIRA Project Base fields

    Shared by the binding jira.project.project
    and the wizard to link/create a JIRA project
    """
    _name = 'jira.project.base.mixin'

    jira_key = fields.Char(
        string='JIRA Key',
        kequired=True,
        size=10,  # limit on JIRA
    )
    sync_issue_type_ids = fields.Many2many(
        comodel_name='jira.issue.type',
        string='Issue Levels to Synchronize',
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
    )
    project_template_shared = fields.Char(
        string='Default Shared Template',
    )
    sync_action = fields.Selection(
        selection=[
            ('link', 'Link with JIRA'),
            ('export', 'Export to JIRA'),
        ],
        default='link',
        required=True,
        help="Defines if the information of the project (name "
             "and key) are exported to JIRA when changed. Link means"
             "the project already exists on JIRA, no sync of the project"
             " details once the link is established."
             " Tasks are always imported from JIRA, not pushed.",
    )

    @api.model
    def _selection_project_template(self):
        return self.env['jira.backend']._selection_project_template()


class JiraProjectProject(models.Model):
    _name = 'jira.project.project'
    _inherit = ['jira.binding', 'jira.project.base.mixin']
    _inherits = {'project.project': 'odoo_id'}
    _description = 'Jira Projects'

    odoo_id = fields.Many2one(comodel_name='project.project',
                              string='Project',
                              required=True,
                              index=True,
                              ondelete='restrict')
    project_type = fields.Selection(
        selection="_selection_project_type"
    )

    @api.model
    def _selection_project_type(self):
        return [
            ('software', 'Software'),
            ('business', 'Business'),
        ]

    # Disable and implement the constraint jira_binding_uniq as python because
    # we need to override the in connector_jira_service_desk and it would try
    # to create it again at every update because of the base implementation
    # in the binding's parent model.
    @api.model_cr
    def _add_sql_constraints(self):
        # we replace the sql constraint by a python one
        # to include the organizations
        constraints = []
        for (key, definition, msg) in self._sql_constraints:
            if key == 'jira_binding_uniq':
                conname = '%s_%s' % (self._table, key)
                has_definition = tools.constraint_definition(
                    self.env.cr, conname
                )
                if has_definition:
                    tools.drop_constraint(self.env.cr, self._table, conname)
            else:
                constraints.append((key, definition, msg))
        self._sql_constraints = constraints
        super()._add_sql_constraints()

    def _other_same_type_domain(self):
        """Return the domain to search a binding on the same project and type

        It is used for the constraint allowing only one binding of each type.
        The reason for this is:

        * supporting several projects of different types is a requirements (eg.
          1 service desk and 1 software)
        * but if we implement new features like "if I create a task it is
          pushed to Jira", with different projects we would not know where to
          push them

        Using this constraint, we'll be able to focus new export features by
        project type.

        """
        self.ensure_one()
        domain = [
            ('odoo_id', '=', self.odoo_id.id),
            ('backend_id', '=', self.backend_id.id),
            ('project_type', '=', self.project_type)
        ]
        if self.id:
            domain.append(
                ('id', '!=', self.id),
            )
        return domain

    @api.constrains('backend_id', 'odoo_id', 'project_type')
    def _constrains_odoo_jira_uniq(self):
        """Add a constraint on backend+odoo id

        More than one binding is tolerated but only one can be a master
        binding. The master binding will be used when we have to push data from
        Odoo to Jira (add tasks, ...).
        """
        for binding in self:
            same_link_bindings = self.with_context(active_test=False).search(
                self._other_same_type_domain()
            )
            if same_link_bindings:
                raise exceptions.ValidationError(_(
                    "The project \"%s\" already has a binding with "
                    "a Jira project of the same type (%s)."
                ) % (binding.display_name, self.project_type))

    @api.constrains('backend_id', 'external_id')
    def _constrains_jira_uniq(self):
        """Add a constraint on backend+jira id

        Defined as a python method rather than a postgres constraint
        in order to ease the override in connector_jira_servicedesk
        """
        for binding in self:
            if not binding.external_id:
                continue
            same_link_bindings = self.with_context(active_test=False).search([
                ('id', '!=', binding.id),
                ('backend_id', '=', binding.backend_id.id),
                ('external_id', '=', binding.external_id),
            ])
            if same_link_bindings:
                raise exceptions.ValidationError(_(
                    "The project %s is already linked with the same"
                    " JIRA project."
                ) % (same_link_bindings.display_name))

    @api.constrains('jira_key')
    def check_jira_key(self):
        for project in self:
            if not project.jira_key:
                continue
            if not self._jira_key_valid(project.jira_key):
                raise exceptions.ValidationError(
                    _('%s is not a valid JIRA Key') % project.jira_key
                )

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
        record = super().create(values)
        record._ensure_jira_key()
        return record

    @api.multi
    def write(self, values):
        if 'project_template' in values:
            raise exceptions.UserError(
                _('The project template cannot be modified.')
            )
        res = super().write(values)
        self._ensure_jira_key()
        return res

    @api.multi
    def _ensure_jira_key(self):
        if self.env.context.get('connector_no_export'):
            return
        for record in self:
            if not record.jira_key:
                raise exceptions.UserError(
                    _('The JIRA Key is mandatory in order to link a project')
                )

    @api.multi
    def unlink(self):
        if any(self.mapped('external_id')):
            raise exceptions.UserError(
                _('Exported project cannot be deleted.')
            )
        return super().unlink()


class ProjectProject(models.Model):
    _inherit = 'project.project'

    jira_bind_ids = fields.One2many(
        comodel_name='jira.project.project',
        inverse_name='odoo_id',
        copy=False,
        string='Project Bindings',
        context={'active_test': False},
    )
    jira_key = fields.Char(
        string='JIRA Key',
        compute='_compute_jira_key',
    )

    @api.depends('jira_bind_ids.jira_key')
    def _compute_jira_key(self):
        for project in self:
            keys = project.mapped('jira_bind_ids.jira_key')
            project.jira_key = ', '.join(keys)

    @api.multi
    def name_get(self):
        names = []
        for project in self:
            project_id, name = super(ProjectProject, project).name_get()[0]
            if project.jira_key:
                name = '[%s] %s' % (project.jira_key, name)
            names.append((project_id, name))
        return names

    @api.multi
    def create_and_link_jira(self):
        action_link = self.env.ref('connector_jira.open_project_link_jira')
        action = action_link.read()[0]
        action['context'] = dict(
            self.env.context,
            active_id=self.id,
            active_model=self._name,
        )
        return action


class ProjectAdapter(Component):

    _name = 'jira.project.adapter'
    _inherit = ['jira.webservice.adapter']
    _apply_on = ['jira.project.project']

    def read(self, id_):
        with self.handle_404():
            return self.get(id_).raw

    def get(self, id_):
        with self.handle_404():
            return self.client.project(id_)

    def write(self, id_, values):
        with self.handle_404():
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
