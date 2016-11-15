# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import fields, models

from ...unit.backend_adapter import JiraAdapter
from ...backend import jira


class JiraAccountAnalyticLine(models.Model):
    _name = 'jira.account.analytic.line'
    _inherit = 'jira.binding'
    _inherits = {'account.analytic.line': 'openerp_id'}
    _description = 'Jira Worklog'

    openerp_id = fields.Many2one(comodel_name='account.analytic.line',
                                 string='Timesheet Line',
                                 required=True,
                                 index=True,
                                 ondelete='restrict')
    # The REST API needs issue id + worklog id, so we keep it along
    # in case we'll need it for an eventual export
    jira_issue_id = fields.Char()


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    jira_bind_ids = fields.One2many(
        comodel_name='jira.account.analytic.line',
        inverse_name='openerp_id',
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
        return self.client.worklogs(issue_id)
