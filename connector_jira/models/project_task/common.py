# Copyright 2016-2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, exceptions, fields, models
from odoo.osv import expression

from odoo.addons.component.core import Component


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
        readonly=True,
    )
    jira_issue_type_id = fields.Many2one(
        comodel_name="jira.issue.type",
        string="Issue Type",
        readonly=True,
    )
    jira_epic_link_id = fields.Many2one(
        comodel_name="jira.project.task",
        string="Epic",
        readonly=True,
    )
    jira_parent_id = fields.Many2one(
        comodel_name="jira.project.task",
        string="Parent Issue",
        readonly=True,
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
        return self.mapped("jira_project_bind_id")._is_linked()

    def unlink(self):
        if any(self.mapped("external_id")):
            raise exceptions.UserError(_("A Jira task cannot be deleted."))
        return super().unlink()

    @api.depends("jira_key")
    def _compute_jira_issue_url(self):
        """Compute the external URL to JIRA."""
        for record in self:
            record.jira_issue_url = record.backend_id.make_issue_url(record.jira_key)


class ProjectTask(models.Model):
    _inherit = "project.task"

    jira_bind_ids = fields.One2many(
        comodel_name="jira.project.task",
        inverse_name="odoo_id",
        copy=False,
        string="Task Bindings",
        context={"active_test": False},
    )
    jira_issue_type = fields.Char(
        compute="_compute_jira_issue_type",
        string="JIRA Issue Type",
        store=True,
    )
    jira_compound_key = fields.Char(
        compute="_compute_jira_compound_key",
        string="JIRA Key",
        store=True,
    )
    jira_epic_link_task_id = fields.Many2one(
        comodel_name="project.task",
        compute="_compute_jira_epic_link_task_id",
        string="JIRA Epic",
        store=True,
    )
    jira_parent_task_id = fields.Many2one(
        comodel_name="project.task",
        compute="_compute_jira_parent_task_id",
        string="JIRA Parent",
        store=True,
    )
    jira_issue_url = fields.Char(
        string="JIRA issue",
        compute="_compute_jira_issue_url",
    )

    @api.depends("jira_bind_ids.jira_issue_type_id.name")
    def _compute_jira_issue_type(self):
        for record in self:
            types = record.mapped("jira_bind_ids.jira_issue_type_id.name")
            record.jira_issue_type = ",".join([t for t in types if t])

    @api.depends("jira_bind_ids.jira_key")
    def _compute_jira_compound_key(self):
        for record in self:
            keys = record.mapped("jira_bind_ids.jira_key")
            record.jira_compound_key = ",".join([k for k in keys if k])

    @api.depends("jira_bind_ids.jira_epic_link_id.odoo_id")
    def _compute_jira_epic_link_task_id(self):
        for record in self:
            tasks = record.mapped("jira_bind_ids.jira_epic_link_id.odoo_id")
            if len(tasks) == 1:
                record.jira_epic_link_task_id = tasks

    @api.depends("jira_bind_ids.jira_parent_id.odoo_id")
    def _compute_jira_parent_task_id(self):
        for record in self:
            tasks = record.mapped("jira_bind_ids.jira_parent_id.odoo_id")
            if len(tasks) == 1:
                record.jira_parent_task_id = tasks

    @api.depends("jira_bind_ids.jira_key")
    def _compute_jira_issue_url(self):
        """Compute the external URL to JIRA.

        We assume that we have only one external record.
        """
        for record in self:
            if not record.jira_bind_ids:
                record.jira_issue_url = False
                continue
            main_binding = record.jira_bind_ids[0]
            record.jira_issue_url = main_binding.jira_issue_url

    def name_get(self):
        names = []
        for task in self:
            task_id, name = super(ProjectTask, task).name_get()[0]
            if task.jira_compound_key:
                name = "[{}] {}".format(task.jira_compound_key, name)
            names.append((task_id, name))
        return names

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        res = super().name_search(name, args, operator, limit)
        if not name:
            return res
        domain = [
            "|",
            ("jira_compound_key", "=ilike", name + "%"),
            ("id", "in", [x[0] for x in res]),
        ]
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = ["&", "!"] + domain[1:]
        return self.search(
            domain + (args or []),
            limit=limit,
        ).name_get()

    @api.model
    def _get_connector_jira_fields(self):
        return [
            "jira_bind_ids",
            "name",
            "date_deadline",
            "user_id",
            "description",
            "active",
            "project_id",
            "planned_hours",
            "stage_id",
        ]

    @api.model
    def _connector_jira_create_validate(self, vals):
        ProjectProject = self.env["project.project"]
        project_id = vals.get("project_id")
        if project_id:
            project_id = ProjectProject.sudo().browse(project_id)
            if (
                not self.env.context.get("connector_jira")
                and project_id.mapped("jira_bind_ids")._is_linked()
            ):
                raise exceptions.UserError(
                    _("Task can not be created in project linked to JIRA!")
                )

    def _connector_jira_write_validate(self, vals):
        if (
            not self.env.context.get("connector_jira")
            and self.mapped("jira_bind_ids")._is_linked()
        ):
            fields = list(vals.keys())
            self._update_cache(vals)
            new_values = self._convert_to_write(
                vals,
            )
            for old_values in self.read(fields, load="_classic_write"):
                old_values = self._convert_to_write(
                    old_values,
                )
                for field in self._get_connector_jira_fields():
                    if field not in fields:
                        continue
                    if new_values[field] == old_values[field]:
                        continue
                    raise exceptions.UserError(
                        _("Task linked to JIRA Issue can not be modified!")
                    )

    def _connector_jira_unlink_validate(self):
        if (
            not self.env.context.get("connector_jira")
            and self.mapped("jira_bind_ids")._is_linked()
        ):
            raise exceptions.UserError(
                _("Task linked to JIRA Issue can not be deleted!")
            )

    @api.model
    def create(self, vals):
        self._connector_jira_create_validate(vals)
        return super().create(vals)

    def write(self, vals):
        self._connector_jira_write_validate(vals)
        return super().write(vals)

    def unlink(self):
        self._connector_jira_unlink_validate()
        return super().unlink()


class TaskAdapter(Component):
    _name = "jira.project.task.adapter"
    _inherit = ["jira.webservice.adapter"]
    _apply_on = ["jira.project.task"]

    def read(self, id_, fields=None):
        # pylint: disable=W8106
        return self.get(id_, fields=fields).raw

    def get(self, id_, fields=None):
        with self.handle_404():
            return self.client.issue(id_, fields=fields, expand=["renderedFields"])

    def search(self, jql):
        # we need to have at least one field which is not 'id' or 'key'
        # due to this bug: https://github.com/pycontribs/jira/pull/289
        fields = "id,updated"
        issues = self.client.search_issues(jql, fields=fields, maxResults=None)
        return [issue.id for issue in issues]
