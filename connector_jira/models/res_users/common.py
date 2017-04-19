# Copyright 2016-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _, api, exceptions, fields, models
from odoo.addons.component.core import Component


class JiraResUsers(models.Model):
    _name = 'jira.res.users'
    _inherit = 'jira.binding'
    _inherits = {'res.users': 'odoo_id'}
    _description = 'Jira User'

    odoo_id = fields.Many2one(comodel_name='res.users',
                              string='User',
                              required=True,
                              index=True,
                              ondelete='restrict')


class ResUsers(models.Model):
    _inherit = 'res.users'

    jira_bind_ids = fields.One2many(
        comodel_name='jira.res.users',
        inverse_name='odoo_id',
        copy=False,
        string='User Bindings',
        context={'active_test': False},
    )

    @api.multi
    def button_link_with_jira(self):
        self.ensure_one()
        self.link_with_jira()
        if not self.jira_bind_ids:
            raise exceptions.UserError(
                _('No JIRA user could be found')
            )

    @api.multi
    def link_with_jira(self, backends=None):
        if backends is None:
            backends = self.env['jira.backend'].search([])
        for backend in backends:
            with backend.work_on('jira.res.users') as work:
                binder = work.component(usage='binder')
                adapter = work.component(usage='backend.adapter')
                for user in self:
                    if binder.to_external(user, wrap=True):
                        continue
                    jira_user = adapter.search(fragment=user.email)
                    if not jira_user:
                        jira_user = adapter.search(fragment=user.login)
                    if not jira_user:
                        continue
                    elif len(jira_user) > 1:
                        raise exceptions.UserError(
                            _('Several users found for %s. '
                              'Set it manually..') % user.login
                        )
                    jira_user, = jira_user
                    binding = self.env['jira.res.users'].create({
                        'backend_id': backend.id,
                        'odoo_id': user.id,
                    })
                    binder.bind(jira_user.key, binding)


class UserAdapter(Component):
    _name = 'jira.res.users.adapter'
    _inherit = ['jira.webservice.adapter']
    _apply_on = ['jira.res.users']

    def read(self, id_):
        return self.client.user(id_).raw

    def search(self, fragment=None):
        """ Search users

        :param fragment: a string to match usernames, name or email against.
        """
        users = self.client.search_users(fragment, maxResults=None,
                                         includeActive=True,
                                         includeInactive=True)
        return users
