# Copyright: 2015 LasLabs, Inc.
# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import binascii
import json
import logging
import urllib.parse
from contextlib import closing, contextmanager
from datetime import datetime
from os import urandom

import psycopg2
import pytz
import requests

import odoo
from odoo import _, api, exceptions, fields, models, tools

from odoo.addons.component.core import Component

from ...fields import MilliDatetime

_logger = logging.getLogger(__name__)

JIRA_TIMEOUT = 30  # seconds

try:
    from jira import JIRA, JIRAError
    from jira.utils import json_loads
except ImportError as err:
    _logger.debug(err)

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
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

    def _default_consumer_key(self):
        """Generate a rnd consumer key of length self.KEY_LEN"""
        return binascii.hexlify(urandom(self.KEY_LEN))[: self.KEY_LEN]

    uri = fields.Char(string="Jira URI", required=True)
    name = fields.Char()
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
            ("authenticate", "Authenticate"),
            ("setup", "Setup"),
            ("running", "Running"),
        ],
        default="authenticate",
        required=True,
        readonly=True,
    )
    private_key = fields.Text(
        readonly=True,
        groups="connector.group_connector_manager",
    )
    public_key = fields.Text(readonly=True)
    consumer_key = fields.Char(
        default=lambda self: self._default_consumer_key(),
        readonly=True,
        groups="connector.group_connector_manager",
    )

    access_token = fields.Char(
        readonly=True,
        groups="connector.group_connector_manager",
    )
    access_secret = fields.Char(
        readonly=True,
        groups="connector.group_connector_manager",
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

    use_webhooks = fields.Boolean(
        readonly=True,
        help="Webhooks need to be configured on the Jira instance. "
        "When activated, synchronization from Jira is blazing fast. "
        "It can be activated only on one Jira backend at a time. ",
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

    odoo_webhook_base_url = fields.Char(
        string="Base Odoo URL for Webhooks",
        default=lambda self: self._default_odoo_webhook_base_url(),
    )
    webhook_issue_jira_id = fields.Char()
    webhook_worklog_jira_id = fields.Char()
    # TODO: use something better to show this info
    # For instance, we could use web_notify to simply show a system msg.
    report_user_sync = fields.Html(readonly=True)

    @api.model
    def _default_odoo_webhook_base_url(self):
        params = self.env["ir.config_parameter"]
        return params.get_param("web.base.url", "")

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

    @api.constrains("use_webhooks")
    def _check_use_webhooks_unique(self):
        if len(self.search([("use_webhooks", "=", True)])) > 1:
            raise exceptions.ValidationError(
                _("Only one backend can listen to webhooks")
            )

    @api.model
    def create(self, values):
        record = super().create(values)
        record.create_rsa_key_vals()
        return record

    def create_rsa_key_vals(self):
        """Create public/private RSA keypair"""
        for backend in self:
            private_key = rsa.generate_private_key(
                public_exponent=self.RSA_PUBLIC_EXPONENT,
                key_size=self.RSA_BITS,
                backend=default_backend(),
            )
            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
            public_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            backend.write({"private_key": pem, "public_key": public_pem})

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

    def state_setup(self):
        for backend in self:
            if backend.state == "authenticate":
                backend.state = "setup"

    def state_running(self):
        for backend in self:
            if backend.state == "setup":
                backend.state = "running"

    def create_webhooks(self):
        self.ensure_one()
        other_using_webhook = self.search(
            [("use_webhooks", "=", True), ("id", "!=", self.id)]
        )
        if other_using_webhook:
            raise exceptions.UserError(
                _(
                    "Only one JIRA backend can use the webhook at a time. "
                    'You must disable them on the backend "%s" before '
                    "activating them here."
                )
                % (other_using_webhook.name,)
            )

        # open a new cursor because we'll commit after the creations
        # to be sure to keep the webhook ids
        with new_env(self.env) as env:
            backend = env[self._name].browse(self.id)
            base_url = backend.odoo_webhook_base_url
            if not base_url:
                raise exceptions.UserError(_("The Odoo Webhook base URL must be set."))

            with self.work_on("jira.backend") as work:
                backend.use_webhooks = True

                adapter = work.component(usage="backend.adapter")
                # TODO: we could update the JQL of the webhook
                # each time a new project is sync'ed, so we would
                # filter out the useless events
                url = urllib.parse.urljoin(base_url, "/connector_jira/webhooks/issue")
                webhook = adapter.create_webhook(
                    name="Odoo Issues",
                    url=url,
                    events=[
                        "jira:issue_created",
                        "jira:issue_updated",
                        "jira:issue_deleted",
                    ],
                )
                # the only place where to find the hook id is in
                # the 'self' url, looks like
                # u'http://jira:8080/rest/webhooks/1.0/webhook/5'
                webhook_id = webhook["self"].split("/")[-1]
                backend.webhook_issue_jira_id = webhook_id
                if not tools.config["test_enable"]:
                    env.cr.commit()  # pylint: disable=invalid-commit

                url = urllib.parse.urljoin(base_url, "/connector_jira/webhooks/worklog")
                webhook = adapter.create_webhook(
                    name="Odoo Worklogs",
                    url=url,
                    events=["worklog_created", "worklog_updated", "worklog_deleted"],
                )
                webhook_id = webhook["self"].split("/")[-1]
                backend.webhook_worklog_jira_id = webhook_id
                if not tools.config["test_enable"]:
                    env.cr.commit()  # pylint: disable=invalid-commit

    @api.onchange("odoo_webhook_base_url")
    def onchange_odoo_webhook_base_url(self):
        if self.use_webhooks:
            msg = _(
                "If you change the base URL, you must delete and create "
                "the Webhooks again."
            )
            return {"warning": {"title": _("Warning"), "message": msg}}

    @api.onchange("worklog_date_timezone_mode")
    def _onchange_worklog_date_import_timezone_mode(self):
        for jira_backend in self:
            if jira_backend.worklog_date_timezone_mode == "specific":
                continue
            jira_backend.worklog_date_timezone = False

    def delete_webhooks(self):
        self.ensure_one()
        with self.work_on("jira.backend") as work:
            adapter = work.component(usage="backend.adapter")
            if self.webhook_issue_jira_id:
                try:
                    adapter.delete_webhook(self.webhook_issue_jira_id)
                except JIRAError as err:
                    # 404 means it has been deleted in JIRA, ignore it
                    if err.status_code != 404:
                        raise
            if self.webhook_worklog_jira_id:
                try:
                    adapter.delete_webhook(self.webhook_worklog_jira_id)
                except JIRAError as err:
                    # 404 means it has been deleted in JIRA, ignore it
                    if err.status_code != 404:
                        raise
            self.use_webhooks = False

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
                self.report_user_sync = self.env.ref(
                    "connector_jira.backend_report_user_sync"
                ).render({"backend": self, "result": bknd_result})
        return True

    def get_user_resolution_order(self):
        """User resolution should happen by login first as it's unique, while
        resolving by email is likely to give false positives"""
        return ["login", "email"]

    def import_issue_type(self):
        self.env["jira.issue.type"].import_batch(self)
        return True

    @api.model
    def get_api_client(self):
        self.ensure_one()
        # tokens are only readable by connector managers
        backend = self.sudo()
        oauth = {
            "access_token": backend.access_token,
            "access_token_secret": backend.access_secret,
            "consumer_key": backend.consumer_key,
            "key_cert": backend.private_key,
        }
        options = {
            "server": backend.uri,
            "verify": backend.verify_ssl,
        }
        return JIRA(options=options, oauth=oauth, timeout=JIRA_TIMEOUT)

    @api.model
    def _scheduler_import_project_task(self):
        self.search([]).import_project_task()

    @api.model
    def _scheduler_import_res_users(self):
        self.search([]).import_res_users()

    @api.model
    def _scheduler_import_analytic_line(self):
        self.search([]).import_analytic_line()

    @api.model
    def _scheduler_delete_analytic_line(self):
        self.search([]).delete_analytic_line()

    def make_issue_url(self, jira_issue_id):
        return urllib.parse.urljoin(self.uri, "/browse/{}".format(jira_issue_id))


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

    def create_webhook(
        self, name=None, url=None, events=None, jql="", exclude_body=False
    ):
        assert name and url and events
        data = {
            "name": name,
            "url": url,
            "events": events,
            "jqlFilter": jql,
            "excludeIssueDetails": exclude_body,
        }
        url = self.client._get_url("webhook", base=self.webhook_base_path)
        response = self.client._session.post(url, data=json.dumps(data))
        return json_loads(response)

    def delete_webhook(self, id_):
        url = self.client._get_url("webhook/%s" % id_, base=self.webhook_base_path)
        return json_loads(self.client._session.delete(url))
