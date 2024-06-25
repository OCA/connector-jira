# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    jira_issue_key = fields.Char(readonly=True)
    jira_epic_issue_key = fields.Char(readonly=True)
    jira_issue_type_id = fields.Many2one("jira.issue.type", readonly=True)

    @api.model
    def _select(self):
        return (
            super()._select()
            + """,
            A.jira_issue_key AS jira_issue_key,
            A.jira_epic_issue_key AS jira_epic_issue_key,
            A.jira_issue_type_id AS jira_issue_type_id
        """
        )
