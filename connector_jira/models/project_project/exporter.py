# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if


class JiraProjectProjectListener(Component):
    _name = "jira.project.project.listener"
    _inherit = ["base.connector.listener"]
    _apply_on = ["jira.project.project"]

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        if record.sync_action == "export":
            record.with_delay(priority=10).export_record(fields=fields)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if record.sync_action == "export":
            record.with_delay(priority=10).export_record(fields=fields)


class ProjectProjectListener(Component):
    _name = "project.project.listener"
    _inherit = ["base.connector.listener"]
    _apply_on = ["project.project"]

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if fields == ["jira_bind_ids"] or fields == ["message_follower_ids"]:
            # When vals is esb_bind_ids:
            # Binding edited from the record's view. When only this field has
            # been modified, an other job has already been delayed for the
            # binding record so can exit this event early.

            # When vals is message_follower_ids:
            # MailThread.message_subscribe() has been called, this
            # method does a write on the field message_follower_ids,
            # we never want to export that.
            return
        for binding in record.jira_bind_ids:
            if binding.sync_action == "export":
                binding.with_delay(priority=10).export_record(fields=fields)


class JiraProjectProjectExporter(Component):
    _name = "jira.project.project.exporter"
    _inherit = ["jira.exporter"]
    _apply_on = ["jira.project.project"]

    def _create_project(self, adapter, key, name, template, values):
        project = adapter.create(
            key=key,
            name=name,
            template_name=template,
            values=values,
        )
        return project["projectId"]

    def _create_shared_project(self, adapter, key, name, shared_key, lead):
        project = adapter.create_shared(
            key=key,
            name=name,
            shared_key=shared_key,
            lead=lead,
        )
        return project["projectId"]

    def _update_project(self, adapter, values):
        adapter.write(self.external_id, values)

    def _run(self, fields=None):
        adapter = self.component(usage="backend.adapter")

        key = self.binding.jira_key
        name = self.binding.name[:80]
        template = self.binding.project_template
        # TODO: add lead

        if self.external_id:
            self._update_project(adapter, {"name": name, "key": key})
        else:
            if template == "shared":
                shared_key = self.binding.project_template_shared
                self.external_id = self._create_shared_project(
                    adapter, key, name, shared_key, None
                )
            else:
                self.external_id = self._create_project(
                    adapter, key, name, template, {}
                )
