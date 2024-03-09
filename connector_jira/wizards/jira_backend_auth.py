# Copyright: 2015 LasLabs, Inc.
# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
from urllib.parse import parse_qsl

import requests

from odoo import _, api, exceptions, fields, models

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
    _name = "jira.backend.auth"
    _description = "Jira Backend Auth"
