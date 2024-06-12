# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    jira_issue_key = fields.Char("Original Task Key", readonly=True)
    jira_epic_issue_key = fields.Char("Original JIRA Epic Key", readonly=True)

    @api.model
    def _select(self):
        res = super()._select()
        res += ", A.jira_issue_key AS jira_issue_key"
        res += ", A.jira_epic_issue_key AS jira_epic_issue_key"
        return res
