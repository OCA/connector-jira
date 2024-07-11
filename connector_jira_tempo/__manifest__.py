# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "JIRA Connector Tempo",
    "version": "17.0.1.0.0",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Connector",
    "depends": ["connector_jira_tempo_base", "hr_timesheet"],
    "website": "https://github.com/OCA/connector-jira",
    "data": [
        "data/cron.xml",
        "views/account_analytic_line.xml",
        "views/jira_backend.xml",
    ],
    "installable": True,
}
