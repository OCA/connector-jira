# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp.addons.connector.unit.mapper import ImportMapper, mapping
from ...unit.importer import (
    DelayedBatchImporter,
    JiraImporter,
)
from ...unit.mapper import FromFields
from ...backend import jira


@jira
class ProjectTaskMapper(ImportMapper, FromFields):
    _model_name = 'jira.project.task'

    from_fields = [
        ('summary', 'name'),
        ('duedate', 'date_deadline'),
    ]

    # TODO:
    # responsible

    @mapping
    def description(self, record):
        # TODO: description is a variant of wiki syntax...
        # and the Odoo field is HTML...
        return {'description': record['fields']['description']}

    @mapping
    def project(self, record):
        jira_project_id = record['fields']['project']['id']
        binder = self.binder_for('jira.project.project')
        project = binder.to_openerp(jira_project_id, unwrap=True)
        # TODO: map to an "Unaffected" project if project is missing
        # or import the project in _import_dependencies() of the importer
        return {'project_id': project.id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@jira
class ProjectTaskBatchImporter(DelayedBatchImporter):
    """ Import the Jira tasks

    For every id in in the list of tasks, a delayed job is created.
    Import from a date
    """
    _model_name = 'jira.project.task'


@jira
class ProjectTaskImporter(JiraImporter):
    _model_name = 'jira.project.task'
