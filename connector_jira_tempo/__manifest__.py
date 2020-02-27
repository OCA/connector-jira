# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'JIRA Connector Tempo',
    'version': '12.0.2.1.1',
    'author':
        'Camptocamp, '
        'Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'category': 'Connector',
    'depends': [
        'connector_jira_tempo_base',
        'hr_timesheet',
    ],
    'website': 'https://github.com/OCA/connector-jira',
    'data': [
        'data/cron.xml',
        'views/jira_backend_view.xml',
        'views/timesheet_account_analytic_line.xml',
    ],
    'installable': True,
}
