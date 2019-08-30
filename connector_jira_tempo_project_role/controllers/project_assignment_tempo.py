# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json

from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.addons.web.controllers.main import ensure_db


class ProjectAssignmentTempo(http.Controller):
    @http.route(
        '/connector_jira/assignments',
        auth='none',
        type='http',
        methods=['GET'],
    )
    def get_assignments(self, **kwargs):
        ensure_db()
        request.uid = SUPERUSER_ID
        JiraProjectTask = request.env['jira.project.task']
        JiraResUsers = request.env['jira.res.users']
        ProjectRole = request.env['project.role']

        issue = kwargs.get('issue')
        author = kwargs.get('author')
        callback = kwargs.get('callback')
        if not issue or not author or not callback:
            return request.not_found()

        jira_task = JiraProjectTask.search([('jira_key', '=', issue)])
        if not jira_task or len(jira_task) > 1:
            return request.not_found()

        jira_user = JiraResUsers.search([('external_id', '=', author)])
        if not jira_user or len(jira_user) > 1:
            return request.not_found()

        roles = ProjectRole.get_available_roles(
            jira_user.odoo_id,
            jira_task.odoo_id.project_id,
        )

        values = []
        for role in roles:
            values.append({
                'key': role.name,
                'value': role.name,
            })
        return request.make_response(
            "%s(%s)" % (callback, json.dumps({'values': values})),
            headers=[('Content-Type', 'application/javascript')],
        )
