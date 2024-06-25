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


class JiraDelayedBatchImporter(AbstractComponent):
    """Delay import of the records"""

    _name = "jira.delayed.batch.importer"
    _inherit = ["jira.batch.importer"]

    def _import_record(self, record_id, force=False, record=None, **kwargs):
        """Delay the import of the records"""
        self.model.with_delay(**kwargs).import_record(
            self.backend_record, record_id, force=force, record=record
        )
