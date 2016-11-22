# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import fields, models

from ...unit.backend_adapter import JiraAdapter
from ...backend import jira


class JiraIssueType(models.Model):
    _name = 'jira.issue.type'
    _inherit = 'jira.binding'
    _description = 'Jira Issue Type'

    name = fields.Char(required=True, readonly=True)
    description = fields.Char(readonly=True)


@jira
class IssueTypeAdapter(JiraAdapter):
    _model_name = 'jira.issue.type'

    def read(self, id):
        return self.client.issue_type(id).raw

    def search(self):
        issues = self.client.issue_types()
        return [issue.id for issue in issues]
