# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        ALTER TABLE jira_backend_timestamp
        ADD COLUMN import_timestamp timestamp;
    """)
    cr.execute("""
        UPDATE jira_backend_timestamp
        SET import_timestamp = import_start_time;
    """)
    cr.execute("""
        ALTER TABLE jira_backend_timestamp
        ALTER COLUMN import_timestamp SET NOT NULL;
    """)
