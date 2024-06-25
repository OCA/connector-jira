# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.tools import groupby


class JiraAccountAnalyticLine(models.Model):
    _name = "jira.account.analytic.line"
    _inherit = "jira.binding"
    _inherits = {"account.analytic.line": "odoo_id"}
    _description = "Jira Worklog"

    odoo_id = fields.Many2one(
        comodel_name="account.analytic.line",
        string="Timesheet",
        required=True,
        index=True,
        ondelete="restrict",
    )
    # The REST API needs issue id + worklog id, so we keep it along
    # in case we'll need it for an eventual export
    jira_issue_id = fields.Char()

    # As we can have more than one jira binding on a project.project, we store
    # to which one a task binding is related.
    jira_project_bind_id = fields.Many2one(
        comodel_name="jira.project.project",
        ondelete="restrict",
    )

    # we have to store these fields on the analytic line because
    # they may be different than the ones on their odoo task:
    # for instance, we do not import "Tasks" but we import "Epics",
    # the analytic line for a "Task" will be linked to an "Epic" on
    # Odoo, but we still want to know the original task here
    jira_issue_key = fields.Char(string="Original Task Key")
    jira_issue_type_id = fields.Many2one(
        comodel_name="jira.issue.type",
        string="Original Issue Type",
    )
    jira_issue_url = fields.Char(
        string="Original JIRA issue Link",
        compute="_compute_jira_issue_url",
        store=True,
    )
    jira_epic_issue_key = fields.Char(string="Original Epic Key")
    jira_epic_issue_url = fields.Char(
        string="Original JIRA Epic Link",
        compute="_compute_jira_issue_url",
        store=True,
    )

    _sql_constraints = [
        (
            "jira_binding_backend_uniq",
            "unique(backend_id, odoo_id)",
            "A binding already exists for this line and this backend.",
        ),
    ]

    def _is_linked(self):
        return self.jira_project_bind_id._is_linked()

    @api.depends(
        "backend_id", "backend_id.uri", "jira_issue_key", "jira_epic_issue_key"
    )
    def _compute_jira_issue_url(self):
        """Compute the external URL to JIRA."""
        for backend, records in groupby(self, key=lambda r: r.backend_id):
            if backend:
                urlmaker = backend.make_issue_url
            else:

                def urlmaker(*args, **kwargs):
                    return ""

            for record in records:
                record.jira_issue_url = urlmaker(record.jira_issue_key)
                record.jira_epic_issue_url = urlmaker(record.jira_epic_issue_key)

    @api.model
    def import_record(self, backend, issue_id, worklog_id, force=False):
        """Import a worklog from JIRA"""
        with backend.work_on(self._name) as work:
            importer = work.component(usage="record.importer")
            return importer.run(worklog_id, issue_id=issue_id, force=force)

    def force_reimport(self):
        for binding in self.sudo():
            binding.with_delay(priority=8).import_record(
                binding.backend_id,
                binding.jira_issue_id,
                binding.external_id,
                force=True,
            )
