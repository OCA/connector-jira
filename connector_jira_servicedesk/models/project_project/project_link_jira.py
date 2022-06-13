# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ProjectLinkJira(models.TransientModel):
    _inherit = "project.link.jira"

    @api.model
    def _selection_state(self):
        states = super()._selection_state()
        states.append(("link_organizations", "Link Organizations"))
        return states

    def state_exit_start(self):
        if self.sync_action == "link":
            self.state = "link_organizations"
        else:
            res = super().state_exit_start()
            return res

    def state_exit_link_organizations(self):
        if not self.jira_project_id:
            self._link_binding()
        self.state = "issue_types"

    def _prepare_link_binding_values(self, jira_project):
        values = super()._prepare_link_binding_values(jira_project)
        values["organization_ids"] = [(6, 0, self.organization_ids.ids)]
        return values
