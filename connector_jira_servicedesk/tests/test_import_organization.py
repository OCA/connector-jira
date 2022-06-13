# Copyright 2019-2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.addons.connector_jira.tests.common import JiraTransactionComponentCase

from .common import recorder


class TestImportOrganization(JiraTransactionComponentCase):
    @recorder.use_cassette
    def test_import_organization_batch(self):
        """Batch import of organizations

        This is a direct import of all organizations, without using
        individual jobs.
        """
        organizations = self.env["jira.organization"].search([])
        self.assertEqual(len(organizations), 0)
        self.env["jira.organization"].import_batch(
            self.backend_record,
        )
        organizations = self.env["jira.organization"].search([])
        # ensure that we have more than 50 records which
        # is the pagination of the REST API
        self.assertEqual(len(organizations), 60)

    def test_import_organization_from_record(self):
        """Import one organization from a records

        The batch import directly pass the record because it gets
        all the data at once from the API.
        """
        binding = self.env["jira.organization"].create(
            {
                "backend_id": self.backend_record.id,
                "external_id": "55",
                "name": "dummy",
            }
        )
        binding.import_record(
            self.backend_record,
            "55",
            record={"id": "55", "name": "new name"},
        )
        self.assertEqual(binding.name, "new name")

    @recorder.use_cassette
    def test_import_organization_from_api_call(self):
        """Import one organization from a call to the API"""
        binding = self.env["jira.organization"].create(
            {
                "backend_id": self.backend_record.id,
                "external_id": "55",
                "name": "dummy",
            }
        )
        binding.import_record(
            self.backend_record,
            "55",
        )
        self.assertEqual(binding.name, "org25")
