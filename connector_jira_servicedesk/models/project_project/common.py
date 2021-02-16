# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
import urllib.parse

from odoo import _, api, exceptions, fields, models


class JiraProjectBaseFields(models.AbstractModel):
    """JIRA Project Base fields

    Shared by the binding jira.project.project
    and the wizard to link/create a JIRA project
    """

    _inherit = "jira.project.base.mixin"

    organization_ids = fields.Many2many(
        comodel_name="jira.organization",
        string="Organization(s) on Jira",
        domain="[('backend_id', '=', backend_id)]",
        help="If organizations are set, a task will be "
        "added to the project only if the project AND "
        "the organization match with the selection.",
    )


class JiraProjectProject(models.Model):
    _inherit = "jira.project.project"

    servicedesk_customer_portal_number = fields.Integer(
        string="Service desk customer portal ID",
        help="This number is used to compute servicedesk URL on analytic lines",
    )

    @api.model
    def _selection_project_type(self):
        selection = super()._selection_project_type()
        selection.append(("service_desk", "Service Desk"))
        return selection

    @api.constrains("backend_id", "external_id", "organization_ids")
    def _constrains_jira_uniq(self):
        """Modify the base constraint by adding organizations

        Rather than checking unicity of backend+jira id, we validate
        backend+jira id+organizations ids.

        It allows to have different odoo projects depending of the
        organization used on Jira.

        """
        for binding in self:
            if not binding.external_id:
                continue
            same_link_bindings = self.with_context(active_test=False).search(
                [
                    ("id", "!=", binding.id),
                    ("backend_id", "=", binding.backend_id.id),
                    ("external_id", "=", binding.external_id),
                ]
            )
            for other in same_link_bindings:
                my_orgs = binding.organization_ids
                other_orgs = other.organization_ids
                if not my_orgs and not other_orgs:
                    raise exceptions.ValidationError(
                        _(
                            "The project %s is already linked with the same"
                            " JIRA project without organization."
                        )
                        % (other.display_name)
                    )
                if set(my_orgs.ids) == set(other_orgs.ids):
                    raise exceptions.ValidationError(
                        _(
                            "The project %s is already linked with this "
                            "JIRA project and similar organizations."
                        )
                        % (other.display_name)
                    )

    def make_servicedesk_issue_url(self, jira_issue_id):
        return urllib.parse.urljoin(
            self.backend_id.uri,
            "/service_desk/customer/portal/{}/{}".format(
                self.servicedesk_customer_portal_number, jira_issue_id
            ),
        )
