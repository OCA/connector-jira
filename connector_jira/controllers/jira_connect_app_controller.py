# Copyright 2016-2024 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""

Receive webhooks from Jira


(Outdated) JIRA could well send all the data in the webhook request's body,
which would avoid Odoo to make another GET to get this data, but
JIRA webhooks are potentially insecure as we don't know if it really
comes from JIRA. So we don't use the data sent by the webhook and the job
gets the data by itself (with the nice side-effect that the job is retryable).

TODO: we now have authenticated calls from Jira through the JWT tokens, so we
 could move back to a setup where we avoid querying the data back to Jira.
 Changing this is on the roadmap.

"""

import json
import logging

import jwt
import requests
from werkzeug.exceptions import Forbidden

import odoo
from odoo import http
from odoo.http import request

from odoo.addons.web.controllers.utils import ensure_db

_logger = logging.getLogger(__name__)


class JiraConnectAppController(http.Controller):
    """Manage the lifecyle of the App

    The app-descriptor endpoint when called returns the app descriptor,
    which lists the endpoints for installation / uninstallation /
    enabling / disabling the app on a Jira cloud server.

    The lifecycle requests all receive a payload with the following keys:

    {
        "key": "installed-addon-key",
        "clientKey": "unique-client-identifier",
        "sharedSecret": "a-secret-key-not-to-be-lost",
        "serverVersion": "server-version", # DEPRECATED
        "pluginsVersion": "version-of-connect",
        "baseUrl": "https://example.atlassian.net",
        "displayUrl": "https://issues.example.com",
        "displayUrlServicedeskHelpCenter": "https://support.example.com",
        "productType": "jira",
        "description": "Atlassian Jira at https://example.atlassian.net",
        "serviceEntitlementNumber": "SEN-number",
        "entitlementId": "Entitlement-Id",
        "entitlementNumber": "Entitlement-Number",
        "eventType": "installed",
        "installationId":
            "ari:cloud:ecosystem::installation/uuid-of-forge-installation-identifier"
    }

    Upon reception of an "installed" lifecycle call, we create a backend record
    for the app, in state "disabled".
    Upon reception of an "enabled" lifecycle call, we set the backend to "enabled".
    Upon reception of a "disabled" lifecycle call, we set the backend to "disabled".
    Upon reception of an "uninstalled" lifecycle call, we unlink the backend record.

    Documentation:
    https://developer.atlassian.com/cloud/jira/platform/connect-app-descriptor/#lifecycle
    """

    def _get_backend(self, backend_id):
        backend = request.env["jira.backend"].search([("id", "=", backend_id)])
        if not backend:
            _logger.warning("Cannot retrieve Jira backend with ID %s" % backend_id)
        return backend

    @http.route(
        "/jira/<int:backend_id>/app-descriptor.json",
        type="http",
        methods=["GET"],
        auth="public",
        csrf=False,
    )
    def app_descriptor(self, backend_id, **kwargs):
        ensure_db()
        request.update_env(user=odoo.SUPERUSER_ID)
        backend = self._get_backend(backend_id)
        data = json.dumps(backend._get_app_descriptor() if backend else {})
        headers = [("Content-Type", "application/json"), ("Content-Length", len(data))]
        return request.make_response(data, headers)

    def _validate_jwt_token(self):
        """Use authorization header to validate the request

        The process is described in
        https://developer.atlassian.com/cloud/jira/platform/security-for-connect-apps/
        """
        auth_header = request.httprequest.headers["Authorization"]
        assert auth_header.startswith("JWT "), "unexpected content in Auth header"
        jwt_token = auth_header[4:]
        headers = jwt.get_unverified_header(jwt_token)
        if "kid" not in headers:
            raise Forbidden()
        kid = headers["kid"]
        # pylint: disable=E8106
        response = requests.get(f"https://connect-install-keys.atlassian.com/{kid}")
        response.raise_for_status()
        public_key = response.text
        response.close()
        _logger.info("public key:\n%s", public_key)
        decoded = jwt.decode(
            jwt_token,
            public_key,
            algorithms=[headers["alg"]],
            audience=request.env["jira.backend"].sudo()._get_base_url(),
        )
        _logger.warning("decoded JWT Token: %s", decoded)
        return True

    @http.route(
        "/jira/<int:backend_id>/installed",
        type="json",
        methods=["POST"],
        auth="public",  # security implemented by self._validate_jwt_token()
        csrf=False,
    )
    def install_app(self, backend_id, **kwargs):
        self._validate_jwt_token()
        payload = request.get_json_data()
        _logger.info("installed: %s", payload)
        assert payload["eventType"] == "installed"
        ensure_db()
        request.update_env(user=odoo.SUPERUSER_ID)
        return {"status": self._get_backend(backend_id)._install_app(payload)}

    @http.route(
        "/jira/<int:backend_id>/uninstalled",
        type="json",
        methods=["POST"],
        auth="public",  # security implemented by self._validate_jwt_token()
        csrf=False,
    )
    def uninstall_app(self, backend_id, **kwargs):
        self._validate_jwt_token()
        payload = request.get_json_data()
        _logger.info("uninstalled: %s", payload)
        assert payload["eventType"] == "uninstalled"
        request.update_env(user=odoo.SUPERUSER_ID)
        return {"status": self._get_backend(backend_id)._uninstall_app(payload)}

    @http.route(
        "/jira/<int:backend_id>/enabled",
        type="json",
        methods=["POST"],
        auth="public",  # security implemented by backend._validate_jwt_from_request()
        csrf=False,
    )
    def enable_app(self, backend_id, **kwargs):
        payload = request.get_json_data()
        _logger.info("enabled: %s", payload)
        assert payload["eventType"] == "enabled"
        request.update_env(user=odoo.SUPERUSER_ID)
        backend = self._get_backend(backend_id)
        status = "ko"
        if backend:
            backend._validate_jwt_from_request()
            status = backend._enable_app(payload)
        return {"status": status}

    @http.route(
        "/jira/<int:backend_id>/disabled",
        type="json",
        methods=["POST"],
        auth="public",  # security implemented by backend._validate_jwt_from_request()
        csrf=False,
    )
    def disable_app(self, backend_id, **kwargs):
        payload = request.get_json_data()
        _logger.info("disabled: %s", payload)
        assert payload["eventType"] == "disabled"
        request.update_env(user=odoo.SUPERUSER_ID)
        backend = self._get_backend(backend_id)
        status = "ko"
        if backend:
            backend._validate_jwt_from_request()
            status = backend._disable_app(payload)
        return {"status": status}
