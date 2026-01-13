# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields

from odoo.addons.component.core import Component


class JiraBinder(Component):
    """Binder for Odoo models

    Where we create an additional model holding the external id.
    The advantages to have a second models are:
    * we can link more than 1 JIRA instance to the same record
    * we can work with, lock, edit the jira binding without touching the
      normal record

    Default binder when no specific binder is defined for a model.
    """

    _name = "jira.binder"
    _inherit = ["base.binder", "jira.base"]

    def sync_date(self, binding):
        assert self._sync_date_field
        return fields.Datetime.to_datetime(binding[self._sync_date_field])
