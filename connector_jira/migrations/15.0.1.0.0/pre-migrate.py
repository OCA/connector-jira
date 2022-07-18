# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from openupgradelib import openupgrade


def migrate(cr, version):
    add_missing_xmlid_on_channel(cr)


def add_missing_xmlid_on_channel(cr):
    query = """
        SELECT id FROM queue_job_channel
        WHERE complete_name='root.connector_jira.import';
    """
    cr.execute(query)
    channel = cr.fetchall()
    if channel:
        openupgrade.add_xmlid(
            cr,
            "connector_jira",
            "import_root",
            "queue.job.channel",
            channel[0][0],
        )
