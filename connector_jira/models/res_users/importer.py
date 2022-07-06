# Copyright 2016-2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import JobError


class UserImporter(Component):
    _name = "jira.res.users.importer"
    _inherit = ["jira.importer"]
    _apply_on = ["jira.res.users"]

    def _import(self, binding):
        record = self.external_record
        jira_key = self.external_id
        binder = self.binder_for("jira.res.users")
        user = binder.to_internal(jira_key, unwrap=True)
        if not user:
            email = record["emailAddress"]
            user = self.env["res.users"].search(
                ["|", ("login", "=", jira_key), ("email", "=", email)],
            )
            if len(user) > 1:
                raise JobError(
                    _(
                        "Several users found (%(login)s) for jira account"
                        "%(jira_key)s (%(email)s)."
                        " Please link it manually from the Odoo user's form.",
                        login=user.mapped("login"),
                        jira_key=jira_key,
                        email=email,
                    )
                )
            elif not user:
                raise JobError(
                    _(
                        "No user found for jira account %(jira_key)s (%(email)s)."
                        " Please link it manually from the Odoo user's form.",
                        jira_key=jira_key,
                        email=email,
                    )
                )
            return user.link_with_jira(backends=self.backend_record)
