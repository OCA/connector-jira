# Copyright 2019-2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class AnalyticLineImporter(Component):
    _inherit = "jira.analytic.line.importer"

    @property
    def _issue_fields_to_read(self):
        issue_fields = super()._issue_fields_to_read
        organization_field_name = self.backend_record.organization_field_name
        if not organization_field_name:
            return issue_fields
        return issue_fields + [organization_field_name]
