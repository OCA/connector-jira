# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp.addons.connector.backend import Backend

jira = Backend('jira')
""" Generic QoQa Backend. """

jira_7_2_0 = Backend(parent=jira, version='7.2.0')
""" Backend for version 7.2.0 of Jira """
