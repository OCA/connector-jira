# Copyright 2016-2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, exceptions, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.model
    def _register_hook(self):
        # OVERRIDE: add ``jira_compound_key`` to class attribute ``_rec_names_search``,
        # allowing using ``_rec_name`` too in method ``name_search()``
        cls = type(self)
        search_fnames = list(cls._rec_names_search or [])
        search_fnames.insert(0, "jira_compound_key")
        if cls._rec_name and cls._rec_name not in search_fnames:
            search_fnames.append(cls._rec_name)
        cls._rec_names_search = search_fnames
        return super()._register_hook()

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._connector_jira_create_validate(vals)
        return super().create(vals_list)

    @api.model
    def _connector_jira_create_validate(self, vals):
        project_id = vals.get("project_id")
        if project_id:
            project = self.env["project.project"].sudo().browse(project_id).exists()
            if (
                not self.env.context.get("connector_jira")
                and project.jira_bind_ids._is_linked()
            ):
                raise exceptions.UserError(
                    _("Task can not be created in project linked to JIRA!")
                )

    def write(self, vals):
        self._connector_jira_write_validate(vals)
        return super().write(vals)

    def _connector_jira_write_validate(self, vals):
        if (
            not self.env.context.get("connector_jira")
            and self.jira_bind_ids._is_linked()
        ):
            new_values = self._convert_to_write(vals)
            for old_values in self.read(list(vals.keys()), load="_classic_write"):
                old_values.pop("id", None)
                old_values = self._convert_to_write(old_values)
                for field in self._get_connector_jira_fields():
                    if field in vals and new_values[field] != old_values[field]:
                        raise exceptions.UserError(
                            _("Task linked to JIRA Issue can not be modified!")
                        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_records_are_linked(self):
        if (
            not self.env.context.get("connector_jira")
            and self.jira_bind_ids._is_linked()
        ):
            raise exceptions.UserError(
                _("Task linked to JIRA Issue can not be deleted!")
            )

    @api.depends("jira_bind_ids.jira_issue_type_id.name")
    def _compute_jira_issue_type(self):
        for record in self:
            types = record.jira_bind_ids.jira_issue_type_id.mapped("name")
            record.jira_issue_type = ",".join([t for t in types if t])

    @api.depends("jira_bind_ids.jira_key")
    def _compute_jira_compound_key(self):
        for record in self:
            keys = record.jira_bind_ids.mapped("jira_key")
            record.jira_compound_key = ",".join([k for k in keys if k])

    @api.depends("jira_bind_ids.jira_epic_link_id.odoo_id")
    def _compute_jira_epic_link_task_id(self):
        self.jira_epic_link_task_id = False
        for record in self:
            tasks = record.jira_bind_ids.jira_epic_link_id.odoo_id
            if len(tasks) == 1:
                record.jira_epic_link_task_id = tasks

    @api.depends("jira_bind_ids.jira_parent_id.odoo_id")
    def _compute_jira_parent_task_id(self):
        self.jira_parent_task_id = False
        for record in self:
            tasks = record.jira_bind_ids.jira_parent_id.odoo_id
            if len(tasks) == 1:
                record.jira_parent_task_id = tasks

    @api.depends("jira_bind_ids.jira_issue_url")
    def _compute_jira_issue_url(self):
        """Compute the external URL to JIRA.

        We assume that we have only one external record.
        """
        for record in self:
            main_binding = record.jira_bind_ids[:1]
            record.jira_issue_url = main_binding.jira_issue_url or ""

    # pylint: disable=W8110
    @api.depends("jira_compound_key")
    def _compute_display_name(self):
        super()._compute_display_name()
        for task in self.filtered("jira_compound_key"):
            task.display_name = f"[{task.jira_compound_key}] {task.display_name}"

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
            "allocated_hours",
            "stage_id",
        ]

    def create_and_link_jira(self):
        self.ensure_one()
        backends = self.project_id.jira_bind_ids.backend_id
        xmlid = "connector_jira.open_task_link_jira"
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        action["context"] = dict(
            self.env.context,
            default_task_id=self.id,
            default_linked_backend_ids=[fields.Command.set(backends.ids)],
            default_backend_id=backends.id if len(backends) == 1 else False,
        )
        return action
