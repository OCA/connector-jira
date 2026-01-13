# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if


class JiraProjectProjectListener(Component):
    _name = "jira.project.project.listener"
    _inherit = ["base.connector.listener", "jira.base"]
    _apply_on = ["jira.project.project"]

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        if record.sync_action == "export":
            record.with_delay(priority=10).export_record(fields=fields)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if record.sync_action == "export":
            record.with_delay(priority=10).export_record(fields=fields)
