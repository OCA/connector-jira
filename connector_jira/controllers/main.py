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
from odoo import _, http
from odoo.http import request

from odoo.addons.web.controllers.main import ensure_db

_logger = logging.getLogger(__name__)


class JiraWebhookController(http.Controller):
    @http.route(
        "/connector_jira/<int:backend_id>/webhooks/issue",
        type="json",
        auth="none",  # security handled with manual JWT check (backend._validate_jwt)
        csrf=False,
    )
    def webhook_issue(self, backend_id, issue_id=None, **kw):
        ensure_db()
        import pprint

        pprint.pprint(request.jsonrequest)
        request.uid = odoo.SUPERUSER_ID
        env = request.env
        backend = env["jira.backend"].search(
            [("id", "=", backend_id), ("state", "=", "running")]
        )
        if not backend:
            _logger.warning(
                "Received an Issue webhook from Jira for backend %d but cannot find a "
                "matching running backend",
                backend_id,
            )
            return
        backend._validate_jwt(
            request.httprequest.headers["Authorization"],
            f"{request.httprequest.path}?{request.httprequest.query_string}",
        )
        action = request.jsonrequest["webhookEvent"]

        payload = request.jsonrequest["issue"]
        issue_id = payload["id"]

        delayable_model = env["jira.project.task"].with_delay()
        if action == "jira:issue_deleted":
            delayable_model.delete_record(backend, issue_id)
        else:
            delayable_model.import_record(backend, issue_id)

    @http.route(
        "/connector_jira/<int:backend_id>/webhooks/worklog",
        type="json",
        auth="none",  # security handled with manual JWT check (backend._validate_jwt)
        csrf=False,
    )
    def webhook_worklog(self, backend_id, **kw):
        ensure_db()
        request.uid = odoo.SUPERUSER_ID
        env = request.env
        backend = env["jira.backend"].search(
            [("id", "=", backend_id), ("state", "=", "running")]
        )
        if not backend:
            _logger.warning(
                "Received a Worklog webhook from Jira for backend %d but cannot find a "
                "matching runnign backend",
                backend_id,
            )
            return
        backend._validate_jwt(
            request.httprequest.headers["Authorization"],
            f"{request.httprequest.path}?{request.httprequest.query_string}",
        )
        action = request.jsonrequest["webhookEvent"]

        payload = request.jsonrequest["worklog"]

        issue_id = payload["issueId"]
        worklog_id = payload["id"]

        if action == "worklog_deleted":
            env["jira.account.analytic.line"].with_delay(
                description=_("Delete a local worklog which has been deleted on JIRA")
            ).delete_record(backend, worklog_id)
        else:
            env["jira.account.analytic.line"].with_delay(
                description=_("Import a worklog from JIRA")
            ).import_record(backend, issue_id, worklog_id, payload=payload)


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
    Upon reception of a "uninstalled" lifecycle call, we unlink the backend record.

    Documentation:
    https://developer.atlassian.com/cloud/jira/platform/connect-app-descriptor/#lifecycle
    """

    @http.route(
        "/jira/<int:backend_id>/app-descriptor.json",
        type="http",
        methods=["GET"],
        auth="public",
        csrf=False,
    )
    def app_descriptor(self, backend_id, **kwargs):
        ensure_db()
        request.uid = odoo.SUPERUSER_ID
        env = request.env
        backend = env["jira.backend"].search([("id", "=", backend_id)])
        if not backend:
            descriptor = {}
        else:
            descriptor = backend._get_app_descriptor()
        mime = "application/json"

        body = json.dumps(descriptor)
        return request.make_response(
            body, [("Content-Type", mime), ("Content-Length", len(body))]
        )

    def _validate_jwt_token(self):
        """use autorization header to validate the request
        The process is described in
        https://developer.atlassian.com/cloud/jira/platform/security-for-connect-apps/
        """
        authorization_header = request.httprequest.headers["Authorization"]
        assert authorization_header.startswith(
            "JWT "
        ), "unexpected content in Authorization header"
        jwt_token = authorization_header[4:]
        decoded = jwt.get_unverified_header(jwt_token)
        if "kid" in decoded:
            response = requests.get(
                f"https://connect-install-keys.atlassian.com/{decoded['kid']}"
            )
            response.raise_for_status()
            public_key = response.text
            response.close()
            _logger.info("public key:\n%s", public_key)
            decoded = jwt.decode(
                jwt_token,
                public_key,
                algorithms=[decoded["alg"]],
                audience=request.env["jira.backend"].sudo()._get_base_url(),
            )
            _logger.warning("decoded JWT Token: %s", decoded)
        else:
            raise Forbidden()
        return True

    @http.route(
        "/jira/<int:backend_id>/installed",
        type="json",
        methods=["POST"],
        auth="public",  # security implemented by _validated_jwt_token
        csrf=False,
    )
    def install_app(self, backend_id, **kwargs):
        self._validate_jwt_token()
        payload = request.jsonrequest
        _logger.info("installed: %s", payload)

        assert payload["eventType"] == "installed"
        ensure_db()
        env = request.env
        backend = env["jira.backend"].sudo().browse(backend_id)
        response = backend._install_app(payload)
        return {"status": response}

    @http.route(
        "/jira/<int:backend_id>/uninstalled",
        type="json",
        methods=["POST"],
        auth="public",  # security implemented by _validated_jwt_token
        csrf=False,
    )
    def uninstall_app(self, backend_id, **kwargs):
        self._validate_jwt_token()
        payload = request.jsonrequest
        _logger.info("uninstalled: %s", payload)
        assert payload["eventType"] == "uninstalled"
        env = request.env
        backend = env["jira.backend"].sudo().browse(backend_id)
        response = backend._uninstall_app(payload)
        return {"status": response}

    @http.route(
        "/jira/<int:backend_id>/enabled",
        type="json",
        methods=["POST"],
        auth="public",  # security handled with manual JWT check (backend._validate_jwt)
        csrf=False,
    )
    def enable_app(self, backend_id, **kwargs):
        # self._validate_jwt_token()
        payload = request.jsonrequest
        _logger.info("enabled: %s", payload)
        assert payload["eventType"] == "enabled"
        env = request.env
        backend = env["jira.backend"].sudo()
        backend = env["jira.backend"].sudo().browse(backend_id)
        backend._validate_jwt(
            request.httprequest.headers["Authorization"],
            f"{request.httprequest.path}?{request.httprequest.query_string}",
        )
        response = backend._enable_app(payload)
        return {"status": response}

    @http.route(
        "/jira/<int:backend_id>/disabled",
        type="json",
        methods=["POST"],
        auth="public",  # security handled with manual JWT check (backend._validate_jwt)
        csrf=False,
    )
    def disable_app(self, backend_id, **kwargs):
        # self._validate_jwt_token()
        payload = request.jsonrequest
        _logger.info("disabled: %s", payload)
        assert payload["eventType"] == "disabled"
        env = request.env
        backend = env["jira.backend"].sudo()
        backend = env["jira.backend"].sudo().browse(backend_id)
        backend._validate_jwt(
            request.httprequest.headers["Authorization"],
            f"{request.httprequest.path}?{request.httprequest.query_string}",
        )
        response = backend._disable_app(payload)
        return {"status": response}
