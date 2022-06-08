# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from itertools import groupby

from odoo import _, exceptions, fields, models

from odoo.addons.component.core import Component


class JiraResUsers(models.Model):
    _name = "jira.res.users"
    _inherit = "jira.binding"
    _inherits = {"res.users": "odoo_id"}
    _description = "Jira User"

    odoo_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        index=True,
        ondelete="restrict",
    )


class ResUsers(models.Model):
    _inherit = "res.users"

    jira_bind_ids = fields.One2many(
        comodel_name="jira.res.users",
        inverse_name="odoo_id",
        copy=False,
        string="User Bindings",
        context={"active_test": False},
    )

    def button_link_with_jira(self):
        self.ensure_one()
        self.link_with_jira(raise_if_mismatch=True)
        if not self.jira_bind_ids:
            raise exceptions.UserError(_("No JIRA user could be found"))

    def link_with_jira(self, backends=None, raise_if_mismatch=False):
        if backends is None:
            backends = self.env["jira.backend"].search([])
        result = {}
        for backend in backends:
            bknd_result = {
                "success": [],
                "error": [],
            }
            with backend.work_on("jira.res.users") as work:
                binder = work.component(usage="binder")
                adapter = work.component(usage="backend.adapter")
                for user in self:
                    if binder.to_external(user, wrap=True):
                        continue
                    jira_user = None
                    for resolve_by in backend.get_user_resolution_order():
                        resolve_by_key = resolve_by
                        resolve_by_value = user[resolve_by]
                        jira_user = adapter.search(fragment=resolve_by_value)
                        if jira_user:
                            break
                    if not jira_user:
                        continue
                    elif len(jira_user) > 1:
                        if raise_if_mismatch:
                            raise exceptions.UserError(
                                _(
                                    'Several users found with "%(resolve_by_key)s"'
                                    'set to "%(resolve_by_value)s". '
                                    "Set it manually.",
                                    resolve_by_key=resolve_by_key,
                                    resolve_by_value=resolve_by_value,
                                )
                            )
                        bknd_result["error"].append(
                            {
                                "key": resolve_by_key,
                                "value": resolve_by_value,
                                "error": "multiple_found",
                                "detail": [x.key for x in jira_user],
                            }
                        )
                        continue
                    jira_user = jira_user[0]
                    existing = (
                        self.env["jira.res.users"]
                        .with_context(
                            active_test=False,
                        )
                        .search(
                            [
                                ("backend_id", "=", backend.id),
                                ("external_id", "=", jira_user.key),
                                ("odoo_id", "!=", user.id),
                            ]
                        )
                    )
                    if existing:
                        bknd_result["error"].append(
                            {
                                "key": resolve_by_key,
                                "value": resolve_by_value,
                                "error": "other_user_bound",
                                "detail": "linked with {}".format(existing.login),
                            }
                        )
                        continue
                    try:
                        binding = self.env["jira.res.users"].create(
                            {"backend_id": backend.id, "odoo_id": user.id}
                        )
                        binder.bind(jira_user.key, binding)
                        bknd_result["success"].append(
                            {
                                "key": "login",
                                "value": user.login,
                                "detail": jira_user.key,
                            }
                        )
                    except Exception as err:
                        bknd_result["error"].append(
                            {
                                "key": "login",
                                "value": user.login,
                                "error": "binding_error",
                                "detail": str(err),
                            }
                        )
            result[backend] = bknd_result
        return result


class UserAdapter(Component):
    _name = "jira.res.users.adapter"
    _inherit = ["jira.webservice.adapter"]
    _apply_on = ["jira.res.users"]

    def read(self, id_):
        # pylint: disable=W8106
        with self.handle_404():
            return self.client.user(id_).raw

    def search(self, fragment=None):
        """Search users

        :param fragment: a string to match usernames, name or email against.
        """
        users = self.client.search_users(
            fragment, maxResults=None, includeActive=True, includeInactive=True
        )

        # User 'key' is unique and if same key appears several times, it means
        # that same user is present in multiple User Directories
        users = list(
            map(
                lambda group: list(group[1])[0],
                groupby(users, key=lambda user: user.key),
            )
        )

        return users
