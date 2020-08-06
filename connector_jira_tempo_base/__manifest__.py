# Copyright 2018 Camptocamp SA
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "JIRA Connector Tempo (base)",
    "version": "12.0.1.1.0",
    "category": "Connector",
    "website": "https://github.com/OCA/connector-jira",
    "author": "Brainbean Apps, " "Camptocamp, " "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "application": False,
    "summary": "Base for JIRA Connector Tempo",
    "depends": ["connector_jira",],
    "data": ["views/jira_backend.xml",],
}
