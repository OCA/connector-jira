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

import logging
from datetime import datetime, timedelta

from odoo import _

from odoo.addons.component.core import AbstractComponent
from odoo.addons.queue_job.exception import RetryableJobError

from .common import IMPORT_DELTA, JIRA_JQL_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class JiraTimestampBatchImporter(AbstractComponent):
    """Batch Importer working with a jira.backend.timestamp.record

    It locks the timestamp to ensure no other job is working on it,
    and uses the latest timestamp value as reference for the search.

    The role of a BatchImporter is to search for a list of
    items to import, then it can either import them directly or delay
    the import of each item separately.
    """

    _name = "jira.timestamp.batch.importer"
    _inherit = ["base.importer", "jira.base"]
    _usage = "timestamp.batch.importer"

    def run(self, timestamp, force=False, **kwargs):
        """Run the synchronization using the timestamp"""
        original_timestamp_value = timestamp.last_timestamp
        if not timestamp._lock():
            self._handle_lock_failed(timestamp)

        next_timestamp_value, records = self._search(timestamp)
        timestamp._update_timestamp(next_timestamp_value)
        number = self._handle_records(records, force=force)
        return _(
            f"Batch from {original_timestamp_value} UTC to {next_timestamp_value} UTC "
            f"generated {number} imports"
        )

    def _handle_records(self, records, force=False):
        """Handle the records to import and return the number handled"""
        number = 0  # Cannot use ``len(records)`` cause ``records`` is a generator
        for record_id in records:
            number += 1
            self._import_record(record_id, force=force)
        return number

    def _handle_lock_failed(self, timestamp):
        _logger.warning("Failed to acquire timestamps %s", timestamp, exc_info=True)
        raise RetryableJobError("Concurrent process already syncing", ignore_retry=True)

    def _search(self, timestamp):
        """Return a tuple (next timestamp value, jira record ids)"""
        adapter = self.backend_adapter
        since, until = timestamp.last_timestamp, datetime.now()
        since_str = since.strftime(JIRA_JQL_DATETIME_FORMAT)
        until_str = until.strftime(JIRA_JQL_DATETIME_FORMAT)
        next_timestamp_value = max(until - timedelta(seconds=IMPORT_DELTA), since)
        recs = adapter.search(f'updated >= "{since_str}" and updated <= "{until_str}"')
        return next_timestamp_value, recs

    def _import_record(self, record_id, force=False, record=None, **kwargs):
        """Delay the import of the records"""
        self.model.with_delay(**kwargs).import_record(
            self.backend_record,
            record_id,
            force=force,
            record=record,
        )
