# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp.addons.connector.connector import Binder

from ..backend import jira


@jira
class JiraBinder(Binder):

    _model_name = [
        'jira.project.project',
    ]
