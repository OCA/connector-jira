# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.connector.event import (on_record_create,
                                         on_record_write,
                                         )
from ... import common
from ...backend import jira
from ...unit.exporter import JiraBaseExporter
from ...unit.backend_adapter import JiraAdapter


@on_record_create(model_names='jira.project.project')
@on_record_write(model_names='jira.project.project')
def delay_export(env, model_name, record_id, vals):
    common.delay_export(env, model_name, record_id, vals, priority=10)


@on_record_write(model_names='project.project')
def delay_export_all_bindings(env, model_name, record_id, vals):
    if list(vals.keys()) == ['jira_bind_ids']:
        # Binding edited from the project's view.
        # When only this field has been modified, an other job has
        # been delayed for the jira.product.product record.
        return
    common.delay_export_all_bindings(env, model_name, record_id, vals)


@jira
class JiraProjectProjectExporter(JiraBaseExporter):
    _model_name = ['jira.project.project']

    def _create_project(self, adapter, key, name, template, values):
        project = adapter.create(
            key=key,
            name=name,
            template_name=template,
            values=values,
        )
        return project['projectId']

    def _create_shared_project(self, adapter, key, name, shared_key, lead):
        project = adapter.create_shared(
            key=key,
            name=name,
            shared_key=shared_key,
            lead=lead,
        )
        return project['projectId']

    def _update_project(self, adapter, values):
        adapter.write(self.external_id, values)

    def _run(self, fields=None):
        adapter = self.unit_for(JiraAdapter)

        key = self.binding.jira_key
        name = self.binding.name[:80]
        template = self.binding.project_template
        # TODO: add lead

        if self.external_id:
            self._update_project(adapter, {'name': name, 'key': key})
        else:
            if template == 'shared':
                shared_key = self.binding.project_template_shared
                self.external_id = self._create_shared_project(
                    adapter, key, name, shared_key, None
                )
            else:
                self.external_id = self._create_project(
                    adapter, key, name, template, {}
                )
