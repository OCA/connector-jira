# Copyright: 2015 LasLabs, Inc.
# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime

import psycopg2

from odoo import api, fields, models

from ..fields import MilliDatetime


class JiraBackendTimestamp(models.Model):
    _name = "jira.backend.timestamp"
    _description = "Jira Backend Import Timestamps"

    backend_id = fields.Many2one(
        comodel_name="jira.backend",
        string="Jira Backend",
        required=True,
    )
    from_date_field = fields.Char(required=True)

    # For worklogs, jira allows to work with milliseconds
    # unix timestamps, we keep this precision by using a new type
    # of field. The ORM values for this field are Unix timestamps the
    # same way Jira use them: unix timestamp as integer multiplied * 1000
    # to keep the milli precision with 3 digits (example 1554318348000).
    last_timestamp = MilliDatetime(string="Last Timestamp", required=True)

    # The content of this field must match to the "usage" of a component.
    # The method JiraBinding.run_batch_timestamp() will find the matching
    # component for the model and call "run()" on it.
    component_usage = fields.Char(
        required=True,
        help="Used by the connector to find which component "
        "execute the batch import (technical).",
    )

    _sql_constraints = [
        (
            "timestamp_field_uniq",
            "unique(backend_id, from_date_field, component_usage)",
            "A timestamp already exists.",
        ),
    ]

    @api.model
    def _timestamp_for_field(self, backend, field_name, component_usage):
        """Return the timestamp for a field"""
        timestamp = self.search(
            [
                ("backend_id", "=", backend.id),
                ("from_date_field", "=", field_name),
                ("component_usage", "=", component_usage),
            ]
        )
        if not timestamp:
            timestamp = self.env["jira.backend.timestamp"].create(
                {
                    "backend_id": backend.id,
                    "from_date_field": field_name,
                    "component_usage": component_usage,
                    "last_timestamp": datetime.fromtimestamp(0),
                }
            )
        return timestamp

    def _update_timestamp(self, timestamp):
        self.ensure_one()
        self.last_timestamp = timestamp

    def _lock(self):
        """Update the timestamp for a synchro

        thus, we prevent 2 synchros to be launched at the same time.
        The lock is released at the commit of the transaction.

        Return True if the lock could be acquired.
        """
        self.ensure_one()
        query = "SELECT id FROM jira_backend_timestamp WHERE id = %s FOR UPDATE NOWAIT"
        try:
            self.env.cr.execute(query, (self.id,))
        except psycopg2.OperationalError:
            return False
        return bool(self.env.cr.fetchone())
