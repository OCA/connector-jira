# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging
import re
import tempfile

from odoo import _, api, exceptions, fields, models, tools
from odoo.osv import expression

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)

try:
    from jira import JIRAError
    from jira.utils import json_loads
except ImportError as err:
    _logger.debug(err)


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
        size=10,
    )  # limit on JIRA
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
        return [
            ("software", "Software"),
            ("business", "Business"),
        ]

    # Disable and implement the constraint jira_binding_uniq as python because
    # we need to override the in connector_jira_service_desk and it would try
    # to create it again at every update because of the base implementation
    # in the binding's parent model.
    def _add_sql_constraints(self):
        # we replace the sql constraint by a python one
        # to include the organizations
        for (key, definition, _msg) in self._sql_constraints:
            conname = "{}_{}".format(self._table, key)
            if key == "jira_binding_uniq":
                has_definition = tools.constraint_definition(
                    self.env.cr, self._table, conname
                )
                if has_definition:
                    tools.drop_constraint(self.env.cr, self._table, conname)
            else:
                tools.add_constraint(self.env.cr, self._table, conname, definition)
        return super()._add_sql_constraints()

    def _export_binding_domain(self):
        """Return the domain for the constraints on export bindings"""
        self.ensure_one()
        domain = [
            ("odoo_id", "=", self.odoo_id.id),
            ("backend_id", "=", self.backend_id.id),
            ("sync_action", "=", "export"),
        ]
        return domain

    @api.constrains("backend_id", "odoo_id", "sync_action")
    def _constrains_odoo_jira_sync_action_export_uniq(self):
        """Add a constraint on backend+odoo id for export action

        Only one binding can have the sync_action "export", as it pushes the
        name and key to Jira, we cannot export the same values to several
        projects.
        """
        for binding in self:
            export_bindings = self.with_context(active_test=False).search(
                self._export_binding_domain()
            )
            if len(export_bindings) > 1:
                raise exceptions.ValidationError(
                    _(
                        "Only one Jira binding can be configured with the Sync."
                        ' Action "Export" for a project.  "%s" already'
                        " has one."
                    )
                    % (binding.display_name,)
                )

    @api.constrains("backend_id", "external_id")
    def _constrains_jira_uniq(self):
        """Add a constraint on backend+jira id

        Defined as a python method rather than a postgres constraint
        in order to ease the override in connector_jira_servicedesk
        """
        for binding in self:
            if not binding.external_id:
                continue
            same_link_bindings = self.with_context(active_test=False).search(
                [
                    ("id", "!=", binding.id),
                    ("backend_id", "=", binding.backend_id.id),
                    ("external_id", "=", binding.external_id),
                ]
            )
            if same_link_bindings:
                raise exceptions.ValidationError(
                    _("The project %s is already linked with the same" " JIRA project.")
                    % (same_link_bindings.display_name)
                )

    @api.constrains("jira_key")
    def check_jira_key(self):
        for project in self:
            if not project.jira_key:
                continue
            if not self._jira_key_valid(project.jira_key):
                raise exceptions.ValidationError(
                    _("%s is not a valid JIRA Key") % project.jira_key
                )

    @api.onchange("backend_id")
    def onchange_project_backend_id(self):
        self.project_template = self.backend_id.project_template
        self.project_template_shared = self.backend_id.project_template_shared

    @staticmethod
    def _jira_key_valid(key):
        return bool(re.match(r"^[A-Z][A-Z0-9]{1,9}$", key))

    @api.constrains("project_template_shared")
    def check_project_template_shared(self):
        for binding in self:
            if not binding.project_template_shared:
                continue
            if not self._jira_key_valid(binding.project_template_shared):
                raise exceptions.ValidationError(
                    _("%s is not a valid JIRA Key") % binding.project_template_shared
                )

    def _is_linked(self):
        for project in self:
            if project.sync_action == "link":
                return True
        return False

    @api.model
    def create(self, values):
        record = super().create(values)
        record._ensure_jira_key()
        return record

    def write(self, values):
        if "project_template" in values:
            raise exceptions.UserError(_("The project template cannot be modified."))
        res = super().write(values)
        self._ensure_jira_key()
        return res

    def _ensure_jira_key(self):
        if self.env.context.get("connector_no_export"):
            return
        for record in self:
            if not record.jira_key:
                raise exceptions.UserError(
                    _("The JIRA Key is mandatory in order to link a project")
                )

    def unlink(self):
        if any(self.mapped("external_id")):
            raise exceptions.UserError(_("Exported project cannot be deleted."))
        return super().unlink()


class ProjectProject(models.Model):
    _inherit = "project.project"

    jira_bind_ids = fields.One2many(
        comodel_name="jira.project.project",
        inverse_name="odoo_id",
        copy=False,
        string="Project Bindings",
        context={"active_test": False},
    )
    jira_key = fields.Char(
        string="JIRA Key",
        compute="_compute_jira_key",
        store=True,
    )

    @api.depends("jira_bind_ids.jira_key")
    def _compute_jira_key(self):
        for project in self:
            keys = project.mapped("jira_bind_ids.jira_key")
            project.jira_key = ", ".join(keys)

    def name_get(self):
        names = []
        for project in self:
            project_id, name = super(ProjectProject, project).name_get()[0]
            if project.jira_key:
                name = "[{}] {}".format(project.jira_key, name)
            names.append((project_id, name))
        return names

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        res = super().name_search(name, args, operator, limit)
        if not name:
            return res
        domain = [
            "|",
            ("jira_key", "=ilike", name + "%"),
            ("id", "in", [x[0] for x in res]),
        ]
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = ["&", "!"] + domain[1:]
        return self.search(
            domain + (args or []),
            limit=limit,
        ).name_get()

    def create_and_link_jira(self):
        action_link = self.env.ref("connector_jira.open_project_link_jira")
        action = action_link.read()[0]
        action["context"] = dict(
            self.env.context,
            active_id=self.id,
            active_model=self._name,
        )
        return action


class ProjectAdapter(Component):

    _name = "jira.project.adapter"
    _inherit = ["jira.webservice.adapter"]
    _apply_on = ["jira.project.project"]

    def read(self, id_):
        # pylint: disable=W8106
        with self.handle_404():
            return self.get(id_).raw

    def get(self, id_):
        with self.handle_404():
            return self.client.project(id_)

    def write(self, id_, values):
        super().write(id_, values)
        with self.handle_404():
            return self.get(id_).update(values)

    def create(self, key=None, name=None, template_name=None, values=None):
        super().create(key=key, name=name, template_name=template_name, values=values)
        project = self.client.create_project(
            key=key,
            name=name,
            template_name=template_name,
        )
        if values:
            project.update(values)
        return project

    def create_shared(self, key=None, name=None, shared_key=None, lead=None):
        assert key and name and shared_key
        # There is no public method for creating a shared project:
        # https://jira.atlassian.com/browse/JRA-45929
        # People found a private method for doing so, which is explained on:
        # https://jira.atlassian.com/browse/JRASERVER-27256

        try:
            project = self.read(shared_key)
            project_id = project["id"]
        except JIRAError as err:
            if err.status_code == 404:
                raise exceptions.UserError(
                    _('Project template with key "%s" not found.') % shared_key
                ) from err
            else:
                raise

        url = (
            self.client._options["server"]
            + "/rest/project-templates/1.0/createshared/%s" % project_id
        )
        payload = {
            "name": name,
            "key": key,
            "lead": lead,
        }

        r = self.client._session.post(url, data=json.dumps(payload))
        if r.status_code == 200:
            r_json = json_loads(r)
            return r_json

        f = tempfile.NamedTemporaryFile(
            suffix=".html",
            prefix="python-jira-error-create-shared-project-",
            delete=False,
        )
        f.write(r.text)

        if self.logging:
            logging.error(
                "Unexpected result while running create shared project."
                "Server response saved in %s for further investigation "
                "[HTTP response=%s]." % (f.name, r.status_code)
            )
        return False
