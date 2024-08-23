# Copyright: 2015 LasLabs, Inc.
# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class JiraBackendAdapter(Component):
    _name = "jira.backend.adapter"
    _inherit = "jira.webservice.adapter"
    _apply_on = ["jira.backend"]

    webhook_base_path = "{server}/rest/webhooks/1.0/{path}"

    def list_fields(self):
        return self.client._get_json("field")
