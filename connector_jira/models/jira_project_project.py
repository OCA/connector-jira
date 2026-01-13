# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import re

from odoo import _, api, exceptions, fields, models, tools


class JiraProjectProject(models.Model):
    _name = "jira.project.project"
    _inherit = ["jira.binding", "jira.project.base.mixin"]
    _inherits = {"project.project": "odoo_id"}
    _description = "Jira Projects"

    odoo_id = fields.Many2one(
        comodel_name="project.project",
        string="Project",
        required=True,
        index=True,
        ondelete="restrict",
    )
    project_type = fields.Selection(selection="_selection_project_type")

    @api.model
    def _selection_project_type(self):
        return [("software", "Software"), ("business", "Business")]

    # Disable and implement the constraint jira_binding_uniq as python because
    # we need to override it in connector_jira_service_desk, and it would try
    # to create it again at every update because of the base implementation
    # in the binding's parent model.
    def _add_sql_constraints(self):
        # we replace the sql constraint by a python one
        # to include the organizations
        for key, definition, __ in self._sql_constraints:
            conname = f"{self._table}_{key}"
            if key == "jira_binding_uniq":
                if tools.constraint_definition(self.env.cr, self._table, conname):
                    tools.drop_constraint(self.env.cr, self._table, conname)
            else:
                tools.add_constraint(self.env.cr, self._table, conname, definition)
        return super()._add_sql_constraints()

    def _export_binding_domain(self):
        """Return the domain for the constraints on export bindings"""
        self.ensure_one()
        return [
            ("odoo_id", "=", self.odoo_id.id),
            ("backend_id", "=", self.backend_id.id),
            ("sync_action", "=", "export"),
        ]

    @api.constrains("backend_id", "odoo_id", "sync_action")
    def _constrains_odoo_jira_sync_action_export_uniq(self):
        """Add a constraint on backend+odoo id for export action

        Only one binding can have the sync_action "export", as it pushes the
        name and key to Jira, we cannot export the same values to several
        projects.
        """
        for binding in self:
            domain = binding._export_binding_domain()
            export_bindings = self.with_context(active_test=False).search(domain)
            if len(export_bindings) > 1:
                raise exceptions.ValidationError(
                    _(
                        "Only one Jira binding can be configured with the Sync. Action"
                        ' "Export" for a project. "%s" already has one.',
                        binding.display_name,
                    )
                )

    @api.constrains("backend_id", "external_id")
    def _constrains_jira_uniq(self):
        """Add a constraint on backend+jira id

        Defined as a python method rather than a postgres constraint
        in order to ease the override in connector_jira_servicedesk
        """
        for binding in self.filtered("external_id"):
            same_link_bindings = self.with_context(active_test=False).search(
                [
                    ("id", "!=", binding.id),
                    ("backend_id", "=", binding.backend_id.id),
                    ("external_id", "=", binding.external_id),
                ]
            )
            if same_link_bindings:
                raise exceptions.ValidationError(
                    _(
                        "The project %s is already linked with the same JIRA project.",
                        same_link_bindings.display_name,
                    )
                )

    @api.constrains("jira_key")
    def _check_jira_key(self):
        for key in self.filtered("jira_key").mapped("jira_key"):
            if not self._jira_key_valid(key):
                raise exceptions.ValidationError(_("%s is not a valid JIRA Key", key))

    @api.onchange("backend_id")
    def onchange_project_backend_id(self):
        self.project_template = self.backend_id.project_template
        self.project_template_shared = self.backend_id.project_template_shared

    @staticmethod
    def _jira_key_valid(key):
        return bool(re.match(r"^[A-Z][A-Z0-9]{1,9}$", key))

    @api.constrains("project_template_shared")
    def _check_project_template_shared(self):
        for tmpl in set(self.mapped("project_template_shared")):
            if tmpl and not self._jira_key_valid(tmpl):
                raise exceptions.ValidationError(_("%s is not a valid JIRA Key", tmpl))

    def _is_linked(self):
        return bool(self) and any(p.sync_action == "link" for p in self)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_jira_key()
        return records

    def write(self, values):
        if "project_template" in values:
            raise exceptions.UserError(_("The project template cannot be modified."))
        res = super().write(values)
        self._ensure_jira_key()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_unless_exported(self):
        if any(self.mapped("external_id")):
            raise exceptions.UserError(_("Exported project cannot be deleted."))

    def _ensure_jira_key(self):
        if self.env.context.get("connector_no_export") or all(r.jira_key for r in self):
            return
        raise exceptions.UserError(_("JIRA Key is mandatory to link a project"))
