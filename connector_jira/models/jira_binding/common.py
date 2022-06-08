# Copyright 2016-2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

from ...fields import MilliDatetime


class JiraBinding(models.AbstractModel):
    """Abstract Model for the Bindings.

    All the models used as bindings between Jira and Odoo
    (``jira.product.product``, ...) should ``_inherit`` it.
    """

    _name = "jira.binding"
    _inherit = "external.binding"
    _description = "Jira Binding (abstract)"

    # odoo-side id must be declared in concrete model
    # odoo_id = fields.Many2one(...)
    backend_id = fields.Many2one(
        comodel_name="jira.backend",
        string="Jira Backend",
        required=True,
        ondelete="restrict",
    )
    jira_updated_at = MilliDatetime()
    external_id = fields.Char(string="ID on Jira", index=True)

    _sql_constraints = [
        (
            "jira_binding_uniq",
            "unique(backend_id, external_id)",
            "A binding already exists for this Jira record",
        ),
    ]

    @api.model
    def import_batch(self, backend):
        """Prepare import of a batch of record"""
        with backend.work_on(self._name) as work:
            importer = work.component(usage="batch.importer")
            return importer.run()

    @api.model
    def run_batch_timestamp(self, backend, timestamp, force=False):
        """Prepare batch of records"""
        with backend.work_on(self._name) as work:
            importer = work.component(usage=timestamp.component_usage)
            return importer.run(timestamp, force=force)

    @api.model
    def import_record(self, backend, external_id, force=False, record=None):
        """Import a record"""
        with backend.work_on(self._name) as work:
            importer = work.component(usage="record.importer")
            return importer.run(external_id, force=force, record=record)

    @api.model
    def delete_record(
        self, backend, external_id, only_binding=False, set_inactive=False
    ):
        """Delete a record on Odoo"""
        with backend.work_on(self._name) as work:
            importer = work.component(usage="record.deleter")
            return importer.run(
                external_id,
                only_binding=only_binding,
                set_inactive=set_inactive,
            )

    def export_record(self, fields=None):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage="record.exporter")
            return exporter.run(self, fields=fields)
