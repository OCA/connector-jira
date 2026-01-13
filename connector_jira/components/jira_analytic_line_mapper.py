# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from pytz import timezone, utc

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

from .common import iso8601_to_naive_date, iso8601_to_utc_datetime, whenempty


class JiraAnalyticLineMapper(Component):
    _name = "jira.analytic.line.mapper"
    _inherit = "jira.import.mapper"
    _apply_on = ["jira.account.analytic.line"]

    direct = [(whenempty("comment", _("missing description")), "name")]

    @mapping
    def issue(self, record):
        issue = self.options.linked_issue
        assert issue
        refs = {"jira_issue_id": record["issueId"], "jira_issue_key": issue["key"]}
        mapper = self.component(usage="import.mapper", model_name="jira.project.task")
        issue_type_dict = mapper.issue_type(issue)
        refs.update(issue_type_dict)
        epic_field_name = self.backend_record.epic_link_field_name
        if epic_field_name and epic_field_name in issue["fields"]:
            refs["jira_epic_issue_key"] = issue["fields"][epic_field_name]
        if self.backend_record.epic_link_on_epic:
            issue_type_id = issue_type_dict.get("jira_issue_type_id")
            issue_type = self.env["jira.issue.type"].browse(issue_type_id)
            if issue_type.exists() and issue_type.name == "Epic":
                refs["jira_epic_issue_key"] = issue.get("key")
        return refs

    @mapping
    def date(self, record):
        mode = self.backend_record.worklog_date_timezone_mode
        started = record["started"]
        if not mode or mode == "naive":
            return {"date": iso8601_to_naive_date(started)}
        started = iso8601_to_utc_datetime(started).replace(tzinfo=utc)
        if mode == "user":
            tz = timezone(record["author"]["timeZone"])
        elif mode == "specific":
            tz = timezone(self.backend_record.worklog_date_timezone)
        else:
            raise NotImplementedError("Cannot parse date with mode '%s'", mode)
        return {"date": started.astimezone(tz).date()}

    @mapping
    def duration(self, record):
        # amount is in float in odoo... 9000.00s = 2h30m00s = 2.5h
        return {"unit_amount": float(record["timeSpentSeconds"]) / 3600}

    @mapping
    def author(self, record):
        author = record["author"]
        key = author["accountId"]
        user = self.binder_for("jira.res.users").to_internal(key, unwrap=True)
        if not user:
            raise MappingError(
                _(
                    "No user found with login '%(key)s' or email '%(mail)s'."
                    " You must create a user or link it manually if the"
                    " login/email differs.",
                    key=key,
                    mail=author.get("emailAddress", "<unknown>"),
                )
            )
        # NB: in v15.0, the employee was retrieved via a ``search()`` on ``hr.employee``
        # with no constraints on the company; we change this to accessing field
        # ``employee_id`` which is a computed field whose value depend on the
        # environment's company to fetch the correct employee and avoids multi-company
        # consistency issues.
        # (We keep the ``active_test=False`` anyway)
        employee = user.with_context(active_test=False).employee_id
        if not employee:
            # In case no employee is found, fallback to the v15.0 behavior, which is:
            # find any employee linked to the user, regardless of the company
            employee = employee.search([("user_id", "=", user.id)], limit=1)
        return {"user_id": user.id, "employee_id": employee.id}

    @mapping
    def project_and_task(self, record):
        if self.options.task_binding:
            task_binding = self.options.task_binding
            return {
                "task_id": task_binding.odoo_id.id,
                "project_id": task_binding.project_id.id,
                "jira_project_bind_id": task_binding.jira_project_bind_id.id,
            }
        elif self.options.project_binding:
            project_binding = self.options.project_binding
            return {
                "project_id": project_binding.odoo_id.id,
                "jira_project_bind_id": project_binding.id,
            }
        elif self.options.fallback_project:
            return {"project_id": self.options.fallback_project.id}
        raise ValueError("No task binding, project binding or fallback project found.")

    @mapping
    def backend_id(self, record):
        return {"backend_id": self.backend_record.id}
