# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class JiraIssueTypeMapper(Component):
    _name = "jira.issue.type.mapper"
    _inherit = ["jira.import.mapper"]
    _apply_on = "jira.issue.type"

    direct = [("name", "name"), ("description", "description")]

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}
