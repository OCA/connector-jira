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

import odoo
from odoo import _, http
from odoo.http import request

from odoo.addons.web.controllers.main import ensure_db

_logger = logging.getLogger(__name__)


class JiraWebhookController(http.Controller):
    @http.route("/connector_jira/webhooks/issue", type="json", auth="none", csrf=False)
    def webhook_issue(self, issue_id=None, **kw):
        ensure_db()
        request.uid = odoo.SUPERUSER_ID
        env = request.env
        backend = env["jira.backend"].search([("use_webhooks", "=", True)], limit=1)
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
        backend = env["jira.backend"].search([("use_webhooks", "=", True)], limit=1)
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
