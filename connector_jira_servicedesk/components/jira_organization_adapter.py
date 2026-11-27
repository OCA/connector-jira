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
        base_url = "{server}/rest/servicedeskapi/{path}"
        super().__init__("organization/{0}", options, session, base_url)
        if raw:
            self._parse_raw(raw)


class OrganizationAdapter(Component):
    _name = "jira.organization.adapter"
    _inherit = ["jira.webservice.adapter"]
    _apply_on = ["jira.organization"]

    # The Service Desk REST API returns an error if this header
    # is not used. The API may change, so they want an agreement for
    # the client about this.
    _desk_headers = CaseInsensitiveDict({"X-ExperimentalApi": "opt-in"})

    _desk_api_path_base = "{server}/rest/servicedeskapi/{path}"

    def __init__(self, work_context):
        super().__init__(work_context)
        self.client._session.headers.update(self._desk_headers)

    # pylint: disable=W8106
    def read(self, id_):
        # No ``super()``: MRO will end up calling ``base.backend.adapter.crud.read()``
        # methods that will raise a ``NotImplementedError`` exception
        organization = Organization(self.client._options, self.client._session)
        with self.handle_404():
            organization.find(id_)
        return organization.raw

    def search(self):
        # A GET on the REST API returns only one page with the
        # first 50 rows. Fetch all pages.
        orgs = []
        # 50 items per page is the maximum allowed by Jira
        start, end = 0, 50
        result = {"isLastPage": False}
        while not result["isLastPage"]:
            result = self.client._get_json(
                "organization",
                params={"start": start, "limit": end},
                base=self._desk_api_path_base,
            )
            start, end = end, end + 50
            orgs += result["values"]
        return orgs
