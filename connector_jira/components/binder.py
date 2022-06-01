# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


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
        sync_date = binding[self._sync_date_field]
        if not sync_date:
            return
        return fields.Datetime.from_string(sync_date)


class JiraModelBinder(Component):
    """Binder for standalone models

    When we synchronize a model that has no equivalent
    in Odoo, we create a model that hold the Jira records
    without `_inherits`.

    """

    _name = "jira.model.binder"
    _inherit = ["base.binder", "jira.base"]

    _apply_on = [
        "jira.issue.type",
    ]

    _odoo_field = "id"

    def to_internal(self, external_id, unwrap=False):
        if unwrap:
            _logger.warning(
                "unwrap has no effect when the "
                "binding is not an inherits "
                "(model %s)",
                self.model._name,
            )
        return super().to_internal(external_id, unwrap=False)

    def unwrap_binding(self, binding):
        if isinstance(binding, models.BaseModel):
            binding.ensure_one()
        else:
            binding = self.model.browse(binding)
        return binding

    def unwrap_model(self):
        return self.model
