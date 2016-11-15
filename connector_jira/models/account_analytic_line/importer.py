# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import _
from openerp.addons.connector.exception import MappingError
from openerp.addons.connector.unit.mapper import (
    ImportMapper,
    mapping,
    only_create,
)
from openerp.addons.connector.queue.job import job
from ...unit.importer import (
    DelayedBatchImporter,
    JiraImporter,
    JiraDeleter,
)
from ...unit.backend_adapter import JiraAdapter
from ...unit.mapper import iso8601_local_date, whenempty
from ...backend import jira


@jira
class AnalyticLineMapper(ImportMapper):
    _model_name = 'jira.account.analytic.line'

    direct = [
        (whenempty('comment', _('missing description')), 'name'),
        (iso8601_local_date('started'), 'date'),
        ]

    @only_create
    @mapping
    def default(self, record):
        return {'is_timesheet': True}

    @mapping
    def issue(self, record):
        return {'jira_issue_id': record['issueId']}

    @mapping
    def duration(self, record):
        spent = float(record['timeSpentSeconds'])
        # amount is in float in odoo... 2h30 = 2.5
        return {'unit_amount': spent / 60 / 60}

    @mapping
    def author(self, record):
        jira_author = record['author']
        jira_author_key = jira_author['key']
        binder = self.binder_for('jira.res.users')
        user = binder.to_openerp(jira_author_key, unwrap=True)
        if not user:
            email = jira_author['emailAddress']
            raise MappingError(
                _('No user found with login "%s" or email "%s".'
                  'You must create a user or link it manually if the '
                  'login/email differs.') % (jira_author_key, email)
            )
        return {'user_id': user.id}

    @mapping
    def project_and_task(self, record):
        task_binding = self.options.task_binding

        if not task_binding:
            issue = self.options.linked_issue
            assert issue
            project_binder = self.binder_for('jira.project.project')
            jira_project_id = issue['fields']['project']['id']
            project = project_binder.to_openerp(jira_project_id, unwrap=True)
            # we can link to any task so we create the worklog
            # on the project without any task
            return {'account_id': project.analytic_account_id.id}

        analytic = task_binding.project_id.analytic_account_id
        return {'task_id': task_binding.openerp_id.id,
                'account_id': analytic.id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@jira
class AnalyticLineBatchImporter(DelayedBatchImporter):
    """ Import the Jira worklogs

    For every id in in the list, a delayed job is created.
    Import from a date
    """
    _model_name = 'jira.account.analytic.line'


@jira
class AnalyticLineImporter(JiraImporter):
    _model_name = 'jira.account.analytic.line'

    def __init__(self, environment):
        super(AnalyticLineImporter, self).__init__(environment)
        self.external_issue_id = None
        self.task_binding = None

    def _recurse_import_task(self):
        """ Import and return the task of proper type for the worklog

        As we decide which type of issues are imported for a project,
        a worklog could be linked to an issue that we don't import.
        In that case, we climb the parents of the issue until we find
        a issue of a type we synchronize.

        It ensures that the 'to-be-linked' issue is imported and return it.

        """
        issue_adapter = self.unit_for(JiraAdapter, model='jira.project.task')
        project_binder = self.binder_for('jira.project.project')
        issue_binder = self.binder_for('jira.project.task')
        issue_type_binder = self.binder_for('jira.issue.type')
        jira_issue_id = self.external_record['issueId']
        epic_field_name = self.backend_record.epic_link_field_name
        current_project_id = self.external_issue['fields']['project']['id']
        while jira_issue_id:
            issue = issue_adapter.read(
                jira_issue_id,
                fields=['issuetype', 'project', 'parent', epic_field_name],
            )
            jira_project_id = issue['fields']['project']['id']
            jira_issue_type_id = issue['fields']['issuetype']['id']
            project_binding = project_binder.to_openerp(jira_project_id)
            issue_type_binding = issue_type_binder.to_openerp(
                jira_issue_type_id
            )
            # JIRA allows to set an EPIC of a different project.
            # If it happens, we discard it.
            if (jira_project_id == current_project_id and
                    issue_type_binding.is_sync_for_project(project_binding)):
                break
            if issue['fields'].get('parent'):
                # 'parent' is used on sub-tasks relating to their parent task
                jira_issue_id = issue['fields']['parent']['id']
            elif issue['fields'].get(epic_field_name):
                # the epic link is set on a jira custom field
                epic_key = issue['fields'][epic_field_name]
                epic = issue_adapter.read(epic_key, fields='id')
                # we got the key of the epic issue, so we translate
                # it to the ID with a call to the API
                jira_issue_id = epic['id']
            else:
                # no parent issue of a type we are synchronizing has been
                # found, the worklog will be assigned to no task
                jira_issue_id = None

        if jira_issue_id:
            self._import_dependency(jira_issue_id, 'jira.project.task')
            return issue_binder.to_openerp(jira_issue_id)

    def _create_data(self, map_record, **kwargs):
        _super = super(AnalyticLineImporter, self)
        return _super._create_data(map_record,
                                   task_binding=self.task_binding,
                                   linked_issue=self.external_issue)

    def _update_data(self, map_record, **kwargs):
        _super = super(AnalyticLineImporter, self)
        return _super._update_data(map_record,
                                   task_binding=self.task_binding,
                                   linked_issue=self.external_issue)

    def run(self, external_id, force=False, record=None, **kwargs):
        assert 'issue_id' in kwargs
        self.external_issue_id = kwargs.pop('issue_id')
        return super(AnalyticLineImporter, self).run(
            external_id, force=force, record=record, **kwargs
        )

    def _get_external_data(self):
        """ Return the raw Jira data for ``self.external_id`` """
        issue_adapter = self.unit_for(JiraAdapter, model='jira.project.task')
        self.external_issue = issue_adapter.read(self.external_issue_id)
        return self.backend_adapter.read(self.external_issue_id,
                                         self.external_id)

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        self.task_binding = self._recurse_import_task()
        jira_assignee = self.external_record['author']
        jira_key = jira_assignee.get('key')
        self._import_dependency(jira_key,
                                'jira.res.users',
                                record=jira_assignee)


@jira
class AnalyticLineDeleter(JiraDeleter):
    _model_name = 'jira.account.analytic.line'


@job(default_channel='root.connector_jira.normal')
def import_worklog(session, model_name, backend_id, issue_id, worklog_id,
                   force=False):
    """ Import a worklog from Jira """
    backend = session.env['jira.backend'].browse(backend_id)
    with backend.get_environment(model_name, session=session) as connector_env:
        importer = connector_env.get_connector_unit(JiraImporter)
        importer.run(worklog_id, issue_id=issue_id, force=force)


@job(default_channel='root.connector_jira.normal')
def delete_worklog(session, model_name, backend_id, issue_id, worklog_id):
    """ Delete a local workflow which has been deleted on JIRA """
    backend = session.env['jira.backend'].browse(backend_id)
    with backend.get_environment(model_name, session=session) as connector_env:
        deleter = connector_env.get_connector_unit(JiraDeleter)
        deleter.run(worklog_id)
