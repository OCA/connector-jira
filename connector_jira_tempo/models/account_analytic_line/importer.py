# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.connector.components.mapper import mapping
from odoo.addons.component.core import Component


class AnalyticLineMapper(Component):
    _inherit = 'jira.analytic.line.mapper'

    @mapping
    def tempo(self, record):
        values = {
            'jira_tempo_status': record['_timesheet']['status'],
        }
        return values
