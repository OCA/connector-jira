# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class JiraIssueTypeBatchImporter(Component):
    """Import the Jira Issue Types

    For every id in in the list of issue types, a direct import is done.
    Import from a date
    """

    _name = "jira.issue.type.batch.importer"
    _inherit = "jira.direct.batch.importer"
    _apply_on = ["jira.issue.type"]

    def run(self):
        """Run the synchronization"""
        for record_id in self.backend_adapter.search():
            self._import_record(record_id)
