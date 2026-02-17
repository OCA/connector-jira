# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class JiraProjectBaseMixin(models.AbstractModel):
    _inherit = "jira.project.base.mixin"

    organization_ids = fields.Many2many(
        comodel_name="jira.organization",
        string="Organization(s) on Jira",
        domain="[('backend_id', '=', backend_id)]",
        help="If organizations are set, a task will be "
        "added to the project only if the project AND "
        "the organization match with the selection.",
    )
