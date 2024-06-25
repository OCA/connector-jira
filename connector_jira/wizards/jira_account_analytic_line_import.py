# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class JiraAccountAnalyticLineImport(models.TransientModel):
    _name = "jira.account.analytic.line.import"
    _description = "Reimport Jira Worklogs"

    analytic_line_ids = fields.Many2many(
        "account.analytic.line",
        relation="import_wiz_2_analytic_lines",
    )
    analytic_binding_ids = fields.Many2many(
        "jira.account.analytic.line",
        relation="import_wiz_2_analytic_bindings",
    )

    def confirm(self):
        bindings = self.analytic_binding_ids | self.analytic_line_ids.jira_bind_ids
        if bindings:
            bindings.force_reimport()
