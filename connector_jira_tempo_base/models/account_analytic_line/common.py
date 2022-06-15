# Copyright 2018 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class WorklogAdapter(Component):
    _inherit = "jira.worklog.adapter"

    _tempo_timesheets_api_path_base = "{server}/rest/tempo-timesheets/3/{path}"

    def _tempo_timesheets_get_url(self, path):
        return self.client._get_url(
            path,
            base=self._tempo_timesheets_api_path_base,
        )

    def read(self, issue_id, worklog_id):
        worklog = super().read(issue_id, worklog_id)
        if self.env.context.get("jira_worklog_no_tempo_timesheets_data"):
            return worklog
        with self.handle_404():
            worklog["_tempo_timesheets"] = self.tempo_timesheets_read(worklog_id)
        return worklog

    def tempo_timesheets_read(self, worklog_id):
        url = self._tempo_timesheets_get_url("worklogs/%s" % worklog_id)
        with self.handle_404():
            response = self.client._session.get(url)
        return response.json()
