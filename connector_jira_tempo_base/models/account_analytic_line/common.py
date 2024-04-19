# Copyright 2018 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import json

from odoo import _, exceptions

from odoo.addons.component.core import Component


class WorklogAdapter(Component):
    _inherit = "jira.worklog.adapter"

    _tempo_timesheets_api_path_base = "{server}/rest/tempo-timesheets/3/{path}"

    def _tempo_timesheets_get_webservice(self):
        backend = self.collection.tempo_ws_backend_id
        return backend

    def read(self, issue_id, worklog_id):
        worklog = super().read(issue_id, worklog_id)
        if self.env.context.get("jira_worklog_no_tempo_timesheets_data"):
            return worklog
        with self.handle_404():
            tempo_timesheet = self.tempo_timesheets_read(worklog_id)
            worklog.update(
                {
                    "_tempo_timesheets": tempo_timesheet,
                    "author": tempo_timesheet["author"],
                    "comment": tempo_timesheet["description"],
                    "tempo_worklog_id": tempo_timesheet["tempoWorklogId"],
                }
            )
        return worklog

    def _tempo_worklog_id(self, jira_worklog_id):
        jira_worklog_id = int(jira_worklog_id)
        backend = self._tempo_timesheets_get_webservice()
        endpoint = "worklogs/jira-to-tempo"
        payload = {"jiraWorklogIds": [jira_worklog_id]}
        response = backend.call("post", url_params={"endpoint": endpoint}, json=payload)
        response = json.loads(response)
        result = response["results"]
        for row in result:
            if row["jiraWorklogId"] == jira_worklog_id:
                return row["tempoWorklogId"]
        raise exceptions.UserError(_("Could not find a matching record"))

    def tempo_timesheets_read(self, jira_worklog_id):
        tempo_worklog_id = self._tempo_worklog_id(jira_worklog_id)
        backend = self._tempo_timesheets_get_webservice()
        endpoint = f"worklogs/{tempo_worklog_id}"
        response = backend.call("get", url_params={"endpoint": endpoint})
        return json.loads(response)
