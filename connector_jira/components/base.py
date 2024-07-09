# Copyright 2018-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import AbstractComponent


class BaseJiraConnectorComponent(AbstractComponent):
    """Base Jira Connector Component

    All components of this connector should inherit from it.
    """

    _name = "jira.base"
    _inherit = "base.connector"
    _collection = "jira.backend"
