# Copyright 2019-2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class JiraAnalyticLineImporter(Component):
    _inherit = "jira.analytic.line.importer"

    @property
    def _issue_fields_to_read(self):
        org_fname = self.backend_record.organization_field_name
        return super()._issue_fields_to_read + ([org_fname] if org_fname else [])
