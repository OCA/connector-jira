# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        ALTER TABLE jira_backend_timestamp
        ADD COLUMN last_timestamp timestamp;
    """)
    cr.execute("""
        UPDATE jira_backend_timestamp
        SET last_timestamp = import_start_time;
    """)
    cr.execute("""
        ALTER TABLE jira_backend_timestamp
        ALTER COLUMN last_timestamp SET NOT NULL;
    """)

    cr.execute("""
        ALTER TABLE jira_account_analytic_line
        ADD COLUMN jira_updated_at timestamp;
    """)
    cr.execute("""
        UPDATE jira_account_analytic_line
        SET jira_updated_at = sync_date;
    """)

    cr.execute("""
        ALTER TABLE jira_project_task
        ADD COLUMN jira_updated_at timestamp;
    """)
    cr.execute("""
        UPDATE jira_project_task
        SET jira_updated_at = sync_date;
    """)
