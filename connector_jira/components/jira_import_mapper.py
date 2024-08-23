# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import AbstractComponent
from odoo.addons.connector.components.mapper import mapping


class JiraImportMapper(AbstractComponent):
    """Base Import Mapper for Jira"""

    _name = "jira.import.mapper"
    _inherit = ["base.import.mapper", "jira.base"]

    @mapping
    def jira_updated_at(self, record):
        if self.options.external_updated_at:
            return {"jira_updated_at": self.options.external_updated_at}
