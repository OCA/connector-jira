# Copyright 2019-2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from os.path import dirname

from odoo.addons.connector_jira.tests.common import get_recorder

recorder = get_recorder(base_path=dirname(__file__))
