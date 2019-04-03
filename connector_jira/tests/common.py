# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.addons.component.tests.common import SavepointComponentCase

from os.path import dirname, join
import os

from vcr import VCR
import logging

_logger = logging.getLogger(__name__)

jira_test_url = os.environ.get('JIRA_TEST_URL', 'http://jira:8080')
jira_test_token_access = os.environ.get('JIRA_TEST_TOKEN_ACCESS', '')
jira_test_token_secret = os.environ.get('JIRA_TEST_TOKEN_SECRET', '')


def get_recorder(**kw):
    defaults = dict(
        record_mode='once',
        cassette_library_dir=join(dirname(__file__), 'fixtures/cassettes'),
        path_transformer=VCR.ensure_suffix('.yaml'),
        match_on=['method', 'path', 'query'],
        filter_headers=['Authorization'],
        decode_compressed_response=True,
    )
    defaults.update(kw)
    return VCR(**defaults)


recorder = get_recorder()


class JiraTransactionCase(SavepointComponentCase):
    """Base class for tests with Jira"""

    def setUp(self):
        super().setUp()
        self.backend_record = self.env.ref(
            'connector_jira.jira_backend_demo'
        )
        self.backend_record.write({
            'uri': jira_test_url,
            'access_token': jira_test_token_access,
            'access_secret': jira_test_token_secret,
        })
