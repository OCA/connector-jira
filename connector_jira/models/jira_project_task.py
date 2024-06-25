# Copyright 2016-2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, exceptions, fields, models


class JiraProjectTask(models.Model):
    _name = "jira.project.task"
    _inherit = "jira.binding"
    _inherits = {"project.task": "odoo_id"}
    _description = "Jira Tasks"

    odoo_id = fields.Many2one(
        comodel_name="project.task",
        string="Task",
        required=True,
        index=True,
        ondelete="restrict",
    )
    # As we can have more than one jira binding on a project.project, we store
    # to which one a task binding is related.
    jira_project_bind_id = fields.Many2one(
        comodel_name="jira.project.project",
        ondelete="restrict",
    )
    jira_key = fields.Char(
        string="Key",
    )
    jira_issue_type_id = fields.Many2one(
        comodel_name="jira.issue.type",
        string="Issue Type",
    )
    jira_epic_link_id = fields.Many2one(
        comodel_name="jira.project.task",
        string="Epic",
    )
    jira_parent_id = fields.Many2one(
        comodel_name="jira.project.task",
        string="Parent Issue",
        help="Parent issue when the issue is a subtask. "
        "Empty if the type of parent is filtered out "
        "of the synchronizations.",
    )
    jira_issue_url = fields.Char(
        string="JIRA issue",
        compute="_compute_jira_issue_url",
    )

    _sql_constraints = [
        (
            "jira_binding_backend_uniq",
            "unique(backend_id, odoo_id)",
            "A binding already exists for this task and this backend.",
        ),
    ]

    def _is_linked(self):
        return self.jira_project_bind_id._is_linked()

    @api.ondelete(at_uninstall=False)
    def _unlink_unless_is_jira_task(self):
        if any(self.mapped("external_id")):
            raise exceptions.UserError(_("A Jira task cannot be deleted."))

    @api.depends("backend_id.uri", "jira_key")
    def _compute_jira_issue_url(self):
        """Compute the external URL to JIRA."""
        for record in self:
            record.jira_issue_url = record.backend_id.make_issue_url(record.jira_key)
