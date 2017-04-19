# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.addons.queue_job.job import job

from ...unit.backend_adapter import JiraAdapter
from ...unit.importer import JiraImporter, JiraDeleter
from ...backend import jira


class JiraAccountAnalyticLine(models.Model):
    _name = 'jira.account.analytic.line'
    _inherit = 'jira.binding'
    _inherits = {'account.analytic.line': 'odoo_id'}
    _description = 'Jira Worklog'

    odoo_id = fields.Many2one(comodel_name='account.analytic.line',
                              string='Timesheet Line',
                              required=True,
                              index=True,
                              ondelete='restrict')
    # The REST API needs issue id + worklog id, so we keep it along
    # in case we'll need it for an eventual export
    jira_issue_id = fields.Char()

    @job(default_channel='root.connector_jira.import')
    @api.model
    def import_record(self, backend, issue_id, worklog_id, force=False):
        """ Import a worklog from JIRA """
        with backend.get_environment(self._name) as connector_env:
            importer = connector_env.get_connector_unit(JiraImporter)
            importer.run(worklog_id, issue_id=issue_id, force=force)

    @job(default_channel='root.connector_jira.import')
    @api.model
    def delete_record(self, backend, issue_id, worklog_id):
        """ Delete a local worklog which has been deleted on JIRA """
        with backend.get_environment(self._name) as connector_env:
            importer = connector_env.get_connector_unit(JiraDeleter)
            importer.run(worklog_id)


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    jira_bind_ids = fields.One2many(
        comodel_name='jira.account.analytic.line',
        inverse_name='odoo_id',
        copy=False,
        string='Worklog Bindings',
        context={'active_test': False},
    )


@jira
class WorklogAdapter(JiraAdapter):
    _model_name = 'jira.account.analytic.line'

    def read(self, issue_id, worklog_id):
        return self.client.worklog(issue_id, worklog_id).raw

    def search(self, issue_id):
        """ Search worklogs of an issue """
        worklogs = self.client.worklogs(issue_id)
        return [worklog.id for worklog in worklogs]
