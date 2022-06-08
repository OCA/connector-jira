# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""Tests for connector_jira

# Running tests

Tests are run normally, you can either execute them with odoo's
``--test-enable`` option or using `pytest-odoo
<https://github.com/camptocamp/pytest-odoo/>`_

The requests to Jira are recorded and simulated using `vcrpy
<https://vcrpy.readthedocs.io/en/latest/usage.html>`_. Which means
the tests can be executed without having a Jira service running.

However, in order to write new tests or modify the existing ones, you may need
to have a service running to record the Webservice interactions.

# Recording new tests with vcr.py

First, you will need a running Jira. We use a docker image, a simple
composition is enough::

    version: '2'
    services:

    jira:
        image: cptactionhank/atlassian-jira-software:7.12.3
        volumes:
        - "data-jira:/var/atlassian/jira"
        ports:
        - 8080:8080

    volumes:
    data-jira:

When you first access to Jira, it will guide you through a procedure
to obtain a demo license.

Once connected, you will need to do the Oauth dance to obtain tokens.

You can do so using the CLI command line::

  odoo jiraoauthdance

See details in ``connector_jira/cli/jira_oauth_dance.py``.

Once you have tokens (access+secret), you will need to set them
in environment variables when you run your tests:

- JIRA_TEST_URL
- JIRA_TEST_TOKEN_ACCESS
- JIRA_TEST_TOKEN_SECRET

From now on, you can write your tests using the ``recorder.use_cassette``
decorator or context manager. If you are changing existing tests, you might
need either to manually edit the cassette files in "tests/fixtures/cassettes"
or record the tests again (in such case, IDs may change).

"""

import logging
import os
from contextlib import contextmanager
from os.path import dirname, join
from unittest import mock

from vcr import VCR

from odoo.addons.component.tests.common import TransactionComponentCase

_logger = logging.getLogger(__name__)

jira_test_url = os.environ.get("JIRA_TEST_URL", "http://jira:8080")
jira_test_token_access = os.environ.get("JIRA_TEST_TOKEN_ACCESS", "")
jira_test_token_secret = os.environ.get("JIRA_TEST_TOKEN_SECRET", "")


def get_recorder(base_path=None, **kw):
    base_path = base_path or dirname(__file__)
    defaults = dict(
        record_mode="once",
        cassette_library_dir=join(base_path, "fixtures/cassettes"),
        path_transformer=VCR.ensure_suffix(".yaml"),
        match_on=["method", "path", "query"],
        filter_headers=["Authorization"],
        decode_compressed_response=True,
    )
    defaults.update(kw)
    return VCR(**defaults)


recorder = get_recorder()


class JiraTransactionComponentCase(TransactionComponentCase):
    """Base class for tests with Jira"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        context = cls.env.context.copy()
        context["tracking_disable"] = True
        cls.env = cls.env(context=context)

        cls.backend_record = cls.env.ref("connector_jira.jira_backend_demo")
        cls.backend_record.write(
            {
                "uri": jira_test_url,
                "access_token": jira_test_token_access,
                "access_secret": jira_test_token_secret,
                "epic_link_field_name": "customfield_10101",
            }
        )

    # Warning: if you add new tests or change the cassettes
    # you might need to change these values
    # to make issue types match
    _base_issue_types = [
        ("Task", "10002"),
        ("Sub-task", "10003"),
        ("Story", "10001"),
        ("Bug", "10004"),
        ("Epic", "10000"),
    ]

    @classmethod
    def _link_user(cls, user, jira_login):
        return (
            cls.env["jira.res.users"]
            .with_context(no_connector_export=True)
            .create(
                {
                    "odoo_id": user.id,
                    "backend_id": cls.backend_record.id,
                    "external_id": jira_login,
                }
            )
        )

    @classmethod
    def _create_issue_type_bindings(cls):
        for name, jira_id in cls._base_issue_types:
            cls.env["jira.issue.type"].create(
                {
                    "name": name,
                    "backend_id": cls.backend_record.id,
                    "external_id": jira_id,
                }
            )

    @classmethod
    def _create_project_binding(
        cls, project, sync_action="link", issue_types=None, **extra
    ):
        values = {
            "odoo_id": project.id,
            "jira_key": "TEST",
            "sync_action": sync_action,
            "backend_id": cls.backend_record.id,
            # dummy id
            "external_id": "9999",
        }
        if issue_types:
            values.update({"sync_issue_type_ids": [(6, 0, issue_types.ids)]})
        values.update(**extra)
        return (
            cls.env["jira.project.project"]
            .with_context(no_connector_export=True)
            .create(values)
        )

    @classmethod
    def _create_task_binding(cls, task, **extra):
        values = {
            "odoo_id": task.id,
            "jira_key": "TEST",
            "backend_id": cls.backend_record.id,
            # dummy id
            "external_id": "9999",
        }
        values.update(**extra)
        return (
            cls.env["jira.project.task"]
            .with_context(no_connector_export=True)
            .create(values)
        )

    @classmethod
    def _create_analytic_line_binding(cls, line, **extra):
        values = {
            "odoo_id": line.id,
            "backend_id": cls.backend_record.id,
            # dummy id
            "external_id": "9999",
        }
        values.update(**extra)
        return (
            cls.env["jira.account.analytic.line"]
            .with_context(no_connector_export=True)
            .create(values)
        )

    @contextmanager
    def mock_with_delay(self):
        with mock.patch(
            "odoo.addons.queue_job.models.base.DelayableRecordset",
            name="DelayableRecordset",
            spec=True,
        ) as delayable_cls:
            # prepare the mocks
            delayable = mock.MagicMock(name="DelayableBinding")
            delayable_cls.return_value = delayable
            yield delayable_cls, delayable
