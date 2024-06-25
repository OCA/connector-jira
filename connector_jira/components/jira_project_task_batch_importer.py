# Copyright 2016-2022 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class JiraProjectTaskBatchImporter(Component):
    """Import the Jira tasks

    For every id in the list of tasks, a delayed job is created.
    Import from a given date.
    """

    _name = "jira.project.task.batch.importer"
    _inherit = ["jira.timestamp.batch.importer"]
    _apply_on = ["jira.project.task"]
