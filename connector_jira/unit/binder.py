# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import fields
from openerp.addons.connector.connector import Binder

from ..backend import jira


@jira
class JiraBinder(Binder):

    _model_name = [
        'jira.project.project',
        'jira.project.task',
    ]

    def sync_date(self, binding):
        assert self._sync_date_field
        sync_date = binding[self._sync_date_field]
        if not sync_date:
            return
        return fields.Datetime.from_string(sync_date)
