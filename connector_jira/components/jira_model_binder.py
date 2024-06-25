# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class JiraModelBinder(Component):
    """Binder for standalone models

    When we synchronize a model that has no equivalent
    in Odoo, we create a model that hold the Jira records
    without `_inherits`.

    """

    _name = "jira.model.binder"
    _inherit = ["base.binder", "jira.base"]
    _apply_on = ["jira.issue.type"]
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
