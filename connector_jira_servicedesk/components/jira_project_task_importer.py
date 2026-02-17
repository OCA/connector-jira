# Copyright 2016-Today Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.component.core import Component


class JiraProjectTaskImporter(Component):
    _inherit = "jira.project.task.importer"

    def _import_dependencies(self):
        # OVERRIDE: import organizations
        res = super()._import_dependencies()
        for jorg_id in self.component(usage="organization.from.task").get_jira_org_ids(
            self.external_record
        ):
            self._import_dependency(jorg_id, "jira.organization")
        return res
