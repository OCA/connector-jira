# Copyright 2020-2021 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import api, fields, models


class JiraAccountAnalyticLine(models.Model):
    _inherit = "jira.account.analytic.line"

    jira_servicedesk_issue_url = fields.Char(
        string="Original JIRA service desk issue Link",
        compute="_compute_jira_servicedesk_issue_url",
    )

    @api.depends("jira_issue_key", "project_id.jira_bind_ids")
    def _compute_jira_servicedesk_issue_url(self):
        """Compute the external URL to JIRA service desk."""
        for record in self:
            url = ""
            if jira_key := record.jira_issue_key:
                if jira_project := record.project_id.jira_bind_ids[:1]:
                    url = jira_project.make_servicedesk_issue_url(jira_key)
            record.jira_servicedesk_issue_url = url
