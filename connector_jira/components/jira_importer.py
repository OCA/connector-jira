# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""

Importers for Jira.

An import can be skipped if the last sync date is more recent than
the last update in Jira.

They should call the ``bind`` method if the binder even if the records
are already bound, to update the last sync date.

"""

import logging
from contextlib import closing, contextmanager

from psycopg2 import IntegrityError, errorcodes

import odoo
from odoo import _, tools

from odoo.addons.component.core import Component
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.queue_job.exception import RetryableJobError

from .common import (
    RETRY_ON_ADVISORY_LOCK,
    RETRY_WHEN_CONCURRENT_DETECTED,
    iso8601_to_utc_datetime,
)

_logger = logging.getLogger(__name__)


class JiraImporter(Component):
    """Base importer for Jira

    If no specific importer is defined for a model, this one is used.
    """

    _name = "jira.importer"
    _inherit = ["base.importer", "jira.base"]
    _usage = "record.importer"

    def __init__(self, work_context):
        super().__init__(work_context)
        self.external_id = None
        self.external_record = None

    def _get_external_data(self):
        """Return the raw Jira data for ``self.external_id``"""
        return self.backend_adapter.read(self.external_id)

    def must_skip(self, force=False):
        """Returns a reason as string if the import must be skipped.

        Returns an empty string to continue with the import.

        :rtype: str
        """
        assert self.external_record
        return ""

    def _before_import(self):
        """Hook called before the import, when we have the Jira data"""

    def _get_external_updated_at(self):
        assert self.external_record
        updated_at = self.external_record.get("fields", {}).get("updated")
        return updated_at and iso8601_to_utc_datetime(updated_at)

    def _is_uptodate(self, binding):
        """Return True if the binding is already up-to-date in Odoo"""
        external_date = self._get_external_updated_at()
        # We store the jira "updated_at" field in the binding,
        # so for further imports, we can check accurately if the
        # record is already up-to-date (this field has a millisecond
        # precision).
        internal_date = bool(binding) and binding.jira_updated_at
        # No update date on Jira, no binding or no last update on the binding => the
        # record does not exist or is not up-to-date, so it should be imported
        return external_date and internal_date and external_date < internal_date

    def _import_dependency(
        self, external_id, binding_model, component=None, record=None, always=False
    ):
        """
        Import a dependency.

        The component that will be used for the dependency can be injected
        with the ``component``.

        :param external_id: id of the related binding to import
        :param binding_model: name of the binding model for the relation
        :type binding_model: str | unicode
        :param component: component to use for the importer
                          By default: lookup component for the model with
                          usage ``record.importer``
        :param record: if we already have the data of the dependency, we
                       can pass it along to the dependency's importer
        :type record: dict
        :param always: if True, the record is updated even if it already
                       exists,
                       it is still skipped if it has not been modified on Jira
        :type always: boolean
        """
        if external_id:
            binder = self.binder_for(binding_model)
            if always or not binder.to_internal(external_id):
                if component is None:
                    component = self.component(
                        usage="record.importer", model_name=binding_model
                    )
                component.run(external_id, record=record, force=True)

    def _import_dependencies(self):
        """Import the dependencies for the record"""
        return

    def _map_data(self):
        """Returns an instance of
        :py:class:`~odoo.addons.component.core.Component`

        """
        return self.mapper.map_record(self.external_record)

    def _validate_data(self, data):
        """Check if the values to import are correct

        Pro-actively check before the ``_create`` or
        ``_update`` if some fields are missing or invalid.

        Raise `InvalidDataError`
        """
        return

    def _filter_data(self, binding, data):
        """Filters out values that aren't actually changing"""
        binding.ensure_one()
        fields = list(data.keys())
        new_values = binding._convert_to_write(data)
        old_binding_values = binding.read(fields, load="_classic_write")[0]
        old_values = binding._convert_to_write(old_binding_values)
        return {f: data[f] for f in fields if new_values[f] != old_values[f]}

    def _get_binding(self):
        """Return the binding id from the jira id"""
        return self.binder.to_internal(self.external_id)

    def _create_data(self, map_record, **kwargs):
        """Get the data to pass to :py:meth:`_create`"""
        return map_record.values(
            for_create=True,
            external_updated_at=self._get_external_updated_at(),
            **kwargs,
        )

    @contextmanager
    def _retry_unique_violation(self):
        """Context manager: catch Unique constraint error and retry the
        job later.

        When we execute several jobs workers concurrently, it happens
        that 2 jobs are creating the same record at the same time
        (especially product templates as they are shared by a lot of
        sales orders), resulting in:

            IntegrityError: duplicate key value violates unique
            constraint "jira_project_project_external_id_uniq"
            DETAIL:  Key (backend_id, external_id)=(1, 4851) already exists.

        In that case, we'll retry the import just later.

        """
        try:
            yield
        except IntegrityError as err:
            if err.pgcode == errorcodes.UNIQUE_VIOLATION:
                raise RetryableJobError(
                    "A database error caused the failure of the job:\n"
                    "%s\n\n"
                    "Likely due to 2 concurrent jobs wanting to create "
                    "the same record. The job will be retried later." % err
                ) from err
            else:
                raise

    def _create_context(self):
        return {
            "connector_jira": True,
            "connector_no_export": True,
            "tracking_disable": True,
        }

    def _create(self, data):
        """Create the Odoo record"""
        # special check on data before import
        self._validate_data(data)
        with self._retry_unique_violation():
            model_ctx = self.model.with_context(**self._create_context())
            binding = model_ctx.sudo().create(data)

        _logger.debug("%s created from Jira %s", binding, self.external_id)
        return binding

    def _update_data(self, map_record, **kwargs):
        """Get the data to pass to :py:meth:`_update`"""
        return map_record.values(
            external_updated_at=self._get_external_updated_at(), **kwargs
        )

    def _update_context(self):
        return {
            "connector_jira": True,
            "connector_no_export": True,
            "tracking_disable": True,
        }

    def _update(self, binding, data):
        """Update an Odoo record"""
        data = self._filter_data(binding, data)
        if not data:
            _logger.debug(
                "%s not updated from Jira %s as nothing changed",
                binding,
                self.external_id,
            )
            return
        self._validate_data(data)
        binding_ctx = binding.with_context(**self._update_context())
        binding_ctx.sudo().write(data)
        _logger.debug("%s updated from Jira %s", binding, self.external_id)
        return

    def _after_import(self, binding):
        """Hook called at the end of the import"""
        return

    @contextmanager
    def do_in_new_work_context(self, model_name=None):
        """Context manager that yields a new component work context

        Using a new Odoo Environment thus a new PG transaction.

        This can be used to make a preemptive check in a new transaction,
        for instance to see if another transaction already made the work.
        """
        registry = odoo.registry(self.env.cr.dbname)
        with closing(registry.cursor()) as cr:
            try:
                new_env = odoo.api.Environment(cr, self.env.uid, self.env.context)
                backend = self.backend_record.with_env(new_env)
                with backend.work_on(model_name or self.model._name) as work:
                    yield work
            except Exception:
                cr.rollback()
                raise
            else:
                if not tools.config["test_enable"]:
                    cr.commit()  # pylint: disable=invalid-commit

    def _handle_record_missing_on_jira(self):
        """Hook called when we are importing a record missing on Jira

        By default, it deletes the matching record or binding if it exists on
        Odoo and returns a result to show on the job, job will be done.
        """
        binding = self._get_binding()
        if binding:
            # emptying the external_id allows to unlink the binding
            binding.external_id = False
            binding.unlink()
        return _("Record does no longer exist in Jira")

    def run(self, external_id, force=False, record=None, **kwargs):
        """Run the synchronization

        A record can be given, reducing number of calls when
        a call already returns data (example: user returns addresses)

        :param external_id: identifier of the record on Jira
        """
        self.external_id = external_id
        lock_name = "import({}, {}, {}, {})".format(
            self.backend_record._name,
            self.backend_record.id,
            self.model._name,
            self.external_id,
        )
        # Keep a lock on this import until the transaction is committed
        self.advisory_lock_or_retry(lock_name, retry_seconds=RETRY_ON_ADVISORY_LOCK)
        if record is not None:
            self.external_record = record
        else:
            try:
                self.external_record = self._get_external_data()
            except IDMissingInBackend:
                return self._handle_record_missing_on_jira()
        binding = self._get_binding()
        if not binding:
            with self.do_in_new_work_context() as new_work:
                # Even when we use an advisory lock, we may have
                # concurrent issues.
                # Explanation:
                # We import Partner A and B, both of them import a
                # partner category X.
                #
                # The squares represent the duration of the advisory
                # lock, the transactions starts and ends on the
                # beginnings and endings of the 'Import Partner'
                # blocks.
                # T1 and T2 are the transactions.
                #
                # ---Time--->
                # > T1 /------------------------\
                # > T1 | Import Partner A       |
                # > T1 \------------------------/
                # > T1        /-----------------\
                # > T1        | Imp. Category X |
                # > T1        \-----------------/
                #                     > T2 /------------------------\
                #                     > T2 | Import Partner B       |
                #                     > T2 \------------------------/
                #                     > T2        /-----------------\
                #                     > T2        | Imp. Category X |
                #                     > T2        \-----------------/
                #
                # As you can see, the locks for Category X do not
                # overlap, and the transaction T2 starts before the
                # commit of T1. So no lock prevents T2 to import the
                # category X and T2 does not see that T1 already
                # imported it.
                #
                # The workaround is to open a new DB transaction at the
                # beginning of each import (e.g. at the beginning of
                # "Imp. Category X") and to check if the record has been
                # imported meanwhile. If it has been imported, we raise
                # a Retryable error so T2 is rollbacked and retried
                # later (and the new T3 will be aware of the category X
                # from its inception).
                binder = new_work.component(usage="binder")
                if binder.to_internal(self.external_id):
                    raise RetryableJobError(
                        "Concurrent error. The job will be retried later",
                        seconds=RETRY_WHEN_CONCURRENT_DETECTED,
                        ignore_retry=True,
                    )

        reason = self.must_skip(force=force)
        if reason:
            return reason

        if not force and self._is_uptodate(binding):
            return _("Already up-to-date.")

        self._before_import()

        # import the missing linked resources
        self._import_dependencies()

        self._import(binding, **kwargs)

    def _import(self, binding, **kwargs):
        """Import the external record.

        Can be inherited to modify for instance the environment
        (change current user, values in context, ...)

        """
        map_record = self._map_data()

        if binding:
            record = self._update_data(map_record)
            self._update(binding, record)
        else:
            record = self._create_data(map_record)
            binding = self._create(record)

        with self._retry_unique_violation():
            self.binder.bind(self.external_id, binding)

        self._after_import(binding)
