# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    jira_tempo_status = fields.Selection(
        selection=[
            ("approved", "Approved"),
            ("in_review", "In Review"),
            # no longer used on cloud version
            ("waiting_for_approval", "Waiting for approval"),
            # no longer used on cloud version
            ("ready_to_submit", "Ready to submit"),
            ("open", "Open"),
        ],
        readonly=True,
    )

    @api.model
    def _select(self):
        return super()._select() + ", A.jira_tempo_status AS jira_tempo_status"
