# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if


class ProjectProjectListener(Component):
    _name = "project.project.listener"
    _inherit = ["base.connector.listener", "jira.base"]
    _apply_on = ["project.project"]

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        # Remove ``jira_bind_ids`` and ``message_follower_ids`` from the fields:
        # - ``jira_bind_ids``: when this field has been modified, an export is triggered
        #   by ``jira.project.project.listener`` after the field's values have been
        #   written to the proper ``jira.project.project`` records, so we ignore this
        #   field to avoid duplicated exports
        # - ``message_follower_ids``: when ``mail.thread.message_subscribe()`` has been
        #   called, it does a ``write()`` on field ``message_follower_ids``, but we
        #   never want to export that
        fields = set(fields or [])
        fields.difference_update({"jira_bind_ids", "message_follower_ids"})
        # After cleaning the fields, if we still have some fields to export, do it
        if fields:
            fields = list(fields)
            for binding in record.jira_bind_ids:
                if binding.sync_action == "export":
                    binding.with_delay(priority=10).export_record(fields=fields)
