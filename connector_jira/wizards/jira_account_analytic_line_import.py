# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class JiraAccountAnalyticLineImport(models.TransientModel):
    _name = "jira.account.analytic.line.import"
    _description = "Reimport Jira Worklogs"

    def confirm(self):
        self.ensure_one()
        model_name = self.env.context.get("active_model")
        record_ids = self.env.context.get("active_ids", [])
        if model_name == "account.analytic.line":
            lines = self.env["account.analytic.line"].browse(record_ids)
            bindings = lines.mapped("jira_bind_ids")
        elif model_name == "jira.account.analytic.line":
            bindings = self.env["jira.account.analytic.line"].browse(record_ids)
        else:
            return

        bindings.force_reimport()
