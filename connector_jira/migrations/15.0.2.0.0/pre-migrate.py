# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)


def migrate(cr, version):
    remove_field_selection(cr)


def remove_field_selection(cr):
    queries = [
        # delete xml ids of ir.model.fields.selections
        "DELETE FROM ir_model_data imd "
        "USING ir_model_fields_selection fs, ir_model_fields f, ir_model m "
        "WHERE imd.module='connector_jira' "
        "AND imd.model='ir.model.fields.selection' "
        "AND res_id=fs.id "
        "AND f.model_id = m.id "
        "AND m.name='jira.backend.auth' "
        "AND fs.field_id=f.id;",
        # delete ir_model_fields_selection
        "DELETE FROM ir_model_fields_selection "
        "USING ir_model_fields f, ir_model m "
        "WHERE f.model_id = m.id "
        "AND m.name='jira.backend.auth' "
        "AND field_id=f.id;",
    ]

    for query in queries:
        cr.execute(query)
