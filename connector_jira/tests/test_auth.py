# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import unittest

from odoo import exceptions

from .common import JiraTransactionComponentCase, recorder


class TestAuth(JiraTransactionComponentCase):
    @recorder.use_cassette
    def test_auth_oauth(self):
        backend = self.backend_record
        # reset access
        backend.write({"access_token": False, "access_secret": False})
        self.assertEqual(backend.state, "authenticate")
        auth_wizard = self.env["jira.backend.auth"].create({"backend_id": backend.id})

        self.assertEqual(auth_wizard.state, "leg_1")
        # Here, the wizard generates a consumer key and
        # a private/public key. User has to copy them in Jira.
        self.assertTrue(auth_wizard.consumer_key)
        self.assertTrue(auth_wizard.public_key)
        self.assertTrue(auth_wizard.backend_id.private_key)
        # Once copied in Jira, they have to confirm "Leg 1"
        auth_wizard.do_oauth_leg_1()

        # during leg 1, Jira validates the keys and returns
        # an authentication URL that the user has to open
        # (will need to login).
        # For this test, I manually validated the auth URI,
        # as we record the requests, the recorded interactions
        # will work for the test.
        self.assertTrue(auth_wizard.auth_uri)
        self.assertEqual(auth_wizard.state, "leg_2")
        # returned by Jira:
        self.assertTrue(auth_wizard.request_token)
        self.assertTrue(auth_wizard.request_secret)

        auth_wizard.do_oauth_leg_3()

        # of course, these are dummy tokens recorded for the test
        # on a demo Jira
        self.assertEqual(backend.access_token, "o7XglNpQdA3pwzGZw9r6WA2X2XZcjaaI")
        self.assertEqual(backend.access_secret, "pwq9Qzc7iax0JtoQqZdLvPlv4ReECZGh")
        self.assertEqual(auth_wizard.state, "done")

    @recorder.use_cassette
    def test_auth_check_connection(self):
        with self.assertRaisesRegex(exceptions.UserError, "Connection successful"):
            self.backend_record.check_connection()

    @unittest.skip(
        "This test is slow because the jira lib retries "
        "401 errors with an exponential backoff."
    )
    @recorder.use_cassette
    def test_auth_check_connection_failure(self):
        # reset access
        self.backend_record.write({"access_token": False, "access_secret": False})
        with self.assertRaisesRegex(exceptions.UserError, "Failed to connect"):
            self.backend_record.check_connection()
