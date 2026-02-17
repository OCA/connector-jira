# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
import urllib.parse

from odoo import _, api, exceptions, fields, models


class JiraProjectProject(models.Model):
    _inherit = "jira.project.project"

    servicedesk_customer_portal_number = fields.Integer(
        string="Service desk customer portal ID",
        help="This number is used to compute servicedesk URL on analytic lines",
    )

    @api.model
    def _selection_project_type(self):
        return super()._selection_project_type() + [("service_desk", "Service Desk")]

    @api.constrains("backend_id", "external_id", "organization_ids")
    def _constrains_jira_uniq(self):
        """Modify the base constraint by adding organizations

        Rather than checking unicity of backend+jira id, we validate
        backend+jira id+organizations ids.

        It allows to have different odoo projects depending of the
        organization used on Jira.

        """
        for binding in self.filtered("external_id"):
            for other in self.with_context(active_test=False).search(
                [
                    ("id", "!=", binding.id),
                    ("backend_id", "=", binding.backend_id.id),
                    ("external_id", "=", binding.external_id),
                ]
            ):
                my_orgs = binding.organization_ids
                other_orgs = other.organization_ids
                if not my_orgs and not other_orgs:
                    raise exceptions.ValidationError(
                        _(
                            "The project %s is already linked with the same"
                            " JIRA project without organization.",
                            other.display_name,
                        )
                    )
                if my_orgs == other_orgs:
                    raise exceptions.ValidationError(
                        _(
                            "The project %s is already linked with this "
                            "JIRA project and similar organizations.",
                            other.display_name,
                        )
                    )

    def make_servicedesk_issue_url(self, jira_issue_id):
        base = self.backend_id.uri
        num = self.servicedesk_customer_portal_number
        url = f"/service_desk/customer/portal/{num}/{jira_issue_id}"
        return urllib.parse.urljoin(base, url)
