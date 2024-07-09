# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    "name": "JIRA Connector - Service Desk Extension",
    "version": "17.0.1.0.0",
    "author": "Camptocamp,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Connector",
    "depends": ["connector_jira"],
    "website": "https://github.com/OCA/connector-jira",
    "data": [
        "security/ir.model.access.csv",
        "views/jira_backend.xml",
        "views/jira_project_project.xml",
        "wizards/project_link_jira.xml",
    ],
    "installable": True,
}
