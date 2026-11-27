# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class JiraOrganizationBatchImporter(Component):
    """Import the Jira Organizations

    For every id in in the list of organizations, a direct import is done.
    """

    _name = "jira.organization.batch.importer"
    _inherit = "jira.direct.batch.importer"
    _apply_on = ["jira.organization"]

    def run(self):
        """Run the synchronization"""
        for record in self.backend_adapter.search():
            self._import_record(record["id"], record=record)
