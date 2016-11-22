# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp.addons.connector.event import (on_record_create,
                                            on_record_write,
                                            )
from ... import consumer
from ...backend import jira
from ...unit.exporter import JiraBaseExporter
from ...unit.backend_adapter import JiraAdapter


@on_record_create(model_names='jira.project.project')
@on_record_write(model_names='jira.project.project')
def delay_export(session, model_name, record_id, vals):
    consumer.delay_export(session, model_name, record_id, vals, priority=10)


@on_record_write(model_names='project.project')
def delay_export_all_bindings(session, model_name, record_id, vals):
    if vals.keys() == ['jira_bind_ids']:
        # Binding edited from the project's view.
        # When only this field has been modified, an other job has
        # been delayed for the jira.product.product record.
        return
    consumer.delay_export_all_bindings(session, model_name, record_id, vals)


@jira
class JiraProjectProjectExporter(JiraBaseExporter):
    _model_name = ['jira.project.project']

    def _project_values(self):
        return {
            'key': self.binding_record.jira_key,
            'name': self.binding_record.name[:80],
        }

    def _run(self, fields=None):
        adapter = self.unit_for(JiraAdapter)
        project_values = self._project_values()
        if self.external_id:
            project = adapter.get(self.external_id)
            project.update(project_values)
        else:
            values = project_values.copy()
            key = values.pop('key')
            name = values.pop('name')
            project = adapter.create(
                key=key,
                name=name,
                template_name=self.backend_record.project_template,
                values=values,
            )
            self.external_id = project['projectId']
