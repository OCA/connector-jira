# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import models
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class JiraProjectBinder(Component):
    _name = 'jira.project.binder'
    _inherit = 'jira.binder'

    _apply_on = [
        'jira.project.project',
    ]

    def to_external(self, binding, wrap=False):
        """ Give the external ID for an Odoo binding ID

        More than one jira binding is tolerated on projects, but regarding the
        exports, we flag only one of them as master for the exports. The master
        binding is either the binding with the sync action "export", or if no
        binding is using the export action, this is the one flagged
        "is_master".

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
                [(self._odoo_field, '=', binding.id),
                 (self._backend_field, '=', self.backend_record.id),
                 (self.is_master, '=', True),
                 ]
            )
            if not binding:
                return None
            binding.ensure_one()
            return binding[self._external_field]
        return binding[self._external_field]
