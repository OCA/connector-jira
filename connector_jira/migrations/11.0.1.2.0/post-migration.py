# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE jira_backend_timestamp
        SET component_usage = 'timestamp.batch.importer'
        WHERE from_date_field IN (
            'import_analytic_line_from_date',
            'import_project_task_from_date'
        );
    """)
    cr.execute("""
        ALTER TABLE jira_backend_timestamp
        ALTER COLUMN component_usage SET NOT NULL;
    """)
