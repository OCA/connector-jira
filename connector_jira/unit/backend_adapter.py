# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from openerp.addons.connector.unit.backend_adapter import CRUDAdapter


class JiraAdapter(CRUDAdapter):
    """ External Records Adapter for Jira """

    def __init__(self, environment):
        """
        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(JiraAdapter, self).__init__(environment)
        self.client = self.backend_record.get_api_client()
