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

import logging
import pprint

import odoo
from odoo import _, http
from odoo.http import request

from odoo.addons.web.controllers.utils import ensure_db

_logger = logging.getLogger(__name__)


class JiraWebhookController(http.Controller):
    def _get_backend(self, backend_id):
        backend = request.env["jira.backend"].search(
            [("id", "=", backend_id), ("state", "=", "running")]
        )
        if not backend:
            _logger.warning(
                "Cannot retrieve running Jira backend with ID %s" % backend_id
            )
        return backend

    @http.route(
        "/connector_jira/<int:backend_id>/webhooks/issue",
        type="json",
        auth="none",  # security implemented by backend._validate_jwt_from_request()
        csrf=False,
    )
    def webhook_issue(self, backend_id, issue_id=None, **kw):
        ensure_db()
        data = request.get_json_data()
        pprint.pprint(data)
        request.update_env(user=odoo.SUPERUSER_ID)
        backend = self._get_backend(backend_id)
        if not backend:
            return
        backend._validate_jwt_from_request()
        model = request.env["jira.project.task"]
        args = (backend, data["issue"]["id"])
        if data["webhookEvent"] == "jira:issue_deleted":
            delay_msg = _("Delete a local issue which has been deleted on JIRA")
            method = "delete_record"
        else:
            delay_msg = _("Import a issue from JIRA")
            method = "import_record"
        getattr(model.with_delay(description=delay_msg), method)(*args)

    @http.route(
        "/connector_jira/<int:backend_id>/webhooks/worklog",
        type="json",
        auth="none",  # security implemented by backend._validate_jwt_from_request()
        csrf=False,
    )
    def webhook_worklog(self, backend_id, **kw):
        ensure_db()
        data = request.get_json_data()
        pprint.pprint(data)
        request.update_env(user=odoo.SUPERUSER_ID)
        backend = self._get_backend(backend_id)
        if not backend:
            return
        backend._validate_jwt_from_request()
        model = request.env["jira.account.analytic.line"]
        if data["webhookEvent"] == "worklog_deleted":
            delay_msg = _("Delete a local worklog which has been deleted on JIRA")
            method = "delete_record"
            args = (backend, data["worklog"]["id"])
        else:
            delay_msg = _("Import a worklog from JIRA")
            method = "import_record"
            args = (backend, data["worklog"]["issueId"], data["worklog"]["id"])
        getattr(model.with_delay(description=delay_msg), method)(*args)
