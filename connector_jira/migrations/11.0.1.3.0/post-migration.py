# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {'active_test': False})
    task_bindings = env['jira.project.task'].search([
        ('jira_project_bind_id', '=', False)
    ])
    for binding in task_bindings:
        project = binding.odoo_id.project_id
        project_bindings = project.jira_bind_ids
        if not project_bindings:
            continue
        # If we had several projects (one software + one service desk were
        # allowed), we don't know which one the task belongs to. Try to guess
        # from the issue key or take the first one in despair.
        if not binding.jira_key:
            binding.jira_project_bind_id = project_bindings[0]
            continue
        # A Jira key is XYZ-n where XYZ is the key of the project and n the
        # sequence.
        key = binding.jira_key.split('-')[0]
        same_key_binding = project_bindings.filtered(
            lambda r: r.jira_key == key
        )
        if len(same_key_binding) == 1:
            binding.jira_project_bind_id = same_key_binding
        else:
            binding.jira_project_bind_id = project_bindings[0]
