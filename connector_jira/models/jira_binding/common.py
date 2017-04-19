# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.addons.queue_job.job import job, related_action
from ...unit.importer import JiraImporter, BatchImporter, JiraDeleter
from ...unit.exporter import JiraBaseExporter


class JiraBinding(models.AbstractModel):
    """ Abstract Model for the Bindings.

    All the models used as bindings between Jira and Odoo
    (``jira.product.product``, ...) should ``_inherit`` it.
    """
    _name = 'jira.binding'
    _inherit = 'external.binding'
    _description = 'Jira Binding (abstract)'

    # odoo-side id must be declared in concrete model
    # odoo_id = fields.Many2one(...)
    backend_id = fields.Many2one(
        comodel_name='jira.backend',
        string='Jira Backend',
        required=True,
        ondelete='restrict',
    )
    external_id = fields.Char(string='ID on Jira', index=True)

    _sql_constraints = [
        ('jira_binding_uniq', 'unique(backend_id, external_id)',
         "A binding already exists for this Jira record"),
    ]

    @job(default_channel='root.connector_jira.import')
    @api.model
    def import_batch(self, backend, from_date=None, to_date=None):
        """ Prepare import of a batch of records """
        with backend.get_environment(self._name) as connector_env:
            importer = connector_env.get_connector_unit(BatchImporter)
            importer.run(from_date=from_date, to_date=to_date)

    @job(default_channel='root.connector_jira.import')
    @api.model
    def import_record(self, backend, external_id, force=False):
        """ Import a record """
        with backend.get_environment(self._name) as connector_env:
            importer = connector_env.get_connector_unit(JiraImporter)
            importer.run(external_id, force=force)

    @job(default_channel='root.connector_jira.import')
    @api.model
    def delete_record(self, backend, external_id):
        """ Delete a record on Odoo """
        with backend.get_environment(self._name) as connector_env:
            importer = connector_env.get_connector_unit(JiraDeleter)
            importer.run(external_id)

    @job(default_channel='root.connector_jira.export')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_record(self, fields=None):
        self.ensure_one()
        with self.backend_id.get_environment(self._name) as connector_env:
            exporter = connector_env.get_connector_unit(JiraBaseExporter)
            exporter.run(self, fields=fields)
