# Copyright 2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import datetime
import json

from odoo import fields, models

from odoo.addons.component.core import Component


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    jira_tempo_status = fields.Selection(
        selection=[
            ("approved", "Approved"),
            ("in_review", "In Review"),
            (
                "waiting_for_approval",
                "Waiting for approval",
            ),  # no longer used on cloud version
            ("ready_to_submit", "Ready to submit"),  # no longer used on cloud version
            ("open", "Open"),
        ]
    )


class WorklogAdapter(Component):
    _inherit = "jira.worklog.adapter"

    def read(self, issue_id, worklog_id):
        worklog = super().read(issue_id, worklog_id)
        if self.env.context.get("jira_worklog_no_tempo_timesheets_approval_data"):
            return worklog
        with self.handle_404():
            worklog["_tempo_timesheets_approval"] = self.tempo_timesheets_approval_read(
                worklog
            )
        return worklog

    def tempo_timesheets_approval_read(self, worklog):
        backend = self._tempo_timesheets_get_webservice()
        account_id = worklog["author"]["accountId"]
        period_start = datetime.date.today().isoformat()
        response = backend.call(
            "get",
            url_params={
                "endpoint": f"timesheet-approvals/user/{account_id}?from={period_start}"
            },
        )
        return json.loads(response)

    def tempo_timesheets_approval_read_status_by_team(
        self, team_id, period_start
    ):  # noqa
        backend = self._tempo_timesheets_get_webservice()
        response = backend.call(
            "get",
            url_params={
                "endpoint": f"timesheet-approvals/team/{team_id}?from={period_start}"
            },
        )
        return json.loads(response)
