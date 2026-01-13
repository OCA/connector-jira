# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _

from odoo.addons.component.core import Component


class JiraDeleter(Component):
    _name = "jira.deleter"
    _inherit = ["base.deleter", "jira.base"]
    _usage = "record.deleter"

    def run(self, external_id, only_binding=False, set_inactive=False):
        binding = self.binder.to_internal(external_id)
        if not binding.exists():
            return _("Binding not found")
        if set_inactive and binding._active_name:  # Cannot archive it
            binding.action_archive()
            return _("Binding deactivated")
        else:
            record = binding.odoo_id
            # emptying the external_id allows to unlink the binding
            binding.external_id = False
            binding.unlink()
            if not only_binding:
                record.unlink()
            return _("Record deleted")
