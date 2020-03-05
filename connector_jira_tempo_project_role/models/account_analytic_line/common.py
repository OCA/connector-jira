# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def _get_connector_jira_fields(self):
        return super()._get_connector_jira_fields() + [
            'role_id',
        ]
