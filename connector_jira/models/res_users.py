# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import _, exceptions, fields, models


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
        jira_user_model = self.env["jira.res.users"]
        if backends is None:
            backends = self.env["jira.backend"].search([])

        # TODO: try to split this method, though it's quite hard since all its variables
        #  are used somewhere in the method itself...
        result = {}
        for backend in backends:
            bknd_result = {"success": [], "error": []}
            result[backend] = bknd_result
            with backend.work_on("jira.res.users") as work:
                binder = work.component(usage="binder")
                adapter = work.component(usage="backend.adapter")
                for user in self:
                    # Already linked to the current user
                    if binder.to_external(user, wrap=True):
                        continue

                    # Retrieve users in Jira
                    jira_users = []
                    for resolve_by in backend.get_user_resolution_order():
                        resolve_by_key = resolve_by
                        resolve_by_value = user[resolve_by]
                        jira_users = adapter.search(fragment=resolve_by_value or "")
                        if jira_users:
                            break

                    # No user => nothing to do
                    if not jira_users:
                        continue

                    # Multiple users => raise an error or log the info
                    elif len(jira_users) > 1:
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
                                "detail": [x.accountId for x in jira_users],
                            }
                        )
                        continue

                    # Exactly 1 user in Jira => extract it, bind it to the current user
                    external_id = jira_users[0].accountId
                    domain = [
                        ("backend_id", "=", backend.id),
                        ("external_id", "=", external_id),
                        ("odoo_id", "!=", user.id),
                    ]
                    existing = jira_user_model.with_context(active=False).search(domain)

                    # Jira user is already linked to an Odoo user => log the info
                    if existing:
                        bknd_result["error"].append(
                            {
                                "key": resolve_by_key,
                                "value": resolve_by_value,
                                "error": "other_user_bound",
                                "detail": f"linked with {existing.login}",
                            }
                        )
                        continue

                    # Create binding
                    vals = {"backend_id": backend.id, "odoo_id": user.id}
                    try:
                        binding = jira_user_model.create(vals)
                        binder.bind(external_id, binding)
                    except Exception as err:
                        # Log errors
                        bknd_result["error"].append(
                            {
                                "key": "login",
                                "value": user.login,
                                "error": "binding_error",
                                "detail": str(err),
                            }
                        )
                    else:
                        # Log success
                        bknd_result["success"].append(
                            {
                                "key": "login",
                                "value": user.login,
                                "detail": external_id,
                            }
                        )
        return result
