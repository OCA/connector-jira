# Copyright 2021 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class JiraProjectTaskStage(models.Model):
    _inherit = "project.task.type"

    jira_unbind = fields.Boolean(
        string="Jira Unbind",
        help="Cut the link between JIRA and the task when project reached this stage.",
    )
