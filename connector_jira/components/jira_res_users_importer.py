# Copyright 2016-2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import JobError


class JiraResUsersImporter(Component):
    _name = "jira.res.users.importer"
    _inherit = ["jira.importer"]
    _apply_on = ["jira.res.users"]

    def _import(self, binding):
        jira_key = self.external_id
        user = self.binder_for("jira.res.users").to_internal(jira_key, unwrap=True)
        if not user:
            email = self.external_record.get("emailAddress")
            if email is None:
                raise JobError(
                    _(
                        "Unable to find a user from account Id (%s)"
                        " and no email provided",
                        jira_key,
                    )
                )
            user = self.env["res.users"].search([("email", "=", email)])
            if not user:
                raise JobError(
                    _(
                        "No user found for jira account %(key)s (%(mail)s)."
                        " Please link it manually from the Odoo user's form.",
                        key=jira_key,
                        mail=email,
                    )
                )
            elif len(user) > 1:
                raise JobError(
                    _(
                        "Several users found (%(login)s) for jira account %(key)s"
                        " (%(mail)s). Please link it manually from the Odoo user's"
                        " form.",
                        login=", ".join(user.mapped("login")),
                        key=jira_key,
                        mail=email,
                    )
                )
            return user.link_with_jira(backends=self.backend_record)
