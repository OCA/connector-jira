# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models, exceptions, _


class JiraProjectBaseFields(models.AbstractModel):
    """JIRA Project Base fields

    Shared by the binding jira.project.project
    and the wizard to link/create a JIRA project
    """
    _inherit = 'jira.project.base.mixin'

    organization_ids = fields.Many2many(
        comodel_name='jira.organization',
        string='Organization(s) on Jira',
        domain="[('backend_id', '=', backend_id)]",
        help="If organizations are set, a task will be "
             "added to the project only if the project AND "
             "the organization match with the selection."
    )


class JiraProjectProject(models.Model):
    _inherit = 'jira.project.project'

    @api.constrains('backend_id', 'external_id', 'organization_ids')
    @api.multi
    def _constrains_jira_uniq(self):
        for binding in self:
            same_link_bindings = self.search([
                ('id', '!=', self.id),
                ('backend_id', '=', self.backend_id.id),
                ('external_id', '=', self.external_id),
            ])
            for other in same_link_bindings:
                my_orgs = binding.organization_ids
                other_orgs = other.organization_ids
                if not my_orgs and not other_orgs:
                    raise exceptions.ValidationError(_(
                        "The project %s is already linked with the same"
                        " JIRA project without organization."
                    ) % (other.display_name))
                if set(my_orgs.ids) == set(other_orgs.ids):
                    raise exceptions.ValidationError(_(
                        "The project %s is already linked with this "
                        "JIRA project and similar organizations."
                    ) % (other.display_name))
