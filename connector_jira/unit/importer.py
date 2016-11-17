# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

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

import openerp
from openerp import _
from openerp.addons.connector.connector import Binder
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.unit.synchronizer import Importer
from openerp.addons.connector.exception import (IDMissingInBackend,
                                                RetryableJobError)
from .mapper import iso8601_to_utc_datetime
from .backend_adapter import JIRA_JQL_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

RETRY_ON_ADVISORY_LOCK = 1  # seconds
RETRY_WHEN_CONCURRENT_DETECTED = 1  # seconds


class JiraImporter(Importer):
    """ Base importer for Jira """

    def __init__(self, environment):
        """
        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(JiraImporter, self).__init__(environment)
        self.external_id = None
        self.external_record = None

    def _get_external_data(self):
        """ Return the raw Jira data for ``self.external_id`` """
        return self.backend_adapter.read(self.external_id)

    def must_skip(self):
        """ Returns a reason if the import should be skipped.

        Returns None to continue with the import

        """
        assert self.external_record
        return

    def _before_import(self):
        """ Hook called before the import, when we have the Jira
        data"""

    def _is_uptodate(self, binding):
        """Return True if the import should be skipped because
        it is already up-to-date in OpenERP"""
        assert self.external_record
        ext_fields = self.external_record.get('fields', {})
        external_updated_at = ext_fields.get('updated')
        if not external_updated_at:
            return False # no update date on Jira, always import it.
        if not binding:
            return  # it does not exist so it should not be skipped
        external_date = iso8601_to_utc_datetime(external_updated_at)
        sync_date = self.binder.sync_date(binding)
        if not sync_date:
            return
        # if the last synchronization date is greater than the last
        # update in jira, we skip the import.
        # Important: at the beginning of the exporters flows, we have to
        # check if the jira date is more recent than the sync_date
        # and if so, schedule a new import. If we don't do that, we'll
        # miss changes done in Jira
        return external_date < sync_date

    def _import_dependency(self, external_id, binding_model,
                           importer_class=None, record=None, always=False):
        """
        Import a dependency. The importer class is a subclass of
        ``JiraImporter``. A specific class can be defined.

        :param external_id: id of the related binding to import
        :param binding_model: name of the binding model for the relation
        :type binding_model: str | unicode
        :param importer_cls: :py:class:`openerp.addons.connector.\
                                        connector.ConnectorUnit`
                             class or parent class to use for the export.
                             By default: JiraImporter
        :type importer_cls: :py:class:`openerp.addons.connector.\
                                       connector.MetaConnectorUnit`
        :param record: if we already have the data of the dependency, we
                       can pass it along to the dependency's importer
        :type record: dict
        :param always: if True, the record is updated even if it already
                       exists,
                       it is still skipped if it has not been modified on Jira
        :type always: boolean
        """
        if not external_id:
            return
        if importer_class is None:
            importer_class = JiraImporter
        binder = self.binder_for(binding_model)
        if always or not binder.to_openerp(external_id):
            importer = self.unit_for(importer_class, model=binding_model)
            importer.run(external_id, record=record)

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        return

    def _map_data(self):
        """ Returns an instance of
        :py:class:`~openerp.addons.connector.unit.mapper.MapRecord`

        """
        return self.mapper.map_record(self.external_record)

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``_create`` or
        ``_update`` if some fields are missing or invalid.

        Raise `InvalidDataError`
        """
        return

    def _get_binding(self):
        """Return the binding id from the jira id"""
        return self.binder.to_openerp(self.external_id)

    def _create_data(self, map_record, **kwargs):
        """ Get the data to pass to :py:meth:`_create` """
        return map_record.values(for_create=True, **kwargs)

    @contextmanager
    def _retry_unique_violation(self):
        """ Context manager: catch Unique constraint error and retry the
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
                    'A database error caused the failure of the job:\n'
                    '%s\n\n'
                    'Likely due to 2 concurrent jobs wanting to create '
                    'the same record. The job will be retried later.' % err)
            else:
                raise

    def _create_context(self):
        return {
            'connector_no_export': True
        }

    def _create(self, data):
        """ Create the Odoo record """
        # special check on data before import
        self._validate_data(data)
        with self._retry_unique_violation():
            model_ctx = self.model.with_context(**self._create_context())
            binding = model_ctx.create(data)

        _logger.debug('%s created from Jira %s',
                      binding, self.external_id)
        return binding

    def _update_data(self, map_record, **kwargs):
        """ Get the data to pass to :py:meth:`_update` """
        return map_record.values(**kwargs)

    def _update(self, binding, data):
        """ Update an OpenERP record """
        # special check on data before import
        self._validate_data(data)
        binding.with_context(connector_no_export=True).write(data)
        _logger.debug('%s updated from Jira %s', binding, self.external_id)
        return

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        return

    @contextmanager
    def do_in_new_connector_env(self, model_name=None):
        """ Context manager that yields a new connector environment

        Using a new Odoo Environment thus a new PG transaction.

        This can be used to make a preemptive check in a new transaction,
        for instance to see if another transaction already made the work.
        """
        with openerp.api.Environment.manage():
            registry = openerp.modules.registry.RegistryManager.get(
                self.env.cr.dbname
            )
            with closing(registry.cursor()) as cr:
                try:
                    new_env = openerp.api.Environment(cr, self.env.uid,
                                                      self.env.context)
                    new_connector_session = ConnectorSession.from_env(new_env)
                    connector_env = self.connector_env.create_environment(
                        self.backend_record.with_env(new_env),
                        new_connector_session,
                        model_name or self.model._name,
                        connector_env=self.connector_env
                    )
                    yield connector_env
                except:
                    cr.rollback()
                    raise
                else:
                    cr.commit()

    def run(self, external_id, force=False, record=None):
        """ Run the synchronization

        A record can be given, reducing number of calls when
        a call already returns data (example: user returns addresses)

        :param external_id: identifier of the record on Jira
        """
        self.external_id = external_id
        lock_name = 'import({}, {}, {}, {})'.format(
            self.backend_record._name,
            self.backend_record.id,
            self.model._name,
            self.external_id,
        )
        # Keep a lock on this import until the transaction is committed
        self.advisory_lock_or_retry(lock_name,
                                    retry_seconds=RETRY_ON_ADVISORY_LOCK)
        if record is not None:
            self.external_record = record
        else:
            try:
                self.external_record = self._get_external_data()
            except IDMissingInBackend:
                return _('Record does no longer exist in Jira')
        binding = self._get_binding()
        if not binding:
            with self.do_in_new_connector_env() as new_connector_env:
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
                # from the its inception).
                binder = new_connector_env.get_connector_unit(Binder)
                if binder.to_openerp(self.external_id):
                    raise RetryableJobError(
                        'Concurrent error. The job will be retried later',
                        seconds=RETRY_WHEN_CONCURRENT_DETECTED,
                        ignore_retry=True
                    )

        reason = self.must_skip()
        if reason:
            return reason

        if not force and self._is_uptodate(binding):
            return _('Already up-to-date.')

        self._before_import()

        # import the missing linked resources
        self._import_dependencies()

        self._import(binding)

    def _import(self, binding):
        """ Import the external record.

        Can be inherited to modify for instance the session
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


class BatchImporter(Importer):
    """ The role of a BatchImporter is to search for a list of
    items to import, then it can either import them directly or delay
    the import of each item separately.
    """

    def run(self, from_date=None, to_date=None):
        """ Run the synchronization """
        parts = []
        if from_date:
            from_date = from_date.strftime(JIRA_JQL_DATETIME_FORMAT)
            parts.append('updated >= "%s"' % from_date)
        if to_date:
            to_date = to_date.strftime(JIRA_JQL_DATETIME_FORMAT)
            parts.append('updated <= "%s"' % to_date)
        record_ids = self.backend_adapter.search(' and '.join(parts))
        for record_id in record_ids:
            self._import_record(record_id)

    def _import_record(self, record_id):
        """ Import a record directly or delay the import of the record.

        Method to implement in sub-classes.
        """
        raise NotImplementedError


class DirectBatchImporter(BatchImporter):
    """ Import the records directly, without delaying the jobs. """
    _model_name = None

    def _import_record(self, record_id):
        """ Import the record directly """
        import_record(self.session,
                      self.model._name,
                      self.backend_record.id,
                      record_id)


class DelayedBatchImporter(BatchImporter):
    """ Delay import of the records """
    _model_name = None

    def _import_record(self, record_id, **kwargs):
        """ Delay the import of the records"""
        import_record.delay(self.session,
                            self.model._name,
                            self.backend_record.id,
                            record_id,
                            **kwargs)


@job(default_channel='root.connector_jira.import')
def import_batch(session, model_name, backend_id, from_date=None,
                 to_date=None):
    """ Prepare a batch import of records from Jira """
    backend = session.env['jira.backend'].browse(backend_id)
    with backend.get_environment(model_name, session=session) as connector_env:
        importer = connector_env.get_connector_unit(BatchImporter)
        importer.run(from_date=from_date, to_date=to_date)


@job(default_channel='root.connector_jira.normal')
def import_record(session, model_name, backend_id, external_id, force=False):
    """ Import a record from Jira """
    backend = session.env['jira.backend'].browse(backend_id)
    with backend.get_environment(model_name, session=session) as connector_env:
        importer = connector_env.get_connector_unit(JiraImporter)
        importer.run(external_id, force=force)
