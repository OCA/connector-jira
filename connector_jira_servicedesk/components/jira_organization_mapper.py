# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping


class OrganizationMapper(Component):
    _name = "jira.organization.mapper"
    _inherit = ["jira.import.mapper"]
    _apply_on = "jira.organization"

    direct = [("name", "name")]

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}
