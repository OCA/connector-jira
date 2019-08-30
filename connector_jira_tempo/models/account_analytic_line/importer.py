# Copyright 2018 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.connector.components.mapper import mapping
from odoo.addons.component.core import Component


class AnalyticLineMapper(Component):
    _inherit = 'jira.analytic.line.mapper'

    @mapping
    def tempo_timesheets_approval(self, record):
        approval = record['_tempo_timesheets_approval']
        values = {
            'jira_tempo_status': approval['status'],
        }
        return values
