# Copyright: 2015 LasLabs, Inc.
# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

import requests

from urllib.parse import parse_qsl

from odoo import models, fields, api, exceptions, _

_logger = logging.getLogger(__name__)

try:
    from oauthlib.oauth1 import SIGNATURE_RSA
except ImportError as err:
    _logger.debug(err)

try:
    from requests_oauthlib import OAuth1
except ImportError as err:
    _logger.debug(err)


class JiraBackendAuth(models.TransientModel):
    _name = 'jira.backend.auth'
    _description = 'Jira Backend Auth'

    OAUTH_BASE = 'plugins/servlet/oauth'

    @api.model
    def default_get(self, fields):
        values = super().default_get(fields)
        context = self.env.context
        if (context.get('active_model') == 'jira.backend' and
                context.get('active_id')):
            backend = self.env['jira.backend'].browse(context['active_id'])
            values.update({
                'backend_id': backend.id,
                'consumer_key': backend.consumer_key,
                'public_key': backend.public_key,
            })
        return values

    backend_id = fields.Many2one('jira.backend')
    state = fields.Selection([
        ('leg_1', 'OAuth Remote Config'),
        ('leg_2', 'OAuth Remote Auth'),
        ('done', 'Complete')
    ], default='leg_1')

    consumer_key = fields.Char(
        related='backend_id.consumer_key',
        readonly=True,
    )
    public_key = fields.Text(
        related='backend_id.public_key',
        readonly=True,
    )

    # fields populated by leg_1
    request_token = fields.Char(readonly=True)
    request_secret = fields.Char(readonly=True)
    auth_uri = fields.Char(readonly=True)

    @api.model
    def _next_action(self):
        act = self.env['ir.actions.act_window'].for_xml_id(
            'connector_jira', 'action_jira_backend_auth'
        )
        act['res_id'] = self.id
        return act

    @api.multi
    def generate_new_key(self):
        self.backend_id.create_rsa_key_vals()
        jira_model = self.env['jira.backend']
        self.backend_id.consumer_key = jira_model._default_consumer_key()
        return self._next_action()

    @api.multi
    def do_oauth_leg_1(self):
        oauth_hook = OAuth1(
            client_key=self.consumer_key,
            client_secret='',
            signature_method=SIGNATURE_RSA,
            rsa_key=self.backend_id.private_key,
        )
        try:
            req = requests.post(
                '%s/%s/request-token' % (self.backend_id.uri, self.OAUTH_BASE),
                verify=self.backend_id.verify_ssl, auth=oauth_hook
            )
        except requests.exceptions.SSLError as err:
            raise exceptions.UserError(
                _('SSL error during negociation: %s') % (err,)
            )
        resp = dict(parse_qsl(req.text))

        token = resp.get('oauth_token')
        secret = resp.get('oauth_token_secret')

        if None in [token, secret]:
            raise exceptions.UserError(
                _('Did not get token (%s) or secret (%s) from Jira. Resp %s') %
                (token, secret, resp)
            )

        self.write({
            'request_token': token,
            'request_secret': secret,
            'auth_uri': '%s/%s/authorize?oauth_token=%s' % (
                self.backend_id.uri, self.OAUTH_BASE, token
            ),
        })
        self.state = 'leg_2'
        return self._next_action()

    @api.multi
    def do_oauth_leg_3(self):
        """ Perform OAuth step 3 to get access_token and secret """
        oauth_hook = OAuth1(
            client_key=self.consumer_key,
            client_secret='',
            signature_method=SIGNATURE_RSA,
            rsa_key=self.backend_id.private_key,
            resource_owner_key=self.request_token,
            resource_owner_secret=self.request_secret,
        )
        try:
            req = requests.post(
                '%s/%s/access-token' % (self.backend_id.uri, self.OAUTH_BASE),
                verify=self.backend_id.verify_ssl, auth=oauth_hook
            )
        except requests.exceptions.SSLError as err:
            raise exceptions.UserError(
                _('SSL error during negociation: %s') % (err,)
            )
        resp = dict(parse_qsl(req.text))

        token = resp.get('oauth_token')
        secret = resp.get('oauth_token_secret')

        if None in [token, secret]:
            raise exceptions.UserError(
                _('Did not get token (%s) or secret (%s) from Jira. Resp %s') %
                (token, secret, resp)
            )

        self.backend_id.write({
            'access_token': token,
            'access_secret': secret,
        })
        self.state = 'done'
        self.backend_id.state_setup()
        return self._next_action()
