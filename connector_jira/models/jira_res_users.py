# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class JiraResUsers(models.Model):
    _name = "jira.res.users"
    _inherit = "jira.binding"
    _inherits = {"res.users": "odoo_id"}
    _description = "Jira User"

    odoo_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        index=True,
        ondelete="restrict",
    )
