# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models
from odoo.addons.component.core import Component


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    jira_tempo_status = fields.Selection(
        selection=[
            ('approved', 'Approved'),
            ('waiting_for_approval', 'Waiting for approval'),
            ('ready_to_submit', 'Ready to submit'),
            ('open', 'Open'),
        ]
    )


class WorklogAdapter(Component):
    _inherit = 'jira.worklog.adapter'

    # SPECS
    # http://developer.tempo.io/doc/timesheets/api/rest/latest
    # the base path must be overridden otherwise
    # `_get_url` will give us back a bad path including the std JIRA one
    _tempo_api_path_base = '{server}/rest/tempo-timesheets/3/{path}'

    def _tempo_get_url(self, path):
        return self.client._get_url(path, base=self._tempo_api_path_base)

    def read(self, issue_id, worklog_id):
        worklog = super().read(issue_id, worklog_id)
        if self.env.context.get('jira_worklog_no_tempo_data'):
            return worklog
        with self.handle_404():
            worklog['_timesheet'] = self.tempo_read_approval(worklog)
        return worklog

    # This one seems useless ATM.
    # def tempo_read_worklog(self, worklog):
    #     url = self._tempo_get_url('worklogs')
    #     r = self.client._session.get(url, params={'dateFrom': '2018-01-01'})
    #     return {}

    def tempo_read_approval(self, worklog):
        username = worklog['author']['name']
        url = self._tempo_get_url('timesheet-approval/current')
        with self.handle_404():
            resp = self.client._session.get(url, params={'username': username})
        return resp.json()

    def tempo_read_status_by_team(self, team_id, period_start):
        url = self._tempo_get_url('timesheet-approval')
        params = {
            'teamId': team_id,
            'periodStartDate': period_start
        }
        with self.handle_404():
            resp = self.client._session.get(url, params=params)
        return resp.json()
