# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

"""
Related Actions for Jira:

Related actions are associated with jobs.
When called on a job, they will return an action to the client.

"""

import functools
from openerp.addons.connector import related_action
from .unit.binder import JiraBinder

unwrap_binding = functools.partial(related_action.unwrap_binding,
                                   binder_class=JiraBinder)
