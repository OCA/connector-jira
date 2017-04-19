# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _
from odoo.addons.connector.exception import MappingError
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.component.core import Component


class ProjectTaskMapper(Component):
    _name = 'jira.project.task.mapper'
    _inherit = 'base.import.mapper'
    _apply_on = ['jira.project.task']

    direct = [
        ('key', 'jira_key'),
    ]

    from_fields = [
        ('summary', 'name'),
        ('duedate', 'date_deadline'),
    ]

    @mapping
    def from_attributes(self, record):
        return self.component(usage='map.from.attrs').values(
            record, self
        )

    @mapping
    def issue_type(self, record):
        binder = self.binder_for('jira.issue.type')
        jira_type_id = record['fields']['issuetype']['id']
        binding = binder.to_internal(jira_type_id)
        return {'jira_issue_type_id': binding.id}

    @mapping
    def assignee(self, record):
        assignee = record['fields'].get('assignee')
        if not assignee:
            return {'user_id': False}
        jira_key = assignee['key']
        binder = self.binder_for('jira.res.users')
        user = binder.to_internal(jira_key, unwrap=True)
        if not user:
            email = assignee['emailAddress']
            raise MappingError(
                _('No user found with login "%s" or email "%s".'
                  'You must create a user or link it manually if the '
                  'login/email differs.') % (jira_key, email)
            )
        return {'user_id': user.id}

    @mapping
    def description(self, record):
        # TODO: description is a variant of wiki syntax...
        # and the Odoo field is HTML...
        return {'description': record['fields']['description']}

    @mapping
    def project(self, record):
        jira_project_id = record['fields']['project']['id']
        binder = self.binder_for('jira.project.project')
        project = binder.to_internal(jira_project_id, unwrap=True)
        return {'project_id': project.id}

    @mapping
    def epic(self, record):
        if not self.options.jira_epic:
            return {}
        jira_epic_id = self.options.jira_epic['id']
        binder = self.binder_for('jira.project.task')
        binding = binder.to_internal(jira_epic_id)
        return {'jira_epic_link_id': binding.id}

    @mapping
    def parent(self, record):
        jira_parent = record['fields'].get('parent', {})
        if not jira_parent:
            return {}
        jira_parent_id = jira_parent['id']
        binder = self.binder_for('jira.project.task')
        binding = binder.to_internal(jira_parent_id)
        return {'jira_parent_id': binding.id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


class ProjectTaskBatchImporter(Component):
    """ Import the Jira tasks

    For every id in in the list of tasks, a delayed job is created.
    Import from a date
    """
    _name = 'jira.project.task.batch.importer'
    _inherit = ['jira.delayed.batch.importer']
    _apply_on = ['jira.project.task']


class ProjectTaskImporter(Component):
    _name = 'jira.project.task.importer'
    _inherit = ['jira.importer']
    _apply_on = ['jira.project.task']

    def __init__(self, work_context):
        super().__init__(work_context)
        self.jira_epic = None

    def _get_external_data(self):
        """ Return the raw Jira data for ``self.external_id`` """
        result = super()._get_external_data()
        epic_field_name = self.backend_record.epic_link_field_name
        if epic_field_name:
            issue_adapter = self.component(
                usage='backend.adapter',
                model_name='jira.project.task'
            )
            epic_key = result['fields'][epic_field_name]
            if epic_key:
                self.jira_epic = issue_adapter.read(epic_key)
        return result

    def _is_issue_type_sync(self):
        jira_project_id = self.external_record['fields']['project']['id']
        binder = self.binder_for('jira.project.project')
        project_binding = binder.to_internal(jira_project_id)
        task_sync_type_id = self.external_record['fields']['issuetype']['id']
        task_sync_type_binder = self.binder_for('jira.issue.type')
        task_sync_type_binding = task_sync_type_binder.to_internal(
            task_sync_type_id,
        )
        return task_sync_type_binding.is_sync_for_project(project_binding)

    def _create_data(self, map_record, **kwargs):
        return super()._create_data(map_record, jira_epic=self.jira_epic)

    def _update_data(self, map_record, **kwargs):
        return super()._update_data(map_record, jira_epic=self.jira_epic)

    def _import(self, binding, **kwargs):
        # called at the beginning of _import because we must be sure
        # that dependencies are there (project and issue type)
        if not self._is_issue_type_sync():
            return _('Project or issue type is not synchronized.')
        return super()._import(binding, **kwargs)

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        jira_assignee = self.external_record['fields'].get('assignee') or {}
        jira_key = jira_assignee.get('key')
        self._import_dependency(jira_key,
                                'jira.res.users',
                                record=jira_assignee)

        jira_issue_type = self.external_record['fields']['issuetype']
        jira_issue_type_id = jira_issue_type['id']
        self._import_dependency(jira_issue_type_id, 'jira.issue.type',
                                record=jira_issue_type)

        jira_parent = self.external_record['fields'].get('parent')
        if jira_parent:
            jira_parent_id = jira_parent['id']
            self._import_dependency(jira_parent_id, 'jira.project.task',
                                    record=jira_parent)

        if self.jira_epic:
            self._import_dependency(self.jira_epic['id'], 'jira.project.task',
                                    record=self.jira_epic)
