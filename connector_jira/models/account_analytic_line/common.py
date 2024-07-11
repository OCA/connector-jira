# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.addons.queue_job.job import job, related_action

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

    # we have to store these fields on the analytic line because
    # they may be different than the ones on their odoo task:
    # for instance, we do not import "Tasks" but we import "Epics",
    # the analytic line for a "Task" will be linked to an "Epic" on
    # Odoo, but we still want to know the original task here
    jira_issue_key = fields.Char(
        string='Original Task Key',
        readonly=True,
    )
    jira_issue_type_id = fields.Many2one(
        comodel_name='jira.issue.type',
        string='Original Issue Type',
        readonly=True,
    )
    jira_issue_url = fields.Char(
        string='Original JIRA issue Link',
        compute='_compute_jira_issue_url',
    )
    jira_epic_issue_key = fields.Char(
        string='Original Epic Key',
        readonly=True,
    )
    jira_epic_issue_url = fields.Char(
        string='Original JIRA Epic Link',
        compute='_compute_jira_issue_url',
    )

    _sql_constraints = [
        ('jira_binding_backend_uniq', 'unique(backend_id, odoo_id)',
         "A binding already exists for this line and this backend."),
    ]

    @api.depends('jira_issue_key', 'jira_epic_issue_key')
    def _compute_jira_issue_url(self):
        """Compute the external URL to JIRA."""
        for record in self:
            record.jira_issue_url = self.backend_id.make_issue_url(
                record.jira_issue_key
            )
            record.jira_epic_issue_url = self.backend_id.make_issue_url(
                record.jira_epic_issue_key
            )

    @job(default_channel='root.connector_jira.import')
    @related_action(action="related_action_jira_link")
    @api.model
    def import_record(self, backend, issue_id, worklog_id, force=False):
        """ Import a worklog from JIRA """
        with backend.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(worklog_id, issue_id=issue_id, force=force)

    @job(default_channel='root.connector_jira.import')
    @api.model
    def delete_record(self, backend, issue_id, worklog_id):
        """ Delete a local worklog which has been deleted on JIRA """
        with backend.work_on(self._name) as work:
            importer = work.component(usage='record.deleter')
            return importer.run(worklog_id)

    @api.multi
    def force_reimport(self):
        for binding in self.mapped('jira_bind_ids'):
            binding.with_delay(priority=8).import_record(
                binding.backend_id,
                binding.jira_issue_id,
                binding.external_id,
                force=True,
            )


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
    jira_issue_key = fields.Char(
        string='Original JIRA Issue Key',
        compute='_compute_jira_references',
        readonly=True,
        store=True,
    )
    jira_issue_url = fields.Char(
        string='Original JIRA issue Link',
        compute='_compute_jira_references',
        readonly=True,
    )
    jira_epic_issue_key = fields.Char(
        compute='_compute_jira_references',
        string='Original JIRA Epic Key',
        readonly=True,
        store=True,
    )
    jira_epic_issue_url = fields.Char(
        string='Original JIRA Epic Link',
        compute='_compute_jira_references',
        readonly=True
    )

    jira_issue_type_id = fields.Many2one(
        comodel_name='jira.issue.type',
        string='Original JIRA Issue Type',
        compute='_compute_jira_references',
        readonly=True,
        store=True
    )

    @api.depends(
        'jira_bind_ids.jira_issue_key',
        'jira_bind_ids.jira_issue_type_id',
        'jira_bind_ids.jira_epic_issue_key',
    )
    def _compute_jira_references(self):
        """Compute the various references to JIRA.

        We assume that we have only one external record for a line
        """
        for record in self:
            if not record.jira_bind_ids:
                continue
            main_binding = record.jira_bind_ids[0]
            record.jira_issue_key = main_binding.jira_issue_key
            record.jira_issue_url = main_binding.jira_issue_url
            record.jira_issue_type_id = main_binding.jira_issue_type_id
            record.jira_epic_issue_key = main_binding.jira_epic_issue_key
            record.jira_epic_issue_url = main_binding.jira_epic_issue_url


class WorklogAdapter(Component):
    _name = 'jira.worklog.adapter'
    _inherit = 'jira.webservice.adapter'
    _apply_on = ['jira.account.analytic.line']

    def read(self, issue_id, worklog_id):
        with self.handle_404():
            return self.client.worklog(issue_id, worklog_id).raw

    def search(self, issue_id):
        """ Search worklogs of an issue """
        worklogs = self.client.worklogs(issue_id)
        return [worklog.id for worklog in worklogs]
