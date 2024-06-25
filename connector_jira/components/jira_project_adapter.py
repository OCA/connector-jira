# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging
import tempfile

from odoo import _, exceptions

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)

try:
    from jira import JIRAError
    from jira.utils import json_loads
except ImportError as err:
    _logger.debug(err)


class JiraProjectAdapter(Component):
    _name = "jira.project.adapter"
    _inherit = ["jira.webservice.adapter"]
    _apply_on = ["jira.project.project"]

    # pylint: disable=W8106
    def read(self, id_):
        # No ``super()``: MRO will end up calling ``base.backend.adapter.crud.read()``
        # methods that will raise a ``NotImplementedError`` exception
        with self.handle_404():
            return self.get(id_).raw

    def get(self, id_):
        with self.handle_404():
            return self.client.project(id_)

    # pylint: disable=W8106
    def write(self, id_, values):
        # No ``super()``: MRO will end up calling ``base.backend.adapter.crud.write()``
        # methods that will raise a ``NotImplementedError`` exception
        with self.handle_404():
            return self.get(id_).update(values)

    # pylint: disable=W8106
    def create(self, key=None, name=None, template_name=None, values=None):
        # No ``super()``: MRO will end up calling ``base.backend.adapter.crud.create()``
        # methods that will raise a ``NotImplementedError`` exception
        project = self.client.create_project(
            key=key,
            name=name,
            template_name=template_name,
        )
        if values:
            project.update(values)
        return project

    def create_shared(self, key=None, name=None, shared_key=None, lead=None):
        assert key and name and shared_key
        # There is no public method for creating a shared project:
        # https://jira.atlassian.com/browse/JRA-45929
        # People found a private method for doing so, which is explained on:
        # https://jira.atlassian.com/browse/JRASERVER-27256

        try:
            project = self.read(shared_key)
            project_id = project["id"]
        except JIRAError as err:
            if err.status_code == 404:
                raise exceptions.UserError(
                    _('Project template with key "%s" not found.') % shared_key
                ) from err
            else:
                raise

        server_url = self.client._options["server"]
        url = server_url + "/rest/project-templates/1.0/createshared/%s" % project_id
        payload = {"name": name, "key": key, "lead": lead}

        response = self.client._session.post(url, data=json.dumps(payload))
        if response.status_code == 200:
            return json_loads(response)

        tmp_file = tempfile.NamedTemporaryFile(
            prefix="python-jira-error-create-shared-project-",
            suffix=".html",
            delete=False,
        )
        tmp_file.write(response.text)

        if self.logging:
            _logger.error(
                "Unexpected result while running create shared project."
                f" Server response saved in {tmp_file.name} for further investigation"
                f" [HTTP response={response.status_code}]."
            )
        return False
