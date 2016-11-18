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
)
from ...unit.mapper import iso8601_local_date
from ...backend import jira


@jira
class AnalyticLineMapper(ImportMapper):
    _model_name = 'jira.account.analytic.line'

    direct = [
        ('comment', 'name'),
        (iso8601_local_date('started'), 'date'),
        ]

    @only_create
    @mapping
    def default(self, record):
        return {'is_timesheet': True}

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
    def task(self, record):
        jira_issue_id = record['issueId']
        binder = self.binder_for('jira.project.task')
        task = binder.to_openerp(jira_issue_id, unwrap=True)
        if not task:
            raise MappingError(
                _('Issue "%s" could not be imported, so the worklog "%s"'
                  'cannot be imported as well.') %
                  (jira_issue_id, record['id'])
            )
        analytic_id = task.project_id.analytic_account_id.id
        return {'task_id': task.id, 'account_id': analytic_id}

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
        super(JiraImporter, self).__init__(environment)
        self.external_issue_id = None

    def run(self, external_id, force=False, record=None, **kwargs):
        assert 'issue_id' in kwargs
        self.external_issue_id = kwargs.pop('issue_id')
        return super(AnalyticLineImporter, self).run(
            external_id, force=force, record=record, **kwargs
        )

    def _get_external_data(self):
        """ Return the raw Jira data for ``self.external_id`` """
        return self.backend_adapter.read(self.external_issue_id,
                                         self.external_id)

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        self._import_dependency(self.external_issue_id,
                                'jira.project.task')

        jira_assignee = self.external_record['author']
        jira_key = jira_assignee.get('key')
        self._import_dependency(jira_key,
                                'jira.res.users',
                                record=jira_assignee)


@job(default_channel='root.connector_jira.normal')
def import_worklog(session, model_name, backend_id, issue_id, worklog_id,
                   force=False):
    """ Import a worklog from Jira """
    backend = session.env['jira.backend'].browse(backend_id)
    with backend.get_environment(model_name, session=session) as connector_env:
        importer = connector_env.get_connector_unit(JiraImporter)
        importer.run(worklog_id, issue_id=issue_id, force=force)
