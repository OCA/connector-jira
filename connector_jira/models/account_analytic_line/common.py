# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.addons.queue_job.job import job

from odoo.addons.component.core import Component


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
        with backend.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            importer.run(worklog_id, issue_id=issue_id, force=force)

    @job(default_channel='root.connector_jira.import')
    @api.model
    def delete_record(self, backend, issue_id, worklog_id):
        """ Delete a local worklog which has been deleted on JIRA """
        with backend.work_on(self._name) as work:
            importer = work.component(usage='record.deleter')
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
    # fields needed to display JIRA issue link in views
    jira_compound_key = fields.Char(
        related='task_id.jira_compound_key',
        readonly=True,
        store=True,
    )
    jira_issue_url = fields.Char(
        related='task_id.jira_issue_url',
        readonly=True,
    )

    jira_epic_compound_key = fields.Char(
        related='task_id.jira_epic_link_task_id.jira_compound_key',
        readonly=True,
        store=True
    )

    jira_epic_issue_url = fields.Char(
        string='JIRA epic URL',
        related='task_id.jira_epic_link_task_id.jira_issue_url',
        readonly=True
    )

    jira_issue_type = fields.Char(
        related='task_id.jira_issue_type',
        readonly=True,
        store=True
    )


class WorklogAdapter(Component):
    _name = 'jira.worklog.adapter'
    _inherit = 'jira.webservice.adapter'
    _apply_on = ['jira.account.analytic.line']

    def read(self, issue_id, worklog_id):
        return self.client.worklog(issue_id, worklog_id).raw

    def search(self, issue_id):
        """ Search worklogs of an issue """
        worklogs = self.client.worklogs(issue_id)
        return [worklog.id for worklog in worklogs]
