# Copyright: 2015 LasLabs, Inc.
# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import binascii
import logging
import json
import urllib.parse

from contextlib import contextmanager, closing
from datetime import datetime, timedelta
from os import urandom

import psycopg2
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jira import JIRA, JIRAError
from jira.utils import json_loads

import odoo
from odoo import models, fields, api, exceptions, _

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)

JIRA_TIMEOUT = 30  # seconds
IMPORT_DELTA = 70  # seconds


@contextmanager
def new_env(env):
    with api.Environment.manage():
        registry = odoo.registry(env.cr.dbname)
        with closing(registry.cursor()) as cr:
            new_env = api.Environment(cr, env.uid, env.context)
            try:
                yield new_env
            except Exception:
                cr.rollback()
                raise
            else:
                cr.commit()


class JiraBackend(models.Model):
    _name = 'jira.backend'
    _description = 'Jira Backend'
    _inherit = 'connector.backend'

    RSA_BITS = 4096
    RSA_PUBLIC_EXPONENT = 65537
    KEY_LEN = 255   # 255 == max Atlassian db col len

    def _default_company(self):
        return self.env['res.company']._company_default_get('jira.backend')

    def _default_consumer_key(self):
        """Generate a rnd consumer key of length self.KEY_LEN"""
        return binascii.hexlify(urandom(self.KEY_LEN))[:self.KEY_LEN]

    uri = fields.Char(string='Jira URI', required=True)
    name = fields.Char()
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        default=lambda self: self._default_company(),
    )
    state = fields.Selection(
        selection=[('authenticate', 'Authenticate'),
                   ('setup', 'Setup'),
                   ('running', 'Running'),
                   ],
        default='authenticate',
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
        selection='_selection_project_template',
        string='Default Project Template',
        default='Scrum software development',
        required=True,
    )
    project_template_shared = fields.Char(
        string='Default Shared Template Key',
    )

    use_webhooks = fields.Boolean(
        string='Use Webhooks',
        readonly=True,
        help="Webhooks need to be configured on the Jira instance. "
             "When activated, synchronization from Jira is blazing fast. "
             "It can be activated only on one Jira backend at a time. "
    )

    import_project_task_from_date = fields.Datetime(
        compute='_compute_last_import_date',
        inverse='_inverse_import_project_task_from_date',
        string='Import Project Tasks from date',
    )

    import_analytic_line_from_date = fields.Datetime(
        compute='_compute_last_import_date',
        inverse='_inverse_import_analytic_line_from_date',
        string='Import Worklogs from date',
    )

    issue_type_ids = fields.One2many(
        comodel_name='jira.issue.type',
        inverse_name='backend_id',
        string='Issue Types',
        readonly=True,
    )

    epic_link_field_name = fields.Char(
        string='Epic Link Field',
        help="The 'Epic Link' field on JIRA is a custom field. "
             "The name of the field is something like 'customfield_10002'. "
    )
    epic_name_field_name = fields.Char(
        string='Epic Name Field',
        help="The 'Epic Name' field on JIRA is a custom field. "
             "The name of the field is something like 'customfield_10003'. "
    )

    odoo_webhook_base_url = fields.Char(
        string='Base Odoo URL for Webhooks',
        default=lambda self: self._default_odoo_webhook_base_url(),
    )
    webhook_issue_jira_id = fields.Char()
    webhook_worklog_jira_id = fields.Char()
    # TODO: use something better to show this info
    # For instance, we could use web_notify to simply show a system msg.
    report_user_sync = fields.Html(readonly=True)

    @api.model
    def _default_odoo_webhook_base_url(self):
        params = self.env['ir.config_parameter']
        return params.get_param('web.base.url', '')

    @api.model
    def _selection_project_template(self):
        return [('Scrum software development',
                 'Scrum software development (Software)'),
                ('Kanban software development',
                 'Kanban software development (Software)'),
                ('Basic software development',
                 'Basic software development (Software)'),
                ('Project management', 'Project management (Business)'),
                ('Task management', 'Task management (Business)'),
                ('Process management', 'Process management (Business)'),
                ('shared', 'From a shared template'),
                ]

    @api.constrains('project_template_shared')
    def check_jira_key(self):
        for backend in self:
            if not backend.project_template_shared:
                continue
            valid = self.env['jira.project.project']._jira_key_valid
            if not valid(backend.project_template_shared):
                raise exceptions.ValidationError(
                    _('%s is not a valid JIRA Key') %
                    backend.project_template_shared
                )

    @api.multi
    @api.depends()
    def _compute_last_import_date(self):
        for backend in self:
            self.env.cr.execute("""
                SELECT from_date_field, import_start_time
                FROM jira_backend_timestamp
                WHERE backend_id = %s""", (backend.id,))
            rows = self.env.cr.dictfetchall()
            for row in rows:
                field = row['from_date_field']
                timestamp = row['import_start_time']
                if field in self._fields:
                    backend[field] = timestamp

    @api.multi
    def _inverse_date_fields(self, field_name):
        for rec in self:
            timestamp_id = self._lock_timestamp(field_name)
            self._update_timestamp(timestamp_id, field_name,
                                   getattr(rec, field_name))

    @api.multi
    def _inverse_import_project_task_from_date(self):
        self._inverse_date_fields('import_project_task_from_date')

    @api.multi
    def _inverse_import_analytic_line_from_date(self):
        self._inverse_date_fields('import_analytic_line_from_date')

    @api.multi
    def _lock_timestamp(self, from_date_field):
        """ Update the timestamp for a synchro

        thus, we prevent 2 synchros to be launched at the same time.
        The lock is released at the commit of the transaction.

        Return the id of the timestamp if the lock could be acquired.
        """
        assert from_date_field
        self.ensure_one()
        query = """
               SELECT id FROM jira_backend_timestamp
               WHERE backend_id = %s
               AND from_date_field = %s
               FOR UPDATE NOWAIT
            """
        try:
            self.env.cr.execute(
                query, (self.id, from_date_field)
            )
        except psycopg2.OperationalError:
            raise exceptions.UserError(
                _("The synchronization timestamp %s is currently locked, "
                  "probably due to an ongoing synchronization." %
                  from_date_field)
            )
        row = self.env.cr.fetchone()
        return row[0] if row else None

    @api.multi
    def _update_timestamp(self, timestamp_id,
                          from_date_field, import_start_time):
        """ Update import timestamp for a synchro

        This method is called to update or create one import timestamp
        for a jira.backend. A concurrency error can arise, but it's
        handled in _import_from_date.
        """
        self.ensure_one()
        if not import_start_time:
            return
        if timestamp_id:
            timestamp = self.env['jira.backend.timestamp'].browse(timestamp_id)
            timestamp.import_start_time = import_start_time
        else:
            self.env['jira.backend.timestamp'].create({
                'backend_id': self.id,
                'from_date_field': from_date_field,
                'import_start_time': import_start_time,
            })

    @api.multi
    def _import_from_date(self, model, from_date_field):
        """ Import records from a date

        Create jobs and update the sync timestamp in a savepoint; if a
        concurrency issue arises, it will be logged and rollbacked silently.
        """
        self.ensure_one()
        with self.env.cr.savepoint():
            import_start_time = datetime.now()
            try:
                self._lock_timestamp(from_date_field)
            except exceptions.UserError:
                # lock could not be acquired, it is already running and
                # locked by another transaction
                _logger.warning("Failed to update timestamps "
                                "for backend: %s and field: %s",
                                self, from_date_field, exc_info=True)
                return
            from_date = self[from_date_field]
            if from_date:
                from_date = fields.Datetime.from_string(from_date)
            else:
                from_date = None
            self.env[model].with_delay(priority=9).import_batch(
                self, from_date=from_date, to_date=import_start_time
            )

            # Reimport next records a small delta before the last import date
            # in case of small lag between servers or transaction committed
            # after the last import but with a date before the last import
            # BTW, the JQL search of JIRA does not allow
            # second precision, only minute precision, so
            # we really have to take more than one minute
            # margin
            next_time = import_start_time - timedelta(seconds=IMPORT_DELTA)
            next_time = fields.Datetime.to_string(next_time)
            setattr(self, from_date_field, next_time)

    @api.constrains('use_webhooks')
    def _check_use_webhooks_unique(self):
        if len(self.search([('use_webhooks', '=', True)])) > 1:
            raise exceptions.ValidationError(
                _('Only one backend can listen to webhooks')
            )

    @api.model
    def create(self, values):
        record = super().create(values)
        record.create_rsa_key_vals()
        return record

    @api.multi
    def create_rsa_key_vals(self):
        """ Create public/private RSA keypair """
        for backend in self:
            private_key = rsa.generate_private_key(
                public_exponent=self.RSA_PUBLIC_EXPONENT,
                key_size=self.RSA_BITS,
                backend=default_backend()
            )
            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            backend.write({
                'private_key': pem,
                'public_key': public_pem,
            })

    @api.multi
    def button_setup(self):
        self.state_running()

    @api.multi
    def activate_epic_link(self):
        self.ensure_one()
        with self.work_on('jira.backend') as work:
            adapter = work.component(usage='backend.adapter')
            jira_fields = adapter.list_fields()
            for field in jira_fields:
                custom_ref = field.get('schema', {}).get('custom')
                if custom_ref == 'com.pyxis.greenhopper.jira:gh-epic-link':
                    self.epic_link_field_name = field['id']
                elif custom_ref == 'com.pyxis.greenhopper.jira:gh-epic-label':
                    self.epic_name_field_name = field['id']

    @api.multi
    def state_setup(self):
        for backend in self:
            if backend.state == 'authenticate':
                backend.state = 'setup'

    @api.multi
    def state_running(self):
        for backend in self:
            if backend.state == 'setup':
                backend.state = 'running'

    @api.multi
    def create_webhooks(self):
        self.ensure_one()
        other_using_webhook = self.search(
            [('use_webhooks', '=', True),
             ('id', '!=', self.id)]
        )
        if other_using_webhook:
            raise exceptions.UserError(
                _('Only one JIRA backend can use the webhook at a time. '
                  'You must disable them on the backend "%s" before '
                  'activating them here.') % (other_using_webhook.name,)
            )

        # open a new cursor because we'll commit after the creations
        # to be sure to keep the webhook ids
        with new_env(self.env) as env:
            backend = env[self._name].browse(self.id)
            base_url = backend.odoo_webhook_base_url
            if not base_url:
                raise exceptions.UserError(
                    _('The Odoo Webhook base URL must be set.')
                )

            with self.work_on('jira.backend') as work:
                backend.use_webhooks = True

                adapter = work.component(usage='backend.adapter')
                # TODO: we could update the JQL of the webhook
                # each time a new project is sync'ed, so we would
                # filter out the useless events
                url = urllib.parse.urljoin(base_url,
                                           '/connector_jira/webhooks/issue')
                webhook = adapter.create_webhook(
                    name='Odoo Issues',
                    url=url,
                    events=['jira:issue_created',
                            'jira:issue_updated',
                            'jira:issue_deleted',
                            ],
                )
                # the only place where to find the hook id is in
                # the 'self' url, looks like
                # u'http://jira:8080/rest/webhooks/1.0/webhook/5'
                webhook_id = webhook['self'].split('/')[-1]
                backend.webhook_issue_jira_id = webhook_id
                env.cr.commit()

                url = urllib.parse.urljoin(base_url,
                                           '/connector_jira/webhooks/worklog')
                webhook = adapter.create_webhook(
                    name='Odoo Worklogs',
                    url=url,
                    events=['worklog_created',
                            'worklog_updated',
                            'worklog_deleted',
                            ],
                )
                webhook_id = webhook['self'].split('/')[-1]
                backend.webhook_worklog_jira_id = webhook_id
                env.cr.commit()

    @api.onchange('odoo_webhook_base_url')
    def onchange_odoo_webhook_base_url(self):
        if self.use_webhooks:
            msg = _('If you change the base URL, you must delete and create '
                    'the Webhooks again.')
            return {'warning': {'title': _('Warning'), 'message': msg}}

    @api.multi
    def delete_webhooks(self):
        self.ensure_one()
        with self.work_on('jira.backend') as work:
            adapter = work.component(usage='backend.adapter')
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

    @api.multi
    def check_connection(self):
        self.ensure_one()
        try:
            self.get_api_client()
        except ValueError as err:
            raise exceptions.UserError(
                _('Failed to connect (%s)') % (err,)
            )
        except JIRAError as err:
            raise exceptions.UserError(
                _('Failed to connect (%s)') % (err.text,)
            )
        raise exceptions.UserError(
            _('Connection successful')
        )

    @api.multi
    def import_project_task(self):
        self._import_from_date('jira.project.task',
                               'import_project_task_from_date')
        return True

    @api.multi
    def import_analytic_line(self):
        self._import_from_date('jira.account.analytic.line',
                               'import_analytic_line_from_date')
        return True

    @api.multi
    def import_res_users(self):
        # wipe report
        self.report_user_sync = ''
        result = self.env['res.users'].search([]).link_with_jira(backends=self)
        for __, bknd_result in result.items():
            if bknd_result.get('error'):
                self.report_user_sync = self.env.ref(
                    'connector_jira.backend_report_user_sync'
                ).render({'backend': self, 'result': bknd_result})
        return True

    @api.multi
    def import_issue_type(self):
        self.env['jira.issue.type'].import_batch(self)
        return True

    @api.model
    def get_api_client(self):
        self.ensure_one()
        # tokens are only readable by connector managers
        backend = self.sudo()
        oauth = {
            'access_token': backend.access_token,
            'access_token_secret': backend.access_secret,
            'consumer_key': backend.consumer_key,
            'key_cert': backend.private_key,
        }
        options = {
            'server': backend.uri,
            'verify': backend.verify_ssl,
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

    @api.multi
    def make_issue_url(self, jira_issue_id):
        return urllib.parse.urljoin(
            self.uri, '/browse/{}'.format(jira_issue_id))


class JiraBackendTimestamp(models.Model):
    _name = 'jira.backend.timestamp'
    _description = 'Jira Backend Import Timestamps'

    backend_id = fields.Many2one(
        comodel_name='jira.backend',
        string='Jira Backend',
        required=True,
    )
    from_date_field = fields.Char(
        string='From Date Field',
        required=True,
    )
    import_start_time = fields.Datetime(
        string='Import Start Time',
        required=True,
    )


class BackendAdapter(Component):
    _name = 'jira.backend.adapter'
    _inherit = 'jira.webservice.adapter'
    _apply_on = ['jira.backend']

    webhook_base_path = '{server}/rest/webhooks/1.0/{path}'

    def list_fields(self):
        return self.client._get_json('field')

    def create_webhook(self, name=None, url=None, events=None,
                       jql='', exclude_body=False):
        assert name and url and events
        data = {'name': name,
                'url': url,
                'events': events,
                'jqlFilter': jql,
                'excludeIssueDetails': exclude_body,
                }
        url = self.client._get_url('webhook', base=self.webhook_base_path)
        response = self.client._session.post(url, data=json.dumps(data))
        return json_loads(response)

    def delete_webhook(self, id_):
        url = self.client._get_url('webhook/%s' % id_,
                                   base=self.webhook_base_path)
        return json_loads(self.client._session.delete(url))
