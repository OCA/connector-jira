# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import fields, models


class JiraBinding(models.AbstractModel):
    """ Abstract Model for the Bindings.

    All the models used as bindings between Jira and Odoo
    (``jira.product.product``, ...) should ``_inherit`` it.
    """
    _name = 'jira.binding'
    _inherit = 'external.binding'
    _description = 'Jira Binding (abstract)'

    # openerp-side id must be declared in concrete model
    # openerp_id = fields.Many2one(...)
    backend_id = fields.Many2one(
        comodel_name='jira.backend',
        string='Jira Backend',
        required=True,
        ondelete='restrict',
    )
    external_id = fields.Char(string='ID on Jira', index=True)

    _sql_constraints = [
        ('jira_binding_uniq', 'unique(backend_id, jira_id)',
         "A binding already exists for this Jira record"),
    ]
