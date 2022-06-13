# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from requests.structures import CaseInsensitiveDict

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)

try:
    from jira.resources import Resource
except ImportError as err:
    _logger.debug(err)
    Resource = object


class Organization(Resource):
    """A Service Desk Organization."""

    def __init__(self, options, session, raw=None):
        super().__init__(
            "organization/{0}", options, session, "{server}/rest/servicedeskapi/{path}"
        )
        if raw:
            self._parse_raw(raw)


class OrganizationAdapter(Component):
    _name = "jira.organization.adapter"
    _inherit = ["jira.webservice.adapter"]
    _apply_on = ["jira.organization"]

    # The Service Desk REST API returns an error if this header
    # is not used. The API may change so they want an agreement for
    # the client about this.
    _desk_headers = CaseInsensitiveDict({"X-ExperimentalApi": "opt-in"})

    _desk_api_path_base = "{server}/rest/servicedeskapi/{path}"

    def __init__(self, work_context):
        super().__init__(work_context)
        self.client._session.headers.update(self._desk_headers)

    def read(self, id_):
        # pylint: disable=method-required-super
        organization = Organization(self.client._options, self.client._session)
        with self.handle_404():
            organization.find(id_)
        return organization.raw

    def search(self):
        # A GET on the REST API returns only one page with the
        # first 50 rows. Fetch all pages.
        orgs = []
        start = 0
        while True:
            result = self.client._get_json(
                "organization",
                params={
                    "start": start,
                    # 50 items per page is the maximum allowed by Jira
                    "limit": start + 50,
                },
                base=self._desk_api_path_base,
            )
            start += 50
            orgs += result["values"]
            if result["isLastPage"]:
                break

        return orgs
