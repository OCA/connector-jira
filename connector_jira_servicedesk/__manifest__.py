# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'JIRA Connector ServiceDesk',
    'version': '11.0.1.0.0',
    'author': 'Camptocamp,Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'category': 'Connector',
    'depends': [
        'connector_jira',
    ],
    'website': 'https://www.camptocamp.com',
    'data': [
        'views/jira_backend_views.xml',
        'views/project_project_views.xml',
        'views/project_link_jira_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
