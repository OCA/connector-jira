# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""

Importers for Jira.

An import can be skipped if the last sync date is more recent than
the last update in Jira.

They should call the ``bind`` method if the binder even if the records
are already bound, to update the last sync date.

"""

from odoo.addons.component.core import AbstractComponent


class JiraBatchImporter(AbstractComponent):
    """The role of a BatchImporter is to search for a list of
    items to import, then it can either import them directly or delay
    the import of each item separately.
    """

    _name = "jira.batch.importer"
    _inherit = ["base.importer", "jira.base"]
    _usage = "batch.importer"

    def run(self):
        """Run the synchronization, search all JIRA records"""
        for record_id in self._search():
            self._import_record(record_id)

    def _search(self):
        return self.backend_adapter.search()

    def _import_record(self, record_id, **kwargs):
        """Import a record directly or delay the import of the record.

        Method to implement in sub-classes.
        """
        raise NotImplementedError
