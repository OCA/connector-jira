# Copyright 2016-2019 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class JiraProjectTaskAdapter(Component):
    _name = "jira.project.task.adapter"
    _inherit = ["jira.webservice.adapter"]
    _apply_on = ["jira.project.task"]

    # pylint: disable=W8106
    def read(self, id_, fields=None):
        # No ``super()``: MRO will end up calling ``base.backend.adapter.crud.read()``
        # methods that will raise a ``NotImplementedError`` exception
        return self.get(id_, fields=fields).raw

    def get(self, id_, fields=None):
        with self.handle_404():
            return self.client.issue(id_, fields=fields, expand=["renderedFields"])

    def search(self, jql):
        # we need to have at least one field which is not 'id' or 'key'
        # due to this bug: https://github.com/pycontribs/jira/pull/289
        issues = self.client.search_issues(jql, fields="id,updated", maxResults=None)
        return [issue.id for issue in issues]
