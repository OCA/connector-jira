# Copyright 2016-2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""

Exporters for Jira.

In addition to its export job, an exporter has to:

* check in Jira if the record has been updated more recently than the
  last sync date and if yes, delay an import
* call the ``bind`` method of the binder to update the last sync date

"""

from contextlib import contextmanager

import psycopg2

from odoo import _, tools

from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import RetryableJobError


class JiraExporter(Component):
    """Common exporter flow for Jira

    If no specific exporter overrides the exporter for a model, this one is
    used.
    """

    _name = "jira.exporter"
    _inherit = ["jira.base.exporter"]
    _usage = "record.exporter"

    def _has_to_skip(self):
        """Return True if the export can be skipped"""
        return False

    @contextmanager
    def _retry_unique_violation(self):
        """Context manager: catch Unique constraint error and retry the
        job later.

        When we execute several jobs workers concurrently, it happens
        that 2 jobs are creating the same record at the same time (binding
        record created by :meth:`_export_dependency`), resulting in:

            IntegrityError: duplicate key value violates unique
            constraint "jira_project_project_odoo_uniq"
            DETAIL:  Key (backend_id, odoo_id)=(1, 4851) already exists.

        In that case, we'll retry the import just later.

        """
        try:
            yield
        except psycopg2.IntegrityError as err:
            if err.pgcode == psycopg2.errorcodes.UNIQUE_VIOLATION:
                raise RetryableJobError(
                    "A database error caused the failure of the job:\n"
                    "%s\n\n"
                    "Likely due to 2 concurrent jobs wanting to create "
                    "the same record. The job will be retried later." % err
                ) from err
            else:
                raise

    def _export_dependency(self, relation, binding_model, component=None):
        """Export a dependency.

        .. warning:: a commit is done at the end of the export of each
                     dependency. The reason for that is that we pushed a record
                     on the backend and we absolutely have to keep its ID.

                     So you *must* take care to not modify the Odoo database
                     excepted when writing back the external ID or eventual
                     external data to keep on this side.

                     You should call this method only in the beginning of
                     exporter synchronization (in `~._export_dependencies`)
                     and do not write data which should be rollbacked in case
                     of error.

        :param relation: record to export if not already exported
        :type relation: :py:class:`odoo.models.BaseModel`
        :param binding_model: name of the binding model for the relation
        :type binding_model: str | unicode
        :param component: component to use for the export
                          By default: lookup a component by usage
                          'record.exporter' and model
        """
        if not relation:
            return
        rel_binder = self.binder_for(binding_model)
        # wrap is typically True if the relation is a 'project.project'
        # record but the binding model is 'jira.project.project'
        wrap = relation._model._name != binding_model

        if wrap and hasattr(relation, "jira_bind_ids"):
            domain = [
                ("odoo_id", "=", relation.id),
                ("backend_id", "=", self.backend_record.id),
            ]
            model = self.env[binding_model].with_context(active_test=False)
            binding = model.search(domain)
            if binding:
                binding.ensure_one()
            else:
                # we are working with a unwrapped record (e.g.
                # product.template) and the binding does not exist yet.
                # Example: I created a product.product and its binding
                # jira.project.project, it is exported, but we need to
                # create the binding for the template.
                bind_values = {
                    "backend_id": self.backend_record.id,
                    "odoo_id": relation.id,
                }
                # If 2 jobs create it at the same time, retry
                # one later. A unique constraint (backend_id,
                # odoo_id) should exist on the binding model
                with self._retry_unique_violation():
                    model_c = (
                        self.env[binding_model]
                        .sudo()
                        .with_context(connector_no_export=True)
                    )
                    binding = model_c.create(bind_values)
                    # Eager commit to avoid having 2 jobs
                    # exporting at the same time.
                    if not tools.config["test_enable"]:
                        self.env.cr.commit()  # pylint: disable=invalid-commit
        else:
            # If jira_bind_ids does not exist we are typically in a
            # "direct" binding (the binding record is the same record).
            # If wrap is True, relation is already a binding record.
            binding = relation

        if not rel_binder.to_external(binding):
            if component is None:
                component = self.component(
                    usage="record.exporter", model_name=binding_model
                )
            component.run(binding.id)

    def _export_dependencies(self):
        """Export the dependencies for the record"""
        return

    def _map_data(self, fields=None):
        """Returns an instance of
        :py:class:`~odoo.addons.component.core.Component`

        """
        return self.mapper.map_record(self.binding)

    def _validate_data(self, data):
        """Check if the values to import are correct

        Pro-actively check before the ``Model.create`` or
        ``Model.update`` if some fields are missing

        Raise `InvalidDataError`
        """
        return

    def _create_data(self, map_record, fields=None, **kwargs):
        """Get the data to pass to :py:meth:`_create`.

        Jira expect that we pass always all the fields, not only
        the modified fields. That's why the `fields` argument
        is None.

        """
        return map_record.values(for_create=True, fields=None, **kwargs)

    def _create(self, data):
        """Create the Jira record"""
        self._validate_data(data)
        return self.backend_adapter.create(data)

    def _update_data(self, map_record, fields=None, **kwargs):
        """Get the data to pass to :py:meth:`_update`.

        Jira expect that we pass always all the fields, not only
        the modified fields. That's why the `fields` argument
        is None.

        """
        return map_record.values(fields=None, **kwargs)

    def _update(self, data):
        """Update a Jira record"""
        assert self.external_id
        self._validate_data(data)
        self.backend_adapter.write(self.external_id, data)

    def _run(self, fields=None):
        """Flow of the synchronization, implemented in inherited classes.

        `~._export_dependencies` might commit exported ids to the database,
        so please do not do changes in the database before the export of the
        dependencies because they won't be rollbacked.
        """
        assert self.binding

        if self._has_to_skip():
            return

        if not self.external_id:
            fields = None  # should be created with all the fields

        # export the missing linked resources
        self._export_dependencies()

        map_record = self._map_data(fields=fields)

        if self.external_id:
            record = self._update_data(map_record, fields=fields)
            if not record:
                return _("Nothing to export.")
            self._update(record)
        else:
            record = self._create_data(map_record, fields=fields)
            if not record:
                return _("Nothing to export.")
            self.external_id = self._create(record)
        return _("Record exported with ID %s on Jira.") % self.external_id
