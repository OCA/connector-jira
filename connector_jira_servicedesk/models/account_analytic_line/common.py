# Copyright 2020-2021 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import api, fields, models


class JiraAccountAnalyticLine(models.Model):
    _inherit = "jira.account.analytic.line"

    jira_servicedesk_issue_url = fields.Char(
        string="Original JIRA service desk issue Link",
        compute="_compute_jira_servicedesk_issue_url",
    )

    @api.depends("jira_issue_key")
    def _compute_jira_servicedesk_issue_url(self):
        """Compute the external URL to JIRA service desk."""
        for record in self:
            jira_project = fields.first(self.project_id.jira_bind_ids)
            if jira_project and record.jira_issue_key:
                record.jira_servicedesk_issue_url = (
                    jira_project.make_servicedesk_issue_url(  # noqa:
                        record.jira_issue_key
                    )
                )


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    jira_servicedesk_issue_url = fields.Char(
        string="Original JIRA service desk issue Link",
        compute="_compute_jira_servicedesk_issue_url",
        readonly=True,
    )

    @api.depends(
        "jira_bind_ids.jira_servicedesk_issue_url",
    )
    def _compute_jira_servicedesk_issue_url(self):
        """Compute the service desk references to JIRA.

        We assume that we have only one external record for a line
        """
        for record in self:
            if not record.jira_bind_ids:
                continue
            main_binding = record.jira_bind_ids[0]
            record.jira_servicedesk_issue_url = main_binding.jira_servicedesk_issue_url
