# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


JIRA_JQL_DATETIME_FORMAT = '%Y-%m-%d %H:%M'  # no seconds :-(


class JiraAdapter(Component):
    """ Generic adapter for using the JIRA backend """
    _name = 'jira.webservice.adapter'
    _inherit = ['base.backend.adapter.crud', 'jira.base']
    _usage = 'backend.adapter'

    def __init__(self, work_context):
        super().__init__(work_context)
        self.client = self.backend_record.get_api_client()
