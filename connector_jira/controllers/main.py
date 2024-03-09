# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""

Receive webhooks from Jira

Webhooks to create in Jira:

1. Odoo Issues
   URL: http://odoo:8069/connector_jira/webhooks/issue/${issue.id}
   Events: Issue{created, updated, deleted}
   Exclude body: yes

1. Odoo Worklogs
   URL: http://odoo:8069/connector_jira/webhooks/worklog
   Events: Issue{created, updated, deleted}
   Exclude body: no


JIRA could well send all the data in the webhook request's body,
which would avoid Odoo to make another GET to get this data, but
JIRA webhooks are potentially insecure as we don't know if it really
comes from JIRA. So we don't use the data sent by the webhook and the job
gets the data by itself (with the nice side-effect that the job is retryable).

"""

import logging
import json

import jwt

import odoo
from odoo import _, http
from odoo.http import request

from odoo.addons.web.controllers.main import ensure_db

_logger = logging.getLogger(__name__)


class JiraWebhookController(http.Controller):
    @http.route("/connector_jira/webhooks/issue", type="json", auth="none", csrf=False)
    def webhook_issue(self, issue_id=None, **kw):
        ensure_db()
        import pprint

        pprint.pprint(request.jsonrequest)
        request.uid = odoo.SUPERUSER_ID
        env = request.env
        backend = env["jira.backend"].search(
            [
                # ("use_webhooks", "=", True)
            ],
            limit=1,
        )
        if not backend:
            _logger.warning(
                "Received a webhook from Jira but cannot find a "
                "Jira backend with webhooks activated"
            )
            return

        action = request.jsonrequest["webhookEvent"]

        worklog = request.jsonrequest["issue"]
        issue_id = worklog["id"]

        delayable_model = env["jira.project.task"].with_delay()
        if action == "jira:issue_deleted":
            delayable_model.delete_record(backend, issue_id)
        else:
            delayable_model.import_record(backend, issue_id)

    @http.route(
        "/connector_jira/webhooks/worklog", type="json", auth="none", csrf=False
    )
    def webhook_worklog(self, **kw):
        ensure_db()
        request.uid = odoo.SUPERUSER_ID
        env = request.env
        backend = env["jira.backend"].search(
            [
                # ("use_webhooks", "=", True)
            ],
            limit=1,
        )
        if not backend:
            _logger.warning(
                "Received a webhook from Jira but cannot find a "
                "Jira backend with webhooks activated"
            )
            return

        action = request.jsonrequest["webhookEvent"]

        worklog = request.jsonrequest["worklog"]
        issue_id = worklog["issueId"]
        worklog_id = worklog["id"]

        if action == "worklog_deleted":
            env["jira.account.analytic.line"].with_delay(
                description=_(
                    "Delete a local worklog which has " "been deleted on JIRA"
                )
            ).delete_record(backend, worklog_id)
        else:
            env["jira.account.analytic.line"].with_delay(
                description=_("Import a worklog from JIRA")
            ).import_record(backend, issue_id, worklog_id)


class JiraConnectAppController(http.Controller):
    """Manage the lifecyle of the App

    The app-descriptor endpoint when called returns the app descriptor, which lists the endpoints for installation / uninstallation / enabling / disabling the app on a Jira cloud server.

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
        "installationId": "ari:cloud:ecosystem::installation/uuid-of-forge-installation-identifier"
    }

    Upon reception of an "installed" lifecycle call, we create a backend record for the app, in state "disabled".
    Upon reception of an "enabled" lifecycle call, we set the backend to "enabled".
    Upon reception of a "disabled" lifecycle call, we set the backend to "disabled".
    Upon reception of a "uninstalled" lifecycle call, we unlink the backend record.

    Documentation: https://developer.atlassian.com/cloud/jira/platform/connect-app-descriptor/#lifecycle
    """

    @http.route(
        "/jira/app-descriptor.json",
        type="http",
        methods=["GET"],
        auth="public",
        csrf=False,
    )
    def app_descriptor(self, **kwargs):
        ensure_db()
        request.uid = odoo.SUPERUSER_ID
        env = request.env

        backend = env["jira.backend"]  # .search([("use_webhooks", "=", True)], limit=1)
        descriptor = backend._get_app_descriptor()
        mime = "application/json"

        body = json.dumps(descriptor)
        print(body)
        return request.make_response(
            body, [("Content-Type", mime), ("Content-Length", len(body))]
        )

    @http.route(
        "/jira/installed", type="json", methods=["POST"], auth="public", csrf=False
    )  # FIXME: auth management
    def install_app(self, **kwargs):
        payload = request.jsonrequest
        # TODO use autorization header to validate the request
        # See https://developer.atlassian.com/cloud/jira/platform/security-for-connect-apps/#validating-installation-lifecycle-requests
        authorization_header = request.httprequest.headers["Authorization"]
        assert authorization_header.startswith("JWT ")
        jwt_token = authorization_header[4:]
        decoded = jwt.get_unverified_header(jwt_token)
        # GET https://connect-install-keys.atlassian.com/{decoded['kid']} -> public key
        # decoded = jwt.decode(jwt_token, public_key, algorithms=[decoded['alg']])

        _logger.info("installed: %s", payload)

        assert payload["eventType"] == "installed"
        ensure_db()
        env = request.env
        backend = env["jira.backend"].sudo()
        backend._install_app(payload)
        return {"status": "OK"}

    @http.route(
        "/jira/uninstalled", type="json", methods=["POST"], auth="public", csrf=False
    )  # FIXME: auth management
    def uninstall_app(self, **kwargs):
        payload = request.jsonrequest
        _logger.info("uninstalled: %s", payload)
        assert payload["eventType"] == "uninstalled"
        env = request.env
        backend = env["jira.backend"].sudo()
        response = backend._uninstall_app(payload)
        return {"status": response}

    @http.route(
        "/jira/enabled", type="json", methods=["POST"], auth="public", csrf=False
    )
    def enable_app(self, payload=None, **kwargs):
        payload = request.jsonrequest
        _logger.info("enabled: %s", payload)
        assert payload["eventType"] == "enabled"
        env = request.env
        backend = env["jira.backend"].sudo()
        response = backend._enable_app(payload)
        return {"status": response}

    @http.route(
        "/jira/disabled", type="json", methods=["POST"], auth="public", csrf=False
    )
    def disable_app(self, payload=None, **kwargs):
        payload = request.jsonrequest
        _logger.info("disabled: %s", payload)
        assert payload["eventType"] == "disabled"
        env = request.env
        backend = env["jira.backend"].sudo()
        response = backend._disable_app(payload)
        return {"status": response}
