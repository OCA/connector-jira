# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.mapper import ImportMapper, mapping
from ...unit.importer import (
    BatchImporter,
    DirectBatchImporter,
    JiraImporter,
)
from ...backend import jira


@jira
class IssueTypeMapper(ImportMapper):
    _model_name = 'jira.issue.type'

    direct = [
        ('name', 'name'),
        ('description', 'description'),
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@jira
class IssueTypeBatchImporter(DirectBatchImporter):
    """ Import the Jira Issue Types

    For every id in in the list of issue types, a delayed job is created.
    Import from a date
    """
    _model_name = 'jira.issue.type'

    def run(self):
        """ Run the synchronization """
        record_ids = self.backend_adapter.search()
        for record_id in record_ids:
            self._import_record(record_id)


@jira
class IssueTypeImporter(JiraImporter):
    _model_name = 'jira.issue.type'


@job(default_channel='root.connector_jira.import')
def import_batch_issue_type(session, model_name, backend_id):
    """ Prepare a batch import of issue types from Jira """
    backend = session.env['jira.backend'].browse(backend_id)
    with backend.get_environment(model_name, session=session) as connector_env:
        importer = connector_env.get_connector_unit(BatchImporter)
        importer.run()
