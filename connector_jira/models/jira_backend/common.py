# Copyright: 2015 LasLabs, Inc.
# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
import urllib.parse
from contextlib import closing, contextmanager
from datetime import datetime

import jwt
import psycopg2
import pytz
import requests
from atlassian_jwt import url_utils

import odoo
from odoo import _, api, exceptions, fields, models, tools
from odoo.tools import config

from odoo.addons.component.core import Component

from ...fields import MilliDatetime

_logger = logging.getLogger(__name__)

JIRA_TIMEOUT = 30  # seconds

try:
    from jira import JIRA, JIRAError
except ImportError as err:
    _logger.debug(err)

try:
    pass
except ImportError as err:
    _logger.debug(err)


@contextmanager
def new_env(env):
    registry = odoo.registry(env.cr.dbname)
    with closing(registry.cursor()) as cr:
        new_env = api.Environment(cr, env.uid, env.context)
        try:
            yield new_env
        except Exception:
            cr.rollback()
            raise
        else:
            if not tools.config["test_enable"]:
                cr.commit()  # pylint: disable=invalid-commit


class JiraBackend(models.Model):
    _name = "jira.backend"
    _description = "Jira Backend"
    _inherit = "connector.backend"

    RSA_BITS = 4096
    RSA_PUBLIC_EXPONENT = 65537
    KEY_LEN = 255  # 255 == max Atlassian db col len

    # def _default_consumer_key(self):
    #     """Generate a rnd consumer key of length self.KEY_LEN"""
    #     return binascii.hexlify(urandom(self.KEY_LEN))[: self.KEY_LEN]

    uri = fields.Char(
        string="Jira URI",
        readonly=True,
        help="the value is provided when the app is installed on Jira Cloud.",
    )
    name = fields.Char(
        size=60,
        help="Display name of the app on the Atlassian Marketplace. Max 60 chars.",
    )
    app_descriptor_url = fields.Char(
        string="App Descriptor URL",
        help="URL to use when registering the backend as an app on the marketplace",
        compute="_compute_app_descriptor_url",
    )
    display_url = fields.Char(
        help="Url used for the Jira app in messages", readonly=True
    )
    application_key = fields.Char(
        compute="_compute_application_key",
        store=True,
        help="The name that will be used as application key to register the app on the"
        " Atlassian marketplace website.\n"
        "It has to be unique among all apps on the marketplace.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    worklog_fallback_project_id = fields.Many2one(
        comodel_name="project.project",
        string="Fallback for Worklogs",
        help="Worklogs which could not be linked to any project "
        "will be created in this project. Worklogs landing in "
        "the fallback project can be reassigned to the correct "
        "project by: 1. linking the expected project with the Jira one, "
        "2. using 'Refresh Worklogs from Jira' on the timesheet lines.",
    )
    worklog_date_timezone_mode = fields.Selection(
        selection=[
            ("naive", "As-is (naive)"),
            ("user", "Jira User"),
            ("specific", "Specific"),
        ],
        default="naive",
        help=(
            "Worklog/Timesheet date timezone modes:\n"
            " - As-is (naive): ignore timezone information\n"
            " - Jira User: use author's timezone\n"
            " - Specific: use pre-configured timezone\n"
        ),
    )
    worklog_date_timezone = fields.Selection(
        selection=lambda self: [(x, x) for x in pytz.all_timezones],
        default=(lambda self: self._context.get("tz") or self.env.user.tz or "UTC"),
    )
    state = fields.Selection(
        selection=[
            # ("authenticate", "Authenticate"),
            ("setup", "Setup"),
            ("running", "Running"),
        ],
        default="setup",
        required=True,
        readonly=True,
        help="State of the Backend.\n"
        "Setup: in this state you can register the backend on "
        "https://marketplace.atlassian.com/ as an app, using the app descriptor url.\n"
        "Running: when you have installed the backend on a Jira cloud instance "
        "(transition is automatic).",
    )
    private_key = fields.Char(
        readonly=True,
        groups="connector.group_connector_manager",
        help="The shared secret for JWT, provided at app installation",
    )
    public_key = fields.Text(
        readonly=True, help="The Client Key for JWT, provided at app installation"
    )

    verify_ssl = fields.Boolean(default=True, string="Verify SSL?")

    project_template = fields.Selection(
        selection="_selection_project_template",
        string="Default Project Template",
        default="Scrum software development",
        required=True,
    )
    project_template_shared = fields.Char(
        string="Default Shared Template Key",
    )

    import_project_task_from_date = fields.Datetime(
        compute="_compute_last_import_date",
        inverse="_inverse_import_project_task_from_date",
        string="Import Project Tasks from date",
    )
    import_project_task_force = fields.Boolean()

    import_analytic_line_from_date = fields.Datetime(
        compute="_compute_last_import_date",
        inverse="_inverse_import_analytic_line_from_date",
        string="Import Worklogs from date",
    )
    import_analytic_line_force = fields.Boolean()

    delete_analytic_line_from_date = fields.Datetime(
        compute="_compute_last_import_date",
        inverse="_inverse_delete_analytic_line_from_date",
        string="Delete Extra Worklogs from date",
    )

    issue_type_ids = fields.One2many(
        comodel_name="jira.issue.type",
        inverse_name="backend_id",
        string="Issue Types",
        readonly=True,
    )

    epic_link_field_name = fields.Char(
        string="Epic Link Field",
        help="The 'Epic Link' field on JIRA is a custom field. "
        "The name of the field is something like 'customfield_10002'. ",
    )
    epic_name_field_name = fields.Char(
        string="Epic Name Field",
        help="The 'Epic Name' field on JIRA is a custom field. "
        "The name of the field is something like 'customfield_10003'. ",
    )
    epic_link_on_epic = fields.Boolean(
        help="Epics on JIRA cannot be linked to another epic. Check this box"
        "to fill the epic field with itself on Odoo.",
    )

    # TODO: use something better to show this info
    # For instance, we could use web_notify to simply show a system msg.
    report_user_sync = fields.Html(readonly=True)

    @api.model_create_multi
    @api.returns("self", lambda value: value.id)
    def create(self, vals_list):
        records = super().create(vals_list)
        records._compute_application_key()
        return records

    def _compute_application_key(self):
        db_name = config["db_name"]
        for rec in self:
            rec.application_key = f"odoo-jira-connector-{db_name}-{rec.id}"

    def _compute_app_descriptor_url(self):
        base_url = self._get_base_url()

        for rec in self:
            rec.app_descriptor_url = f"{base_url}/jira/{rec.id}/app-descriptor.json"

    @api.model
    def _selection_project_template(self):
        return [
            ("Scrum software development", "Scrum software development (Software)"),
            ("Kanban software development", "Kanban software development (Software)"),
            ("Basic software development", "Basic software development (Software)"),
            ("Project management", "Project management (Business)"),
            ("Task management", "Task management (Business)"),
            ("Process management", "Process management (Business)"),
            ("shared", "From a shared template"),
        ]

    @api.constrains("project_template_shared")
    def check_jira_key(self):
        for backend in self:
            if not backend.project_template_shared:
                continue
            valid = self.env["jira.project.project"]._jira_key_valid
            if not valid(backend.project_template_shared):
                raise exceptions.ValidationError(
                    _("%s is not a valid JIRA Key") % backend.project_template_shared
                )

    @api.depends()
    def _compute_last_import_date(self):
        for backend in self:
            self.env.cr.execute(
                """
                SELECT from_date_field, last_timestamp
                FROM jira_backend_timestamp
                WHERE backend_id = %s""",
                (backend.id,),
            )
            rows = self.env.cr.dictfetchall()
            for row in rows:
                field = row["from_date_field"]
                if field in self._fields:
                    backend[field] = row["last_timestamp"]
            if not rows:
                backend.update(
                    {
                        "import_project_task_from_date": False,
                        "import_analytic_line_from_date": False,
                        "delete_analytic_line_from_date": False,
                    }
                )

    def _inverse_date_fields(self, field_name, component_usage):
        for rec in self:
            ts_model = self.env["jira.backend.timestamp"]
            timestamp = ts_model._timestamp_for_field(rec, field_name, component_usage)
            if not timestamp._lock():
                raise exceptions.UserError(
                    _(
                        "The synchronization timestamp is currently locked, "
                        "probably due to an ongoing synchronization."
                    )
                )
            value = getattr(rec, field_name)
            # As the timestamp field is using MilliDatetime, we lose
            # the milliseconds precision when a user writes a new
            # date on the backend. This is not really an issue as we
            # expect mostly to use the milliseconds precision for
            # the dates coming from the Jira webservices (they use
            # milliseconds unix timestamp on some -only some- methods)
            if not value:
                value = datetime.fromtimestamp(0)
            timestamp._update_timestamp(value)

    def _inverse_import_project_task_from_date(self):
        self._inverse_date_fields(
            "import_project_task_from_date",
            "timestamp.batch.importer",
        )

    def _inverse_import_analytic_line_from_date(self):
        self._inverse_date_fields(
            "import_analytic_line_from_date",
            "timestamp.batch.importer",
        )

    def _inverse_delete_analytic_line_from_date(self):
        self._inverse_date_fields(
            "delete_analytic_line_from_date",
            "timestamp.batch.deleter",
        )

    def _run_background_from_date(
        self, model, from_date_field, component_usage, force=False
    ):
        """Import records from a date

        Create jobs and update the sync timestamp in a savepoint; if a
        concurrency issue arises, it will be logged and rollbacked silently.
        """
        self.ensure_one()
        ts_model = self.env["jira.backend.timestamp"]
        timestamp = ts_model._timestamp_for_field(
            self,
            from_date_field,
            component_usage,
        )
        self.env[model].with_delay(priority=9).run_batch_timestamp(
            self, timestamp, force=force
        )

    # XXX check this
    def button_setup(self):
        self.state_running()

    def activate_epic_link(self):
        self.ensure_one()
        with self.work_on("jira.backend") as work:
            adapter = work.component(usage="backend.adapter")
            jira_fields = adapter.list_fields()
            for field in jira_fields:
                custom_ref = field.get("schema", {}).get("custom")
                if custom_ref == "com.pyxis.greenhopper.jira:gh-epic-link":
                    self.epic_link_field_name = field["id"]
                elif custom_ref == "com.pyxis.greenhopper.jira:gh-epic-label":
                    self.epic_name_field_name = field["id"]

    # XXX check this
    def state_setup(self):
        for backend in self:
            if backend.state == "authenticate":
                backend.state = "setup"

    # XXX check this
    def state_running(self):
        for backend in self:
            if backend.state == "setup":
                backend.state = "running"

    @api.onchange("worklog_date_timezone_mode")
    def _onchange_worklog_date_import_timezone_mode(self):
        for jira_backend in self:
            if jira_backend.worklog_date_timezone_mode == "specific":
                continue
            jira_backend.worklog_date_timezone = False

    def check_connection(self):
        self.ensure_one()
        try:
            self.get_api_client().myself()
        except (ValueError, requests.exceptions.ConnectionError) as err:
            raise exceptions.UserError(_("Failed to connect (%s)") % (err,)) from err
        except JIRAError as err:
            raise exceptions.UserError(
                _("Failed to connect (%s)") % (err.text,)
            ) from err
        raise exceptions.UserError(_("Connection successful"))

    def import_project_task(self):
        self._run_background_from_date(
            "jira.project.task",
            "import_project_task_from_date",
            "timestamp.batch.importer",
            force=self.import_project_task_force,
        )
        return True

    def import_analytic_line(self):
        self._run_background_from_date(
            "jira.account.analytic.line",
            "import_analytic_line_from_date",
            "timestamp.batch.importer",
            force=self.import_analytic_line_force,
        )
        return True

    def delete_analytic_line(self):
        self._run_background_from_date(
            "jira.account.analytic.line",
            "delete_analytic_line_from_date",
            "timestamp.batch.deleter",
        )
        return True

    def import_res_users(self):
        self.report_user_sync = None
        result = self.env["res.users"].search([]).link_with_jira(backends=self)
        for __, bknd_result in result.items():
            if bknd_result.get("error"):
                self.report_user_sync = self.env["ir.ui.view"]._render_template(
                    "connector_jira.backend_report_user_sync",
                    {"backend": self, "result": bknd_result},
                )
        return True

    def get_user_resolution_order(self):
        return [
            "email",
        ]

    def import_issue_type(self):
        self.env["jira.issue.type"].import_batch(self)
        return True

    def get_api_client(self):
        self.ensure_one()
        # tokens are only readable by connector managers
        backend = self.sudo()

        options = {
            "server": backend.uri,
            "verify": backend.verify_ssl,
        }
        jwt = {
            "secret": backend.private_key,
            "payload": {
                "iss": self.application_key,  # application key in the app descriptor
            },
        }
        return JIRA(
            options=options, jwt=jwt, timeout=JIRA_TIMEOUT, get_server_info=False
        )

    @api.model
    def _scheduler_import_project_task(self):
        backends = self.search([("state", "=", "running")])
        for backend in backends:
            backend.import_project_task()

    @api.model
    def _scheduler_import_res_users(self):
        backends = self.search([("state", "=", "running")])
        for backend in backends:
            backend.import_res_users()

    @api.model
    def _scheduler_import_analytic_line(self):
        backends = self.search([("state", "=", "running")])
        for backend in backends:
            backend.search([]).import_analytic_line()

    @api.model
    def _scheduler_delete_analytic_line(self):
        backends = self.search([("state", "=", "running")])
        for backend in backends:
            backend.search([]).delete_analytic_line()

    def make_issue_url(self, jira_issue_id):
        return urllib.parse.urljoin(self.uri, f"/browse/{jira_issue_id}")

    def _get_base_url(self):
        fqdn = self.env["ir.config_parameter"].get_param("web.base.url", "")
        if "://" in fqdn:
            fqdn = fqdn.split("://", maxsplit=1)[-1]
        base_url = "https://" + fqdn
        return base_url

    def _get_app_descriptor(self):
        self.ensure_one()
        base_url = self._get_base_url()
        return {
            "key": self.application_key,
            "name": self.name,
            "description": "Connect your Odoo instance to Jira, manage linking "
            "Jira Cards with Odoo projects and tasks, and Tempo worklogs with Odoo "
            f"Timesheets.\nBuilt for {self.name} ({self.application_key})",
            "vendor": {"name": "Camptocamp", "url": "https://www.camptocamp.com/"},
            "baseUrl": base_url,
            "authentication": {"type": "jwt"},
            "lifecycle": {
                "installed": f"{base_url}/jira/{self.id}/installed",
                "uninstalled": f"{base_url}/jira/{self.id}/uninstalled",
                "enabled": f"{base_url}/jira/{self.id}/enabled",
                "disabled": f"{base_url}/jira/{self.id}/disabled",
            },
            "modules": {
                "webhooks": [
                    {
                        "event": "jira:issue_created",
                        "url": f"{base_url}/connector_jira/{self.id}/webhooks/issue",
                    },
                    {
                        "event": "jira:issue_deleted",
                        "url": f"{base_url}/connector_jira/{self.id}/webhooks/issue",
                    },
                    {
                        "event": "jira:issue_updated",
                        "url": f"{base_url}/connector_jira/{self.id}/webhooks/issue",
                    },
                    {
                        "event": "worklog_updated",
                        "url": f"{base_url}/connector_jira/{self.id}/webhooks/worklog",
                    },
                    {
                        "event": "worklog_deleted",
                        "url": f"{base_url}/connector_jira/{self.id}/webhooks/worklog",
                    },
                    {
                        "event": "worklog_created",
                        "url": f"{base_url}/connector_jira/{self.id}/webhooks/worklog",
                    },
                ],
            },
            "apiMigrations": {"gdpr": True, "signed-install": True},
            "scopes": ["project_admin"],
        }

    def _install_app(self, payload):
        """
        When we receive an 'installed' notification, we create a backend record with
        the proper settings.

        payload keys:

        'key': 'odoo-connector-jira'
        'clientKey':  Identifying key but could vary WTF
        'publicKey': DEPRECATED DO NOT USE,
        'sharedSecret': Use to sign JWT tokens
        'serverVersion': DEPRECATED
        'pluginsVersion': DEPRECATED
        'baseUrl': URL prefix for this Atlassian product instance. All of its REST
            endpoints begin with this `baseUrl`. Do not use the `baseUrl` as an
            identifier for the Atlassian product as this value may not be unique.
        'displayUrl': If the Atlassian product instance has an associated custom
            domain, this is the URL through which users will access the product.
        'productType': 'jira',
        'description': 'Atlassian JIRA at https: //testcamptocamp.atlassian.net ',
        'eventType': 'installed',

        """
        self.ensure_one()
        self.write(self._prepare_backend_values(payload))
        _logger.info("Updated Jira backend for uri %s", self.uri)
        assert self.private_key
        return self.id

    def _prepare_backend_values(self, payload):
        values = {
            "display_url": payload.get("displayUrl", False),
            "uri": payload.get("baseUrl", False),
            "state": "setup",
            "public_key": payload.get("clientKey", False),
        }
        if "sharedSecret" in payload:
            values["private_key"] = payload["sharedSecret"]
        return values

    def _uninstall_app(self, payload):
        self.ensure_one()
        # wait for disabled to complete
        self.env.cr.execute(
            "SELECT id from jira_backend WHERE id = %s FOR UPDATE",
            (self.id,),
        )
        self.write(
            {
                "public_key": False,
                "private_key": False,
                "state": "setup",
            }
        )
        _logger.info("Uninstalled Jira backend for uri %s", self.uri)
        return "ok"

    def _enable_app(self, payload):
        self.ensure_one()
        values = self._prepare_backend_values(payload)
        values["state"] = "running"
        self.write(values)
        _logger.info("enable %s -> %s", self.ids, values)
        _logger.info("Enabled Jira backend for uri %s", self.mapped("uri"))
        return "ok"

    def _disable_app(self, payload):
        self.ensure_one()
        self.env.cr.execute(
            "SELECT id from jira_backend WHERE id = %s FOR UPDATE",
            (self.id,),
        )
        values = self._prepare_backend_values(payload)
        values["state"] = "setup"
        _logger.info("disable %s -> %s", self.ids, values)
        self.write(values)
        _logger.info("Disabled Jira backend for uri %s", self.mapped("uri"))
        return "ok"

    def _validate_jwt(self, authorization_header, query_url=None):
        """validation if the JSON Web Token

        Use the algorithm provided by the atlassan module to compute the 'iss' hash
        from the URL and compare it to the value in the token, in addition to the
        standard claims checks.
        """
        self.ensure_one()
        assert authorization_header.startswith(
            "JWT "
        ), "unexpected content in Authorization header"
        jwt_token = authorization_header[4:]
        # see https://developer.atlassian.com/cloud/jira/software/understanding-jwt/
        # for more info
        decoded = jwt.decode(
            jwt_token,
            self.private_key,
            algorithms=["HS256"],
            # audience=self._get_base_url(),
            issuer=self.public_key,
            options={
                "require": [
                    "iss",  # issuer of the claim
                    "exp",  # expiration time
                    "iat",  # issued at time
                    "qsh",  # query string hash
                    # sub: is optional
                    # aud: is optional
                    # context: is optional
                ]
            },
        )
        if query_url is not None:
            expected_hash = url_utils.hash_url("POST", query_url)
            if decoded["iss"] != expected_hash:
                return False
        return True


class JiraBackendTimestamp(models.Model):
    _name = "jira.backend.timestamp"
    _description = "Jira Backend Import Timestamps"

    backend_id = fields.Many2one(
        comodel_name="jira.backend",
        string="Jira Backend",
        required=True,
    )
    from_date_field = fields.Char(
        required=True,
    )
    # For worklogs, jira allows to work with milliseconds
    # unix timestamps, we keep this precision by using a new type
    # of field. The ORM values for this field are Unix timestamps the
    # same way Jira use them: unix timestamp as integer multiplied * 1000
    # to keep the milli precision with 3 digits (example 1554318348000).
    last_timestamp = MilliDatetime(
        string="Last Timestamp",
        required=True,
    )

    # The content of this field must match to the "usage" of a component.
    # The method JiraBinding.run_batch_timestamp() will find the matching
    # component for the model and call "run()" on it.
    component_usage = fields.Char(
        required=True,
        help="Used by the connector to find which component "
        "execute the batch import (technical).",
    )

    _sql_constraints = [
        (
            "timestamp_field_uniq",
            "unique(backend_id, from_date_field, component_usage)",
            "A timestamp already exists.",
        ),
    ]

    @api.model
    def _timestamp_for_field(self, backend, field_name, component_usage):
        """Return the timestamp for a field"""
        timestamp = self.search(
            [
                ("backend_id", "=", backend.id),
                ("from_date_field", "=", field_name),
                ("component_usage", "=", component_usage),
            ]
        )
        if not timestamp:
            timestamp = self.env["jira.backend.timestamp"].create(
                {
                    "backend_id": backend.id,
                    "from_date_field": field_name,
                    "component_usage": component_usage,
                    "last_timestamp": datetime.fromtimestamp(0),
                }
            )
        return timestamp

    def _update_timestamp(self, timestamp):
        self.ensure_one()
        self.last_timestamp = timestamp

    def _lock(self):
        """Update the timestamp for a synchro

        thus, we prevent 2 synchros to be launched at the same time.
        The lock is released at the commit of the transaction.

        Return True if the lock could be acquired.
        """
        self.ensure_one()
        query = """
               SELECT id FROM jira_backend_timestamp
               WHERE id = %s
               FOR UPDATE NOWAIT
            """
        try:
            self.env.cr.execute(query, (self.id,))
        except psycopg2.OperationalError:
            return False
        row = self.env.cr.fetchone()
        return bool(row)


class BackendAdapter(Component):
    _name = "jira.backend.adapter"
    _inherit = "jira.webservice.adapter"
    _apply_on = ["jira.backend"]

    webhook_base_path = "{server}/rest/webhooks/1.0/{path}"

    def list_fields(self):
        return self.client._get_json("field")
