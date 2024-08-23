# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class JiraProjectProjectExporter(Component):
    _name = "jira.project.project.exporter"
    _inherit = ["jira.exporter"]
    _apply_on = ["jira.project.project"]

    def _create_project(self, adapter, key, name, template, values):
        return adapter.create(
            key=key,
            name=name,
            template_name=template,
            values=values,
        )["projectId"]

    def _create_shared_project(self, adapter, key, name, shared_key, lead):
        return adapter.create_shared(
            key=key,
            name=name,
            shared_key=shared_key,
            lead=lead,
        )["projectId"]

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
                self.external_id = self._create_shared_project(
                    adapter, key, name, self.binding.project_template_shared, lead=None
                )
            else:
                self.external_id = self._create_project(
                    adapter, key, name, template, {}
                )
