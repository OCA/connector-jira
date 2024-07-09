# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class IssueTypeMapper(Component):
    _name = "jira.issue.type.mapper"
    _inherit = ["jira.import.mapper"]
    _apply_on = "jira.issue.type"

    direct = [
        ("name", "name"),
        ("description", "description"),
    ]

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}


class IssueTypeBatchImporter(Component):
    """Import the Jira Issue Types

    For every id in in the list of issue types, a direct import is done.
    Import from a date
    """

    _name = "jira.issue.type.batch.importer"
    _inherit = "jira.direct.batch.importer"
    _apply_on = ["jira.issue.type"]

    def run(self):
        """Run the synchronization"""
        record_ids = self.backend_adapter.search()
        for record_id in record_ids:
            self._import_record(record_id)
