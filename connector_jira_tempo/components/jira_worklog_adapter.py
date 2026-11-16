# Copyright 2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import datetime
import json

from odoo.addons.component.core import Component


class JiraWorklogAdapter(Component):
    _inherit = "jira.worklog.adapter"

    def read(self, issue_id, worklog_id):
        worklog = super().read(issue_id, worklog_id)
        if self.env.context.get("jira_worklog_no_tempo_timesheets_approval_data"):
            return worklog
        with self.handle_404():
            approval = self.tempo_timesheets_approval_read(worklog)
            worklog["_tempo_timesheets_approval"] = approval
        return worklog

    def tempo_timesheets_approval_read(self, worklog):
        backend = self._tempo_timesheets_get_webservice()
        account_id = worklog["author"]["accountId"]
        period_start = datetime.date.today().isoformat()
        endpoint = f"timesheet-approvals/user/{account_id}?from={period_start}"
        return json.loads(backend.call("get", url_params={"endpoint": endpoint}))

    def tempo_timesheets_approval_read_status_by_team(self, team_id, period_start):
        backend = self._tempo_timesheets_get_webservice()
        endpoint = f"timesheet-approvals/team/{team_id}?from={period_start}"
        return json.loads(backend.call("get", url_params={"endpoint": endpoint}))
