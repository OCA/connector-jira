# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class JiraBackend(models.Model):
    _inherit = 'jira.backend'

    role_worklog_attribute_name = fields.Char(
        string='Role Worklog Attribute',
        default='Role',
        help="""
            Name of Worklog Attribute configured as Dynamic Dropdown to store
            selected Role according to Assignments.
        """,
    )
