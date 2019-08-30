# Copyright 2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

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

    def read(self, issue_id, worklog_id):
        worklog = super().read(issue_id, worklog_id)
        if self.env.context.get(
                'jira_worklog_no_tempo_timesheets_approval_data'):
            return worklog
        with self.handle_404():
            worklog['_tempo_timesheets_approval'] = \
                self.tempo_timesheets_approval_read(worklog)
        return worklog

    # This one seems useless ATM.
    # def tempo_read_worklog(self, worklog):
    #     url = self._tempo_timesheets_get_url('worklogs')
    #     r = self.client._session.get(url, params={'dateFrom': '2018-01-01'})
    #     return {}

    def tempo_timesheets_approval_read(self, worklog):
        url = self._tempo_timesheets_get_url('timesheet-approval/current')
        with self.handle_404():
            response = self.client._session.get(url, params={
                'username': worklog['author']['name'],
            })
        return response.json()

    def tempo_timesheets_approval_read_status_by_team(
            self, team_id, period_start):
        url = self._tempo_timesheets_get_url('timesheet-approval')
        with self.handle_404():
            response = self.client._session.get(url, params={
                'teamId': team_id,
                'periodStartDate': period_start,
            })
        return response.json()
