# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

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

import openerp
from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import ensure_db

from openerp.addons.connector.session import ConnectorSession

from ..models.account_analytic_line.importer import import_worklog
from ..unit.importer import import_record

_logger = logging.getLogger(__name__)


class JiraWebhookController(http.Controller):

    @http.route('/connector_jira/webhooks/issue',
                type='json', auth='none', csrf=False)
    def webhook_issue(self, issue_id=None, **kw):
        ensure_db()
        request.uid = openerp.SUPERUSER_ID
        env = request.env
        backend = env['jira.backend'].search(
            [('use_webhooks', '=', True)],
            limit=1
        )
        if not backend:
            _logger.warning('Received a webhook from Jira but cannot find a '
                            'Jira backend with webhooks activated')
            return

        worklog = request.jsonrequest['issue']
        issue_id = worklog['id']
        session = ConnectorSession.from_env(env)
        import_record.delay(session, 'jira.project.task', backend.id, issue_id)

    @http.route('/connector_jira/webhooks/worklog',
                type='json', auth='none', csrf=False)
    def webhook_worklog(self, **kw):
        ensure_db()
        request.uid = openerp.SUPERUSER_ID
        env = request.env
        backend = env['jira.backend'].search(
            [('use_webhooks', '=', True)],
            limit=1
        )
        if not backend:
            _logger.warning('Received a webhook from Jira but cannot find a '
                            'Jira backend with webhooks activated')
            return

        worklog = request.jsonrequest['worklog']
        issue_id = worklog['issueId']
        worklog_id = worklog['id']
        session = ConnectorSession.from_env(env)
        import_worklog.delay(session, 'jira.account.analytic.line',
                             backend.id, issue_id, worklog_id)
