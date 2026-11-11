# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class JiraProjectBaseFields(models.AbstractModel):
    """JIRA Project Base fields

    Shared by the binding jira.project.project
    and the wizard to link/create a JIRA project
    """

    _name = "jira.project.base.mixin"
    _description = "JIRA Project Base Mixin"

    jira_key = fields.Char(
        string="JIRA Key",
        required=True,
        size=10,  # limit on JIRA
    )
    sync_issue_type_ids = fields.Many2many(
        comodel_name="jira.issue.type",
        string="Issue Levels to Synchronize",
        domain="[('backend_id', '=', backend_id)]",
        help="Only issues of these levels are imported. "
        "When a worklog is imported no a level which is "
        "not sync'ed, it is attached to the nearest "
        "sync'ed parent level. If no parent can be found, "
        "it is attached to a special 'Unassigned' task.",
    )
    project_template = fields.Selection(
        selection="_selection_project_template",
        string="Default Project Template",
        default="Scrum software development",
    )
    project_template_shared = fields.Char(
        string="Default Shared Template",
    )
    sync_action = fields.Selection(
        selection=[("link", "Link with JIRA"), ("export", "Export to JIRA")],
        default="link",
        required=True,
        help="Defines if the information of the project (name "
        "and key) are exported to JIRA when changed. Link means"
        "the project already exists on JIRA, no sync of the project"
        " details once the link is established."
        " Tasks are always imported from JIRA, not pushed.",
    )

    @api.model
    def _selection_project_template(self):
        return self.env["jira.backend"]._selection_project_template()
