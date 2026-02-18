# Copyright 2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    jira_tempo_status = fields.Selection(
        selection=[
            ("approved", "Approved"),
            ("in_review", "In Review"),
            # no longer used on cloud version
            ("waiting_for_approval", "Waiting for approval"),
            # no longer used on cloud version
            ("ready_to_submit", "Ready to submit"),
            ("open", "Open"),
        ]
    )
