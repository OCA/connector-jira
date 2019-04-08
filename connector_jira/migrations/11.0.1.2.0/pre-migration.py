# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tools.sql import column_exists


def migrate(cr, version):
    if not version:
        return
    if not column_exists(cr, 'jira_backend_timestamp', 'last_timestamp'):
        cr.execute("""
            ALTER TABLE jira_backend_timestamp
            ADD COLUMN last_timestamp timestamp;
        """)
    cr.execute("""
        UPDATE jira_backend_timestamp
        SET last_timestamp = import_start_time
        WHERE last_timestamp IS NULL;
    """)
    cr.execute("""
        ALTER TABLE jira_backend_timestamp
        ALTER COLUMN last_timestamp SET NOT NULL;
    """)

    if not column_exists(cr, 'jira_account_analytic_line', 'jira_updated_at'):
        cr.execute("""
            ALTER TABLE jira_account_analytic_line
            ADD COLUMN jira_updated_at timestamp;
        """)
    cr.execute("""
        UPDATE jira_account_analytic_line
        SET jira_updated_at = sync_date
        WHERE jira_updated_at IS NULL;
    """)

    if not column_exists(cr, 'jira_project_task', 'jira_updated_at'):
        cr.execute("""
            ALTER TABLE jira_project_task
            ADD COLUMN jira_updated_at timestamp;
        """)
    cr.execute("""
        UPDATE jira_project_task
        SET jira_updated_at = sync_date
        WHERE jira_updated_at IS NULL;
    """)
