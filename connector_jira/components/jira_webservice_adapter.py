# Copyright 2016-2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
from contextlib import contextmanager

import requests

from odoo import _, exceptions

from odoo.addons.component.core import Component
from odoo.addons.connector.exception import IDMissingInBackend

_logger = logging.getLogger(__name__)

try:
    import jira
except ImportError as err:
    _logger.debug(err)


class JiraWebserviceAdapter(Component):
    """Generic adapter for using the JIRA backend"""

    _name = "jira.webservice.adapter"
    _inherit = ["base.backend.adapter.crud", "jira.base"]
    _usage = "backend.adapter"

    def __init__(self, work_context):
        super().__init__(work_context)
        self._client = None

    @property
    def client(self):
        # lazy load the client, initialize only when actually needed
        if not self._client:
            self._client = self.backend_record.get_api_client()
        return self._client

    def _post_get_json(
        self,
        path,
        params=None,
        base=jira.client.JIRA.JIRA_BASE_URL,
    ):
        """Get the json for a given path and payload

        :param path: The subpath required
        :type path: str
        :param params: a payload for the method
        :type params: A json payload
        :param base: The Base JIRA URL, defaults to the instance base.
        :type base: Optional[str]
        :rtype: Union[Dict[str, Any], List[Dict[str, str]]]
        """
        return self.client._get_json(path=path, base=base, params=params, use_post=True)

    @contextmanager
    def handle_404(self):
        """Context manager to handle 404 errors on the API

        404 (no record found) on the API are re-raised as:
        ``odoo.addons.connector.exception.IDMissingInBackend``
        """
        try:
            yield
        except jira.exceptions.JIRAError as err:
            if err.status_code == 404:
                raise IDMissingInBackend(f"{err.text} (url: {err.url})") from err
            raise

    @contextmanager
    def handle_user_api_errors(self):
        """Contextmanager to use when the API is used user-side

        It catches the common network or Jira errors and reraise them
        to the user using the Odoo UserError.
        """
        try:
            yield
        except requests.exceptions.ConnectionError as err:
            _logger.exception("Jira ConnectionError")
            message = _("Error during connection with Jira: %s") % (err,)
            raise exceptions.UserError(message) from err
        except jira.exceptions.JIRAError as err:
            _logger.exception("Jira JIRAError")
            message = _("Jira Error: %s") % (err,)
            raise exceptions.UserError(message) from err
        except IDMissingInBackend as err:
            _logger.exception("Jira 404 for an ID")
            message = _("Record does not exist in Jira: %s") % (err,)
            raise exceptions.UserError(message) from err
