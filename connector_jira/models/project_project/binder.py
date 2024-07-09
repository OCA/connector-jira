# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class JiraProjectBinder(Component):
    _name = "jira.project.binder"
    _inherit = "jira.binder"

    _apply_on = [
        "jira.project.project",
    ]

    def _domain_to_external(self, binding):
        return [
            (self._odoo_field, "=", binding.id),
            (self._backend_field, "=", self.backend_record.id),
            ("sync_action", "=", "export"),
        ]

    def to_external(self, binding, wrap=False):
        """Give the external ID for an Odoo binding ID

        More than one jira binding is possible on projects, but we still
        have to know to which one we have to export. Currently, we'll only
        pick the binding with Sync. Action "export". However, if later we
        add, for instance, a push of tasks, we may consider adding other
        means to get the external id.

        :param binding: Odoo binding for which we want the external id
        :param wrap: if True, binding is a normal record, the
                     method will search the corresponding binding and return
                     the external id of the binding
        :return: external ID of the record
        """
        if isinstance(binding, models.BaseModel):
            binding.ensure_one()
        else:
            binding = self.model.browse(binding)
        if wrap:
            binding = self.model.with_context(active_test=False).search(
                self._domain_to_external()
            )
            if not binding:
                return None
            binding.ensure_one()
            return binding[self._external_field]
        return binding[self._external_field]
