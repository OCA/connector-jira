# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from openerp import fields, models
from openerp.addons.connector.connector import Binder

from ..backend import jira

_logger = logging.getLogger(__name__)


@jira
class JiraBinder(Binder):

    _model_name = [
        'jira.account.analytic.line',
        'jira.project.project',
        'jira.project.task',
        'jira.res.users',
    ]

    def sync_date(self, binding):
        assert self._sync_date_field
        sync_date = binding[self._sync_date_field]
        if not sync_date:
            return
        return fields.Datetime.from_string(sync_date)


@jira
class JiraModelBinder(Binder):
    """ Binder for standalone models

    When we synchronize a model that has no equivalent
    in Odoo, we create a model that hold the Jira records
    without `_inherits`.

    """

    _model_name = [
        'jira.issue.type',
    ]

    _openerp_field = 'id'

    def to_openerp(self, external_id, unwrap=False):
        if unwrap:
            _logger.warning('unwrap has no effect when the '
                            'binding is not an inherits '
                            '(model %s)', self.model._name)
        _super = super(JiraModelBinder, self)
        return _super.to_openerp(external_id, unwrap=False)

    def unwrap_binding(self, binding_id, browse=False):
        if isinstance(binding_id, models.BaseModel):
            binding = binding_id
        else:
            binding = self.model.browse(binding_id)
        if browse:
            return binding
        else:
            return binding.id

    def unwrap_model(self):
        return self.model
