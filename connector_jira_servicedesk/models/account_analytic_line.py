# Copyright 2020-2021 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    jira_servicedesk_issue_url = fields.Char(
        string="Original JIRA service desk issue Link",
        compute="_compute_jira_servicedesk_issue_url",
    )

    @api.depends("jira_bind_ids.jira_servicedesk_issue_url")
    def _compute_jira_servicedesk_issue_url(self):
        """Compute the service desk references to JIRA.

        We assume that we have only one external record for a line
        """
        for record in self:
            bind = record.jira_bind_ids[:1]
            record.jira_servicedesk_issue_url = bind.jira_servicedesk_issue_url or ""
