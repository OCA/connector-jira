# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.connector.components.mapper import mapping
from odoo.addons.component.core import Component


class AnalyticLineMapper(Component):
    _inherit = 'jira.analytic.line.mapper'

    @mapping
    def role(self, record):
        role_attribute_key = '_%s_' % (
            self.backend_record.role_worklog_attribute_name
        )
        role_name = None
        for attribute in record['_tempo_timesheets']['worklogAttributes']:
            if attribute['key'] != role_attribute_key:
                continue
            role_name = attribute['value']
            break
        if not role_name:
            return {'role_id': False}
        role = self.env['project.role'].search(
            [('name', '=', role_name)],
            limit=1,
        )
        return {'role_id': role.id if role else False}
