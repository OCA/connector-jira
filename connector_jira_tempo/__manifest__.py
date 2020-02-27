# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'JIRA Connector Tempo',
    'version': '11.0.1.0.2',
    'author': 'Camptocamp,Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'category': 'Connector',
    'depends': [
        'connector_jira',
        'hr_timesheet',
    ],
    'website': 'https://www.camptocamp.com',
    'data': [
        'data/cron.xml',
        'views/jira_backend_view.xml',
        'views/timesheet_account_analytic_line.xml',
    ],
    'installable': True,
}
