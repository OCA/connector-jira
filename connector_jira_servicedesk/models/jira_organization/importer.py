# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.connector.components.mapper import mapping

from odoo.addons.component.core import Component


class OrganizationMapper(Component):
    _name = 'jira.organization.mapper'
    _inherit = ['jira.import.mapper']
    _apply_on = 'jira.organization'

    direct = [
        ('name', 'name'),
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


class OrganizationBatchImporter(Component):
    """ Import the Jira Organizations

    For every id in in the list of organizations, a direct import is done.
    """
    _name = 'jira.organization.batch.importer'
    _inherit = 'jira.direct.batch.importer'
    _apply_on = ['jira.organization']

    def run(self):
        """ Run the synchronization """
        record_ids = self.backend_adapter.search()
        for record_id in record_ids:
            self._import_record(record_id)
