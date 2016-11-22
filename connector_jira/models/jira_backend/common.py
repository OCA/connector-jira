# -*- coding: utf-8 -*-
# Copyright: 2015 LasLabs, Inc.
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from contextlib import contextmanager
from datetime import datetime, timedelta
from os import urandom

import psycopg2
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jira import JIRA, JIRAError

from openerp import models, fields, api, exceptions, _

from openerp.addons.connector.connector import ConnectorEnvironment
from openerp.addons.connector.session import ConnectorSession

from ...unit.importer import import_batch
from ..jira_issue_type.importer import import_batch_issue_type

_logger = logging.getLogger(__name__)

IMPORT_DELTA = 70  # seconds


class JiraBackend(models.Model):
    _name = 'jira.backend'
    _description = 'Jira Backend'
    _inherit = 'connector.backend'
    _backend_type = 'jira'

    RSA_BITS = 4096
    RSA_PUBLIC_EXPONENT = 65537
    KEY_LEN = 255   # 255 == max Atlassian db col len

    def _default_company(self):
        return self.env['res.company']._company_default_get('jira.backend')

    def _default_consumer_key(self):
        ''' Generate a rnd consumer key of length self.KEY_LEN '''
        return urandom(self.KEY_LEN).encode('hex')[:self.KEY_LEN]

    version = fields.Selection(
        selection='_select_versions',
        string='Jira Version',
        required=True,
    )
    uri = fields.Char(string='Jira URI')
    name = fields.Char()
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        default=lambda self: self._default_company(),
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
        default='Process management',
        required=True,
    )

    use_webhooks = fields.Boolean(
        string='Use Webhooks',
        default=lambda self: self._default_use_webhooks(),
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

    @api.model
    def _default_use_webhooks(self):
        return not bool(self.search([('use_webhooks', '=', True)], limit=1))

    @api.model
    def _selection_project_template(self):
        return [('Project management', 'Project management'),
                ('Task management', 'Task management'),
                ('Process management', 'Process management'),
                ]

    @api.model
    def _select_versions(self):
        """ Available versions

        Can be inherited to add custom versions.
        """
        return [('7.2.0', '7.2.0+'),
                ]

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
            session = ConnectorSession.from_env(self.env)
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
            import_batch.delay(session, model, self.id,
                               from_date=from_date,
                               to_date=import_start_time,
                               priority=9)

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
        record = super(JiraBackend, self).create(values)
        self.create_rsa_key_vals()
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
    def check_connection(self):
        self.ensure_one()
        try:
            self.get_api_client()
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
        self.env['res.users'].search([]).link_with_jira(backends=self)
        return True

    @api.multi
    def import_issue_type(self):
        session = ConnectorSession.from_env(self.env)
        import_batch_issue_type(session, 'jira.issue.type', self.id)
        return True

    @contextmanager
    @api.multi
    def get_environment(self, model_name, session=None):
        self.ensure_one()
        if not session:
            session = ConnectorSession.from_env(self.env)
        yield ConnectorEnvironment(self, session, model_name)

    @api.model
    def get_api_client(self):
        oauth = {
            'access_token': self.access_token,
            'access_token_secret': self.access_secret,
            'consumer_key': self.consumer_key,
            'key_cert': self.private_key,
        }
        options = {
            'server': self.uri,
            'verify': self.verify_ssl,
        }
        return JIRA(options=options, oauth=oauth)

    @api.model
    def _scheduler_import_project_task(self):
        self.search([]).import_project_task()

    @api.model
    def _scheduler_import_res_users(self):
        self.search([]).import_res_users()

    @api.model
    def _scheduler_import_analytic_line(self):
        self.search([]).import_analytic_line()


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
