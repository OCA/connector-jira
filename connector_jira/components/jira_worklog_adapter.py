# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from collections import namedtuple

from odoo.addons.component.core import Component

UpdatedWorklog = namedtuple(
    "UpdatedWorklog",
    # id as integer, timestamp
    "worklog_id updated",
)

UpdatedWorklogSince = namedtuple(
    "UpdatedWorklogSince",
    # timestamp, timestamp, list[UpdatedWorklog]
    "since until updated_worklogs",
)


DeletedWorklogSince = namedtuple(
    "DeletedWorklogSince",
    # timestamp, timestamp, list[ids as integer]
    "since until deleted_worklog_ids",
)


class WorklogAdapter(Component):
    _name = "jira.worklog.adapter"
    _inherit = "jira.webservice.adapter"
    _apply_on = ["jira.account.analytic.line"]

    # pylint: disable=W8106
    def read(self, issue_id, worklog_id):
        # No ``super()``: MRO will end up calling ``base.backend.adapter.crud.read()``
        # methods that will raise a ``NotImplementedError`` exception
        with self.handle_404():
            return self.client.worklog(issue_id, worklog_id).raw

    def search(self, issue_id):
        """Search worklogs of an issue"""
        return [worklog.id for worklog in self.client.worklogs(issue_id)]

    @staticmethod
    def _chunks(whole, size):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(whole), size):
            yield whole[i : i + size]

    def yield_read(self, worklog_ids):
        """Generator returning worklog ids data"""
        # the method returns max 1000 results
        for chunk in self._chunks(worklog_ids, 1000):
            yield from self._post_get_json("worklog/list", params={"ids": chunk})

    def updated_since(self, since=None):
        original_since, until = since, since
        updated_worklogs = []
        result = {"lastPage": False}
        while not result["lastPage"]:
            result = self.client._get_json("worklog/updated", params={"since": since})
            updated_worklogs += [
                UpdatedWorklog(worklog_id=row["worklogId"], updated=row["updatedTime"])
                for row in result["values"]
            ]
            until = since = result["until"]
        return UpdatedWorklogSince(
            since=original_since, until=until, updated_worklogs=updated_worklogs
        )

    def deleted_since(self, since=None):
        original_since, until = since, since
        deleted_worklog_ids = []
        result = {"lastPage": False}
        while not result["lastPage"]:
            result = self.client._get_json("worklog/deleted", params={"since": since})
            deleted_worklog_ids += [row["worklogId"] for row in result["values"]]
            until = since = result["until"]
        return DeletedWorklogSince(
            since=original_since, until=until, deleted_worklog_ids=deleted_worklog_ids
        )
