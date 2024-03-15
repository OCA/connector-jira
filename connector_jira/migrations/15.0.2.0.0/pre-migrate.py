# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)


def migrate(cr, version):
    remove_field_selection(cr)


def remove_field_selection(cr, version):
    query = """
        DELETE FROM ir_model_fields_selection
        USING ir_model_fields f, ir_model m
        WHERE f.model_id = m.id AND m.name='jira.backend.auth' AND field_id=f.id;
    """
    cr.execute(query)
