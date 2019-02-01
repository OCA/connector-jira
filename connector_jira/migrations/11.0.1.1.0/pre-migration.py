# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
       ALTER TABLE jira_project_project
       DROP CONSTRAINT IF EXISTS
       jira_project_project_jira_binding_backend_uniq;
    """)

    # copy the jira_key from project to binding before we change it
    # as a computed field
    cr.execute("""
        ALTER TABLE jira_project_project
        ADD COLUMN jira_key VARCHAR(10);
    """)
    cr.execute("""
        UPDATE jira_project_project
        SET jira_key = project_project.jira_key
        FROM project_project
        WHERE project_project.id = jira_project_project.odoo_id;
    """)
    cr.execute("""
        ALTER TABLE jira_project_project
        DROP COLUMN jira_key;
    """)

    cr.execute("""
        ALTER TABLE jira_project_project
        ADD COLUMN project_type VARCHAR;
    """)
    # we don't know the correct value, set software by default
    # until 11.0.1.1.0 we cannot have more than one binding,
    # so the constraint will not fail anyway
    cr.execute("""
        UPDATE jira_project_project
        SET project_type = 'software';
    """)
