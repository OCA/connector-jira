# -*- coding: utf-8 -*-
# Copyright: 2015 LasLabs, Inc.
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from os import urandom

from contextlib import contextmanager

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jira import JIRA, JIRAError

from openerp import models, fields, api, exceptions, _

from openerp.addons.connector.connector import ConnectorEnvironment


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
    private_key = fields.Text(readonly=True)
    public_key = fields.Text(readonly=True)
    consumer_key = fields.Char(
        default=lambda self: self._default_consumer_key(),
        readonly=True,
    )

    access_token = fields.Char(readonly=True)
    access_secret = fields.Char(readonly=True)

    verify_ssl = fields.Boolean(default=True, string="Verify SSL?")

    project_template = fields.Selection(
        selection='_selection_project_template',
        string='Default Project Template',
        default='Process management',
        required=True,
    )

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

    @contextmanager
    @api.multi
    def get_environment(self, session, model_name):
        self.ensure_one()
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
