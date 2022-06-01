# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class QueueJob(models.Model):
    _inherit = "queue.job"

    def related_action_jira_link(self):
        """Open a jira url for an issue"""
        self.ensure_one()

        model_name = self.model_name
        # only tested on issues so far
        issue_models = ("jira.project.task", "jira.account.analytic.line")
        if model_name not in issue_models:
            return

        backend = self.args[0]
        jira_id = self.args[1]

        # Get the key of the issue to generate the URI.
        # JIRA doesn't have an URI to show an issue by id.
        # And at this point, we may be importing a Jira record
        # that is not yet imported in Odoo or fails to import,
        # so we cannot use the URL computed on the Jira binding.
        with backend.work_on("jira.project.task") as work:
            adapter = work.component(usage="backend.adapter")
            with adapter.handle_user_api_errors():
                jira_record = adapter.get(jira_id)
        jira_key = jira_record.key

        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": backend.make_issue_url(jira_key),
        }
