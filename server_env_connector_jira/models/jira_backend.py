# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from distutils.util import strtobool

from odoo import api, fields, models
try:
    from odoo.addons.server_environment import serv_config
except ImportError:
    logging.getLogger('odoo.module').warning(
        'server_environment not available in addons path. '
        'server_env_connector_jira will not be usable')

_logger = logging.getLogger(__name__)


def is_true(strval):
    return bool(strtobool(strval or '0'.lower()))


class JiraBackend(models.Model):
    _inherit = 'jira.backend'

    @api.multi
    def _compute_server_env(self):
        for backend in self:
            for field_name in ('uri', 'verify_ssl', 'odoo_webhook_base_url'):
                section_name = '.'.join((self._name.replace('.', '_'),
                                         backend.name))
                try:
                    value = serv_config.get(section_name, field_name)
                    if field_name == 'verify_ssl' and value:
                        value = is_true(value)
                    setattr(backend, field_name,  value)
                except:
                    _logger.exception('error trying to read field %s '
                                      'in section %s', field_name,
                                      section_name)

    uri = fields.Char(compute='_compute_server_env')
    verify_ssl = fields.Boolean(compute='_compute_server_env')
    odoo_webhook_base_url = fields.Char(compute='_compute_server_env')
