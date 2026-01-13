# Copyright 2016 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component

from ..fields import MilliDatetime


class JiraAnalyticLineBatchImporter(Component):
    """Import the Jira worklogs

    For every ID in the list, a delayed job is created.
    Import is executed starting from a given date.
    """

    _name = "jira.analytic.line.batch.importer"
    _inherit = "jira.timestamp.batch.importer"
    _apply_on = ["jira.account.analytic.line"]

    def _search(self, timestamp):
        unix_timestamp = MilliDatetime.to_timestamp(timestamp.last_timestamp)
        result = self.backend_adapter.updated_since(since=unix_timestamp)
        worklog_ids = self._filter_update(result.updated_worklogs)
        # We need issue_id + worklog_id for the worklog importer (the jira
        # "read" method for worklogs asks both), get it from yield_read.
        # TODO we might consider to optimize the import process here:
        #  yield_read reads worklogs data, then the individual
        #  import will do a request again (and 2 with the tempo module)
        next_timestamp = MilliDatetime.from_timestamp(result.until)
        return next_timestamp, self.backend_adapter.yield_read(worklog_ids)

    def _handle_records(self, records, force=False):
        number = 0  # Cannot use ``len(records)`` cause ``records`` is a generator
        for worklog in records:
            number += 1
            self._import_record(worklog["issueId"], worklog["id"], force=force)
        return number

    def _filter_update(self, updated_worklogs):
        """Filter only the worklogs needing an update

        The result from Jira contains the worklog id and
        the last update on Jira. So we keep only the worklog
        ids with a sync_date before the Jira last update.
        """
        if not updated_worklogs:
            return []
        self.env.cr.execute(
            """
            SELECT external_id, jira_updated_at
            FROM jira_account_analytic_line
            WHERE external_id IN %s
            """,
            (tuple(str(r.worklog_id) for r in updated_worklogs),),
        )
        bindings = dict(self.env.cr.fetchall())
        td, ft = MilliDatetime.to_datetime, MilliDatetime.from_timestamp
        worklog_ids = []
        for worklog in updated_worklogs:
            worklog_id = worklog.worklog_id
            # we store the latest "updated_at" value on the binding
            # so we can check if we already know the latest value,
            # for instance because we imported the record from a
            # webhook before, we can skip the import
            binding_updated_at = bindings.get(str(worklog_id))
            if not binding_updated_at or td(binding_updated_at) < ft(worklog.updated):
                worklog_ids.append(worklog_id)
        return worklog_ids

    def _import_record(self, issue_id, worklog_id, force=False, **kwargs):
        """Delay the import of the records"""
        self.model.with_delay(**kwargs).import_record(
            self.backend_record,
            issue_id,
            worklog_id,
            force=force,
        )
