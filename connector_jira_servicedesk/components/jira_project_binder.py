# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import tools

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class JiraProjectBinder(Component):
    _inherit = "jira.project.binder"

    def to_internal(self, external_id, unwrap=False, organizations=None):
        """Give the Odoo recordset for an external ID

        When organizations are passed (ids are odoo ids), the binder
        will return:

        * a project linked with JIRA with the exact set of organizations
        * if no project has the exact same set, a project linked without
          organization set on the binding

        If no organizations are passed, only project bindings
        without organization match.

        :param external_id: external ID for which we want
                            the Odoo ID
        :param unwrap: if True, returns the normal record
                       else return the binding record
        :param organizations: jira.organization recordset
        :return: a recordset, depending on the value of unwrap,
                 or an empty recordset if the external_id is not mapped
        :rtype: recordset
        """
        domain = [
            (self._external_field, "=", tools.ustr(external_id)),
            (self._backend_field, "=", self.backend_record.id),
        ]
        if not organizations:
            domain.append(("organization_ids", "=", False))
        candidates = self.model.with_context(active_test=False).search(domain)
        if organizations:
            fallback = self.model.browse()
            for candidate in candidates:
                # No organization set on candidate: use it as fallback
                if not candidate.organization_ids:
                    fallback = candidate
                # All organizations are included in the candidate's organizations: it's
                # the binding we were looking for
                elif organizations <= candidate.organization_ids:
                    binding = candidate
                    break
            # No feasible candidate found: use fallback
            else:
                binding = fallback
        else:
            # No organization set: all candidates are feasible
            binding = candidates
        # Binding must be exactly 1
        binding = (binding and binding.ensure_one()) or self.model.browse()
        return binding[self._odoo_field] if unwrap else binding
