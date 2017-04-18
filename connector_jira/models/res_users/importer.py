# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from ...unit.importer import JiraImporter
from ...backend import jira


@jira
class UserImporter(JiraImporter):
    _model_name = 'jira.res.users'

    def _import(self, binding):
        record = self.external_record
        jira_key = self.external_id
        binder = self.binder_for('jira.res.users')
        user = binder.to_internal(jira_key, unwrap=True)
        if not user:
            email = record['emailAddress']
            user = self.env['res.users'].search(
                ['|',
                 ('login', '=', jira_key),
                 ('email', '=', email)],
            )
            user.link_with_jira(backends=self.backend_record)
